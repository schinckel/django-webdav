"""
Copyright 2012 Peter Gebauer
Licensed under GNU GPLv3

General helper functions and classes.
Part of the django-webdav project.
"""
import datetime
from xml.dom import minidom as dom
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound


class HttpResponseMultistatus(HttpResponse):

    def __init__(self, content='', mimetype = None, status = 207, content_type = "text/xml"):
        HttpResponse.__init__(self, content, mimetype, status, content_type)


def get_iso8601(value):
    if not hasattr(value, "isoformat"): # must be a timestamp then
        value = datetime.datetime.fromtimestamp(value)
    return value.isoformat("T")


class Elem(object):

    def __init__(self, name, children = [], **kwargs):
        self.name = name
        self.children = list(children)
        self.attributes = kwargs

    def __repr__(self):
        return "<Elem %s>"%self.name

    def get_xml(self):
        s = "<%s"%self.name
        for k, v in self.attributes.items():
            s += " %s=\"%s\""%(k, v)
        s += ">"
        for child in self.children:
            if hasattr(child, "get_xml"):
                s += child.get_xml()
            else:
                s += str(child)
        s += "</%s>"%self.name
        return s

    def find_children(self, name):
        r = []
        for child in self.children:
            if hasattr(child, "name") and child.name == name:
                r.append(child)
            if hasattr(child, "find_children"):
                r += child.find_children(name)
        return r

    @staticmethod
    def _from_node(node):
        if node.nodeType == node.ELEMENT_NODE:
            elem = Elem(node.tagName)
            for cnode in node.childNodes:
                if cnode.nodeType == node.ATTRIBUTE_NODE:
                    elem.attributes[cnode.name] = cnode.value
                elif cnode.nodeType == node.ELEMENT_NODE:
                    newchild = Elem._from_node(cnode)
                    if newchild:
                        elem.children.append(newchild)
                elif cnode.nodeType == node.TEXT_NODE or cnode.nodeType == CDATA_SECTION_NODE:
                    if str(cnode.data).strip():
                        elem.children.append(str(cnode.data).strip())
            return elem
        return None

    @staticmethod
    def from_xml(xml):
        doc = dom.parseString(xml)
        if not doc:
            return None
        return Elem._from_node(doc.documentElement)


class MethodHandler(object):

    def handle(self, request, path):
        raise NotImplementedError()


class MethodHandlers(dict):

    def add_handler(self, method, handler):
        self[method] = handler

    def handle(self, request, path):
        handler = self.get(request.method)
        if handler:
            return handler.handle(request, path)
        return HttpResponseBadRequest()


