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
        # Check paths
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        if not check_restriction_read(found_path):
            return HttpResponse('', None, 401) 
        lcpath = found_path.get_local_path(path)
        if not os.path.isdir(lcpath):
            return HttpResponseNotFound()
        
        # Get property request
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
        # Check paths
        found_path = WebdavPath.get_match_path_to_dir(path)
        if not found_path:
            return HttpResponseNotFound()
        if not check_restriction_read(found_path):
            return HttpResponse('', None, 401) 
        lcpath = found_path.get_local_path(path)
        if not os.path.isfile(lcpath):
            return HttpResponseNotFound()

        print lcpath

        fsock = open(lcpath, "r")
        filename = os.path.basename(lcpath)
        filesize = os.path.getsize(lcpath)
        response = HttpResponse(fsock)
        response['Content-Disposition'] = 'attachment; filename=' + filename
        return response
