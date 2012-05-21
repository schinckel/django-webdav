"""
Copyright 2012 Peter Gebauer
Licensed under GNU GPLv3

WebDAV implementation.
Part of the django-webdav project.
"""
import logging
import urllib
import os
import shutil
from webdav.util import *
from webdav.models import WebdavPath
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden

logger = logging.getLogger("webdav")

class OptionsHandler(MethodHandler):

    def handle(self, request, path):
        response = HttpResponse()
        if self.mhandlers:
            response["Allow"] = ", ".join(self.mhandlers.keys())
        response["DAV"] = "1, 2, ordered-collections"
        return response


class PropfindHandler(MethodHandler):
    """
    Implements: PROPFIND method.
    Status: completed.
    """

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        if not lcpath:
            return HttpResponseForbidden("403 Internal")
        acl = DirectoryACL(found_path, lcpath)
        response = check_http_authorization(acl, request, found_path, "read")
        if response:
            return response
        elem = Elem.from_xml(request.body)
        if not elem:
            return HttpResponseBadRequest()
        find_props = []
        for child in elem.find_children("prop"):
            for child2 in child.children:
                if hasattr(child2, "name"):
                    find_props.append(child2.name)
        # Return response
        multistatus = Elem("multistatus", xmlns="DAV:")
        if not is_dir(lcpath):
            return HttpResponseBadRequest("400 Bad Request")
        try:
            iterfiles = [lcpath] + os.listdir(lcpath)
        except IOError, ioe:
            logger.warning("could not list directory '%s'; %s"%(lcpath, ioe))
            return HttpResponseForbidden("403 Internal")
        for filename in iterfiles:
            if filename == lcpath:
                urn = urllib.quote(request.path.encode("utf-8"))
                fn = lcpath
            else:
                urn = urllib.quote(os.path.normpath("%s/%s"%(request.path, filename)).encode("utf-8"))
                fn = os.path.normpath("%s/%s/"%(lcpath, filename))
            if (filename == acl.ACL_FILENAME 
                and not acl.perm_acl(request.user)):
                continue
            if not is_file(fn) and not is_dir(fn):
                continue
            response = multistatus.add_child(Elem("response"))
            response.add_child(Elem("href")).add_child(urn)
            propstat = response.add_child(Elem("propstat"))
            prop = propstat.add_child(Elem("prop"))
            try:
                st = os.stat(fn)
            except IOError, ioe:
                st = None
                logger.warning("could not stat file '%s'"%fn)
            if st:
                if "creationdate" in find_props:
                    cdate = format_timestamp(st.st_ctime)
                    prop.add_child(Elem("creationdate")).add_child(cdate)
                if "getlastmodified" in find_props:
                    mdate = format_timestamp(st.st_mtime)
                    prop.add_child(Elem("getlastmodified")).add_child(mdate)
                if "getcontentlength" in find_props:
                    prop.add_child(Elem("getcontentlength")).add_child("%d"%os.path.getsize(fn))
                if is_dir(fn):
                    prop.add_child(Elem("resourcetype")).add_child(Elem("collection"))          
                else:
                    prop.add_child(Elem("resourcetype"))
                propstat.add_child(Elem("status")).add_child("HTTP/1.1 200 OK")
            else:
                propstat.add_child(Elem("status")).add_child("HTTP/1.1 403 Internal")

        logger.debug("returned collection '%s' from '%s'"%(
            found_path.url_path, found_path.local_path))
        xml = u"<?xml version=\"1.0\" encoding=\"utf-8\"?>" + multistatus.get_xml()
        xmldata = xml.encode("utf-8")
        logger.info("propfind '%s'"%lcpath)
        file("xml.log", "w").write(xmldata)
        return HttpResponseMultistatus(xmldata, DAV = "1, 2, ordered-collections")


class GetHandler(MethodHandler):
    """
    Implements: GET method.
    Status: completed.
    """

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        if not lcpath:
            return HttpResponseForbidden("403 Internal")
        acl = DirectoryACL(found_path, lcpath)
        response = check_http_authorization(acl, request, found_path, "read")
        if response:
            return response
        if (not is_file(lcpath) 
            or (lcpath.endswith(acl.ACL_FILENAME) and not acl.perm_acl(request.user))):
            return HttpResponseNotFound()        
        try:
            fsock = file(lcpath, "r")
        except IOError, ioe:
            logger.warning("could read file '%s' ('%s'); %s"%(
                    found_path.url_path, lcpath, ioe))
            return HttpResponseForbidden("403 Internal")
        filename = os.path.basename(lcpath)
        filesize = os.path.getsize(lcpath)
        response = HttpResponse(fsock)
        response['Content-Disposition'] = 'attachment; filename=' + filename.encode("utf-8")
        logger.info("read file '%s' ('%s')"%(found_path.url_path, lcpath))
        return response


class HeadHandler(MethodHandler):
    """
    Implements: HEAD method.
    Status: not complete. I'm not sure what da heck this is supposed to do.
    """

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        if not lcpath:
            return HttpResponseForbidden("403 Internal")
        acl = DirectoryACL(found_path, lcpath)
        response = check_http_authorization(acl, request, found_path, "read")
        if response:
            return response
        if (not is_file(lcpath) 
            or (lcpath.endswith(acl.ACL_FILENAME) and not acl.perm_acl(request.user))):
            return HttpResponseNotFound()        
        try:
            fsock = file(lcpath, "r")
        except IOError, ioe:
            logger.warning("could read file '%s' ('%s'); %s"%(
                    found_path.url_path, lcpath, ioe))
            return HttpResponseForbidden("403 Internal")
        filename = os.path.basename(lcpath)
        filesize = os.path.getsize(lcpath)
        response = HttpResponse(fsock)
        response['Content-Disposition'] = 'attachment; filename=' + filename
        logger.info("read file '%s' ('%s')"%(found_path.url_path, lcpath))
        return response
    

