"""
Copyright 2012 Peter Gebauer
Licensed under GNU GPLv3

WebDAV implementation.
Part of the django-webdav project.
"""
import logging

import os
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
        if not check_restriction_read(request.user, found_path):
            return HttpResponseUnauthorized("401 Unauthorized READ")
        lcpath = found_path.get_local_path(path)
        if not os.path.isdir(lcpath):
            return HttpResponseNotFound()
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
        iterfiles = [lcpath] + os.listdir(lcpath)
        for filename in iterfiles:
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
            st = os.stat(fn)
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
            propstat.add_child(Elem("status")).add_child("HTTP/1.1 200 OK")

        logger.debug("returned collection '%s' from '%s'"%(
            found_path.url_path, found_path.local_path))
        xml = multistatus.get_xml()
        return HttpResponseMultistatus(xml, DAV = "1, 2, ordered-collections")


class GetHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        if not check_restriction_read(request.user, found_path):
            return HttpResponseUnauthorized("401 Unauthorized READ")
        lcpath = found_path.get_local_path(path)
        if not os.path.isfile(lcpath):
            return HttpResponseNotFound()        
        try:
            fsock = file(lcpath, "r")
        except IOError, ioe:
            logger.warning("invalid file permissions '%s' ('%s'); %s"%(
                found_path.url_path, lcpath, ioe))
            return HttpResponseUnauthorized("401 Unauthorized (internal)")
        filename = os.path.basename(lcpath)
        filesize = os.path.getsize(lcpath)
        response = HttpResponse(fsock)
        response['Content-Disposition'] = 'attachment; filename=' + filename
        return response


class HeadHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        if not check_restriction_read(request.user, found_path):
            return HttpResponseUnauthorized("401 Unauthorized READ")
        lcpath = found_path.get_local_path(path)
        if not os.path.isfile(lcpath):
            return HttpResponseNotFound()        
        response = HttpResponse()
        response['Content-Disposition'] = 'attachment; filename=' + filename
        return response
    

class PutHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        lcpath = found_path.get_local_path(path)
        if os.path.isdir(lcpath):
            return HttpResponseBadRequest()
        elif os.path.isfile(lcpath):
            if not check_restriction_write(request.user, found_path):
                return HttpResponseUnauthorized("401 Unauthorized WRITE")
        else:
            if not check_restriction_new_file(request.user, found_path):
                return HttpResponseUnauthorized("401 Unauthorized NEW FILE")
        try:
            content_length = int(request.META.get("CONTENT_LENGTH"))
        except (ValueError, TypeError):
            content_length = 0
        max_quota = found_path.quota * WebdavPath.QUOTA_SIZE_MULT
        if max_quota > 0:
            used_quota = found_path.get_used_quota()
            if used_quota + content_length >= max_quota:
                logger.info("quota exceeded for '%s' ('%s') %d/%d"%(
                    found_path.url_path, lcpath, used_quota, max_quota))
                return HttpResponseUnauthorized("401 Unauthorized QUOTA")
        else:
            used_quota = 0

        try:
            fileout = file(lcpath, "w")
        except IOError, ioe:
            logger.warning("invalid file permissions '%s' ('%s'); %s"%(
                found_path.url_path, lcpath, ioe))
            return HttpResponseUnauthorized("401 Unauthorized (internal)")
        
        buf = request.read(1024)
        while len(buf) > 0:
            if max_quota > 0:
                used_quota += len(buf)
                if used_quota >= max_quota:
                    fileout.close()
                    logger.info("quota exceeded for '%s' ('%s') %d/%d"%(
                        found_path.url_path, lcpath, used_quota, max_quota))
                    return HttpResponseUnauthorized("401 Unauthorized QUOTA")
            fileout.write(buf)
            buf = request.read(1024)
        fileout.close()
        return HttpResponse()        


class DeleteHandler(MethodHandler):

    def handle(self, request, path):
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        if not check_restriction_delete(request.user, found_path):
            return HttpResponseUnauthorized("401 Unauthorized DELETE")
        lcpath = found_path.get_local_path(path)
        if not os.path.isfile(lcpath):
            return HttpResponseNotFound()
        if os.path.isdir(lcpath):
            pass
        elif os.path.isfile(lcpath):
            try:
                os.remove(lcpath)            
            except IOError, ioe:
                logger.warning("invalid file permissions '%s' ('%s'); %s"%(
                    found_path.url_path, lcpath, ioe))
                return HttpResponseUnauthorized("401 Unauthorized (internal)")
        response = HttpResponse()
        return response
    
