"""
Copyright 2012 Peter Gebauer
Licensed under GNU GPLv3

General helper functions and classes.
Part of the django-webdav project.
"""
import logging
import datetime
from xml.dom import minidom as dom
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseNotAllowed

logger = logging.getLogger("webdav")

class HttpResponseMultistatus(HttpResponse):

    def __init__(self, content='', mimetype = None, status = 207, content_type = "text/xml", **kwargs):
        HttpResponse.__init__(self, content, mimetype, status, content_type)
        for k, v in kwargs.items():
            self[k] = v


class HttpResponseUnauthorized(HttpResponse):

    def __init__(self, content='401 Unauthorized', mimetype = None, status = 401, content_type = "text/plain", **kwargs):
        HttpResponse.__init__(self, content, mimetype, status, content_type)
        self["WWW-Authenticate"] = "Basic realm=\"%s\""%kwargs.get("realm", "WebDAV")
            
    
            

def format_timestamp(ts):
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime('%a, %d %b %Y %H:%M:%S %Z')


def check_restriction_read(user, webdavpath):
    if not webdavpath.read_access.strip():
        return True
    if not user.is_active:
        return False
    if user.is_staff:
        return True
    groupsnusers = [s.strip() for s in webdavpath.read_access.split(",")]
    for grouporuser in groupsnusers:
        if grouporuser == user.username or grouporuser in user.groups:
            return True
    return False

def check_restriction_write(user, webdavpath):
    if not webdavpath.write_access.strip():
        return True
    if not user.is_active:
        return False
    if user.is_staff:
        return True
    groupsnusers = [s.strip() for s in webdavpath.write_access.split(",")]
    for grouporuser in groupsnusers:
        if grouporuser == user.username or grouporuser in user.groups:
            return True
    return False

def check_restriction_delete(user, webdavpath):
    if not webdavpath.delete_access.strip():
        return True
    if not user.is_active:
        return False
    if user.is_staff:
        return True
    groupsnusers = [s.strip() for s in webdavpath.delete_access.split(",")]
    for grouporuser in groupsnusers:
        if grouporuser == user.username or grouporuser in user.groups:
            return True
    return False

def check_restriction_new_file(user, webdavpath):
    if not webdavpath.new_file_access.strip():
        return True
    if not user.is_active:
        return False
    if user.is_staff:
        return True
    groupsnusers = [s.strip() for s in webdavpath.new_file_access.split(",")]
    for grouporuser in groupsnusers:
        if grouporuser == user.username or grouporuser in user.groups:
            return True
    return False


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

    def add_child(self, child):
        self.children.append(child)
        return child
    
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

    def __init__(self, mhandlers = None):
        self.mhandlers = mhandlers
    
    def handle(self, request, path):
        raise NotImplementedError()


class MethodHandlers(dict):

    def add_handler(self, method, handler):
        self[method] = handler
        handler.mhandlers = self

    def handle(self, request, path):
        
        handler = self.get(request.method)
        if handler:
            return handler.handle(request, path)
        logger.info("method '%s' not supported"%request.method)
        return HttpResponseNotAllowed(self.keys())