class PutHandler(MethodHandler):
    """
    Implements: PUT method.
    Status: completed.
    """

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)        
        if not lcpath:
            return HttpResponseForbidden("403 Internal")
        acl = DirectoryACL(found_path, lcpath)
        if is_file(lcpath):
            response = check_http_authorization(acl, request, found_path, "write")
            if response:
                return response
        else:
            response = check_http_authorization(acl, request, found_path, "new_file")
            if response:
                return response
        if os.path.islink(lcpath) or is_dir(lcpath):
            logger.warning("trying to overwrite symbolic link or dir '%s'"%lcpath)
            return HttpResponseForbidden("403 Put directory")
        if lcpath.endswith(acl.ACL_FILENAME) and not acl.perm_acl(request.user):
            return HttpResponseForbidden("403 Permission")
        try:
            content_length = int(request.META.get("CONTENT_LENGTH"))
        except (ValueError, TypeError):
            content_length = 0
        max_quota = found_path.quota * WebdavPath.QUOTA_SIZE_MULT
        max_num_files = found_path.max_num_files
        if max_quota > 0:
            used_quota, num_files = get_used_quota(found_path.local_path)
            if used_quota + content_length >= max_quota:
                logger.info("quota exceeded for '%s' ('%s') %d/%d"%(
                    found_path.url_path, lcpath, used_quota, max_quota))
                return HttpResponseForbidden("403 Quota")
            if num_files + 1 >= max_num_files:
                logger.info("num files exceeded for '%s' ('%s') %d/%d"%(
                    found_path.url_path, lcpath, num_files, max_num_files))
                return HttpResponseForbidden("403 Num files")
        else:
            used_quota = 0
            num_files = 0
        try:
            fileout = file(lcpath, "w")
        except IOError, ioe:
            logger.warning("could write file '%s'; %s"%(lcpath, ioe))
            return HttpResponseForbidden("403 Internal")
        buf = request.read(1024)
        while len(buf) > 0:
            if max_quota > 0:
                used_quota += len(buf)
                if used_quota >= max_quota:
                    fileout.close()
                    logger.info("quota exceeded for '%s' ('%s') %d/%d"%(
                        found_path.url_path, lcpath, used_quota, max_quota))
                    return HttpResponseForbidden("403 Quota")
            fileout.write(buf)
            buf = request.read(1024)
        fileout.close()
        logger.info("wrote file '%s'"%lcpath)
        return HttpResponseCreated()


class DeleteHandler(MethodHandler):
    """
    Implements: DELETE method.
    Status: completed.
    """

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        if not lcpath:
            return HttpResponseForbidden("403 Internal")
        acl = DirectoryACL(found_path, lcpath)
        response = check_http_authorization(acl, request, found_path, "delete")
        if response:
            return response
        if lcpath.endswith(acl.ACL_FILENAME) and not acl.perm_acl(request.user):
            return HttpResponseForbidden("403 Permission")
        if not is_file(lcpath) and not is_dir(lcpath):
            return HttpResponseNotFound()
        if is_dir(lcpath):
            try:
                shutil.rmtree(lcpath)
                logger.info("removed directory '%s'"%lcpath)
            except IOError, ioe:
                logger.warning("could not remove directory '%s'; %s"%(lcpath, ioe))
                return HttpResponseNotAllowed("405 Not Allowed")            
        elif is_file(lcpath):
            try:
                os.remove(lcpath)            
                logger.info("removed file '%s'"%lcpath)
            except IOError, ioe:
                logger.warning("could not remove file '%s'; %s"%(lcpath, ioe))
                return HttpResponseNotAllowed("405 Not Allowed")
        response = HttpResponse()
        return response
    

class MakedirHandler(MethodHandler):
    """
    Implements: MKCOL method.
    Status: completed.
    """

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        if not lcpath:
            return HttpResponseForbidden("403 Internal")
        acl = DirectoryACL(found_path, lcpath)
        response = check_http_authorization(acl, request, found_path, "new_file")
        if response:
            return response
        if lcpath.endswith(acl.ACL_FILENAME) and not acl.perm_acl(request.user):
            return HttpResponseForbidden("403 Permission")
        if is_dir(lcpath) or is_file(lcpath):
            return HttpResponseNotAllowed("405 Not Allowed")
        try:
            os.mkdir(lcpath)
        except IOError, ioe:
            logger.warning("could create directory '%s'; %s"%(lcpath, ioe))
            return HttpResponseNotAllowed("405 Not Allowed")
        logger.info("created directory '%s'"%lcpath)
        return HttpResponseCreated()


class CopyHandler(MethodHandler):
    """
    Implements: COPY method.
    Status: not completed.
    """

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        if not lcpath:
            return HttpResponseForbidden("403 Internal")
        response = check_http_authorization(acl, request, found_path, "new_file")
        if response:
            return response
        if lcpath.endswith(acl.ACL_FILENAME) and not acl.perm_acl(request.user):
            return HttpResponseForbidden("403 Permission")
