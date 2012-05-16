"""
Copyright 2012 Peter Gebauer
Licensed under GNU GPLv3

WebDAV implementation.
Part of the django-webdav project.
"""
from util import *

class OptionsHandler(MethodHandler):

    def handle(self, request, path):
        response = HttpResponse()
        response["Allow"] = ["OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE", 
                             "MKCOL, PROPFIND, PROPPATCH, LOCK, UNLOCK, ORDERPATCH"]
        response["DAV"] = "1, 2, ordered-collections"
        return response


class PropfindHandler(MethodHandler):

    def handle(self, request, path):
        elem = Elem.from_xml(request.body)
        if not elem:
            return HttpResponseBadRequest()
        find_props = []
        for child in elem.find_children("prop"):
            for child2 in child.children:
                if hasattr(child2, "name"):
                    find_props.append(child2.name)
        elem = Elem("multistatus", xmlns="DAV:")
        xml = elem.get_xml()
        print xml
        response = HttpResponseMultistatus(xml)
        return response

