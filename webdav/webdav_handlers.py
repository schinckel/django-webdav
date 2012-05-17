"""
Copyright 2012 Peter Gebauer
Licensed under GNU GPLv3

WebDAV implementation.
Part of the django-webdav project.
"""
import logging

import os
import shutil
from webdav.util import *
from webdav.models import WebdavPath
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseNotAllowed

logger = logging.getLogger("webdav")

class OptionsHandler(MethodHandler):

    def handle(self, request, path):
        response = HttpResponse()
        if self.mhandlers:
            response["Allow"] = ", ".join(self.mhandlers.keys())
        response["DAV"] = "1, 2, ordered-collections"
        return response


class PropfindHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        acl = DirectoryACL(found_path, lcpath)
        if not acl.perm_read(request.user):
            return HttpResponseNotAllowed("405 Not Allowed")
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
        if not os.path.isdir(lcpath):
            return HttpResponseBadRequest("403 Bad Request")
        try:
            iterfiles = [lcpath] + os.listdir(lcpath)
        except IOError, ioe:
            logger.warning("could not list directory '%s'; %s"%(lcpath, ioe))
            return HttpResponseNotAllowed("405 Not Allowed")
        for filename in iterfiles:
            if (filename == acl.ACL_FILENAME 
                and not acl.perm_acl(request.user)):
                continue
            if filename == lcpath:
                urn = os.path.normpath(request.path)
                fn = lcpath
            else:
                urn = os.path.normpath("%s/%s"%(request.path, filename))
                fn = os.path.normpath("%s/%s/"%(lcpath, filename))
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
                if os.path.isdir(fn):
                    prop.add_child(Elem("resourcetype")).add_child(Elem("collection"))          
                else:
                    prop.add_child(Elem("resourcetype"))
                propstat.add_child(Elem("status")).add_child("HTTP/1.1 200 OK")
            else:
                propstat.add_child(Elem("status")).add_child("HTTP/1.1 405 Not allowed")

        logger.debug("returned collection '%s' from '%s'"%(
            found_path.url_path, found_path.local_path))
        xml = multistatus.get_xml()
        logger.info("propfind '%s'"%lcpath)
        return HttpResponseMultistatus(xml, DAV = "1, 2, ordered-collections")


class GetHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        acl = DirectoryACL(found_path, lcpath)
        if (os.path.basename(lcpath) == acl.ACL_FILENAME 
            and not acl.perm_acl(request.user)):
            return HttpResponseNotFound()        
        if not acl.perm_read(request.user):
            return HttpResponseNotAllowed("405 Not Allowed")
        if not os.path.isfile(lcpath):
            return HttpResponseNotFound()        
        try:
            fsock = file(lcpath, "r")
        except IOError, ioe:
            logger.warning("could read file '%s' ('%s'); %s"%(
                    found_path.url_path, lcpath, ioe))
            return HttpResponseNotAllowed("405 Not allowed")
        filename = os.path.basename(lcpath)
        filesize = os.path.getsize(lcpath)
        response = HttpResponse(fsock)
        response['Content-Disposition'] = 'attachment; filename=' + filename
        logger.info("read file '%s' ('%s')"%(found_path.url_path, lcpath))
        return response


class HeadHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        acl = DirectoryACL(found_path, lcpath)
        if (os.path.basename(lcpath) == acl.ACL_FILENAME 
            and not acl.perm_acl(request.user)):
            return HttpResponseNotFound()        
        if not acl.perm_read(request.user):
            return HttpResponseNotAllowed("405 Not Allowed")
        if not os.path.isfile(lcpath):
            return HttpResponseNotFound()        
        response = HttpResponse()
        filename = os.path.basedir(lcpath)
        response['Content-Disposition'] = 'attachment; filename=' + filename
        logger.info("head file '%s' ('%s')"%(found_path.url_path, lcpath))
        return response
    

class PutHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        acl = DirectoryACL(found_path, lcpath)
        if (os.path.basename(lcpath) == acl.ACL_FILENAME 
            and not acl.perm_acl(request.user)):
            return HttpResponseNotAllowed("405 Not Allowed")
        if os.path.isdir(lcpath):
            return HttpResponseBadRequest()
        elif os.path.isfile(lcpath):
            if not acl.perm_write(request.user):
                return HttpResponseNotAllowed("405 Not Allowed")
        else:
            if not acl.perm_new_file(request.user):
                return HttpResponseNotAllowed("405 Not Allowed")
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
                return HttpResponseNotAllowed("405 Not Allowed")
            if num_files + 1 >= max_num_files:
                logger.info("num files exceeded for '%s' ('%s') %d/%d"%(
                    found_path.url_path, lcpath, num_files, max_num_files))
                return HttpResponseNotAllowed("405 Not Allowed")
        else:
            used_quota = 0
            num_files = 0

        try:
            fileout = file(lcpath, "w")
        except IOError, ioe:
            logger.warning("could write file '%s'; %s"%(lcpath, ioe))
            return HttpResponseNotAllowed("405 Not Allowed")
        
        buf = request.read(1024)
        while len(buf) > 0:
            if max_quota > 0:
                used_quota += len(buf)
                if used_quota >= max_quota:
                    fileout.close()
                    logger.info("quota exceeded for '%s' ('%s') %d/%d"%(
                        found_path.url_path, lcpath, used_quota, max_quota))
                    return HttpResponseNotAllowed("405 Not Allowed")
            fileout.write(buf)
            buf = request.read(1024)
        fileout.close()
        logger.info("wrote file '%s'"%lcpath)
        return HttpResponse()        


class DeleteHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        acl = DirectoryACL(found_path, lcpath)
        if (os.path.basename(lcpath) == acl.ACL_FILENAME 
            and not acl.perm_acl(request.user)):
            return HttpResponseNotAllowed("405 Not Allowed")
        if not acl.perm_delete(request.user):
            return HttpResponseNotAllowed("405 Not Allowed")
        if not os.path.isfile(lcpath) and not os.path.isdir(lcpath):
            return HttpResponseNotFound()
        if os.path.isdir(lcpath):
            try:
                shutil.rmtree(lcpath)
                logger.info("removed directory '%s'"%lcpath)
            except IOError, ioe:
                logger.warning("could not remove directory '%s'; %s"%(lcpath, ioe))
                return HttpResponseNotAllowed("405 Not Allowed")            
        elif os.path.isfile(lcpath):
            try:
                os.remove(lcpath)            
                logger.info("removed file '%s'"%lcpath)
            except IOError, ioe:
                logger.warning("could not remove file '%s'; %s"%(lcpath, ioe))
                return HttpResponseNotAllowed("405 Not Allowed")
        response = HttpResponse()
        return response
    

class MakedirHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        acl = DirectoryACL(found_path, lcpath)
        if (os.path.basename(lcpath) == acl.ACL_FILENAME 
            and not acl.perm_acl(request.user)):
            return HttpResponseNotAllowed("405 Not Allowed")
        if not acl.perm_new_file(request.user):
            return HttpResponseNotAllowed("405 Not Allowed")
        if os.path.isdir(lcpath) or os.path.isfile(lcpath):
            return HttpResponseNotAllowed("405 Not Allowed")
        try:
            os.mkdir(lcpath)
        except IOError, ioe:
            logger.warning("could create directory '%s'; %s"%(lcpath, ioe))
            return HttpResponseNotAllowed("405 Not Allowed")
        logger.info("created directory '%s'"%lcpath)
        return HttpResponse()        
