"""
Copyright 2012 Peter Gebauer
Licensed under GNU GPLv3

General helper functions and classes.
Part of the django-webdav project.
"""
import os
import logging
import datetime
from xml.dom import minidom as dom
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseNotAllowed
from django.conf import settings
from django.contrib.auth import authenticate, login

logger = logging.getLogger("webdav")


class HttpResponseCreated(HttpResponse):

    def __init__(self, content='', mimetype = None, status = 201, content_type = "text/plain", **kwargs):
        HttpResponse.__init__(self, content, mimetype, status, content_type)


class HttpResponseMultistatus(HttpResponse):

    def __init__(self, content='', mimetype = None, status = 207, content_type = "text/xml", **kwargs):
        HttpResponse.__init__(self, content, mimetype, status, content_type)
        for k, v in kwargs.items():
            self[k] = v


class HttpResponseUnauthorized(HttpResponse):

    def __init__(self, content='401 Unauthorized', mimetype = None, status = 401, content_type = "text/plain", **kwargs):
        HttpResponse.__init__(self, content, mimetype, status, content_type)
        self["WWW-Authenticate"] = "Basic realm=\"%s\""%kwargs.get("realm", "WebDAV")


def is_file(path):
    return os.path.isfile(path) and not os.path.islink(path)


def is_dir(path):
    return os.path.isdir(path) and not os.path.islink(path)


def get_base_uri(request, path):
    s1 = request.build_absolute_uri()[:-len(path)]
    s2 = request.build_absolute_uri()[-len(path):]
    return s1, s2
            

def format_timestamp(ts):
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime('%a, %d %b %Y %H:%M:%S %Z')


class Elem(object):

    def __init__(self, name, children = [], **kwargs):
        self.name = name
        self.children = list(children)
        self.attributes = kwargs

    def __repr__(self):
        return "<Elem %s>"%self.name

    def get_xml(self):
        s = u"<%s"%self.name
        for k, v in self.attributes.items():
            s += u" %s=\"%s\""%(k, v)
        s += u">"
        for child in self.children:
            if hasattr(child, "get_xml"):
                s += child.get_xml()
            else:
                s += unicode(child)
        s += u"</%s>"%self.name
        return unicode(s)

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


class DirectoryACL(object):
    ACL_FILENAME = ".webdav-acl"
    ACL_READ = "read"
    ACL_WRITE = "write"
    ACL_DELETE = "delete"
    ACL_NEW_FILE = "new_file"
    ACL_ACL = "acl"

    def __init__(self, webdavpath, path):
        self.webdavpath = webdavpath
        self.path = path
        self.access_lists = {}
        self.read_acl_file()

    def read_acl_file(self):
        self.access_lists = {}
        fn = self.get_acl_filename(self.path)
        if fn:
            try:
                f = file(fn, "r")
                data = f.read()
                f.close()
            except IOError, ioe:
                logger.warning("could not read ACL file '%s'; %s"%(fn, ioe))
                return False
            for line in data.split("\n"):
                params = line.split("=", 1)
                if len(params) > 1:
                    listname = params[0].strip()
                    values = [s.strip() for s in params[1].split(" ")]
                    if listname and values:
                        self.access_lists[listname] = values
            return True
        return False

    def get_acl_filename(self, path):
        if not self.webdavpath:
            return None        
        local_path = os.path.dirname("%s/"%path)
        while local_path.find("/") >= 0:
            fn = os.path.normpath("%s/%s"%(local_path, self.ACL_FILENAME))
            if is_file(fn):
                logger.debug("using ACL file '%s'"%fn)
                return fn
            else:
                logger.debug("no ACL file '%s', ignoring"%fn)
            local_path = "/".join(local_path.split("/")[:-1])
        return None

    def match_user(self, user, lst):
        for entry in lst:
            if entry == "*":
                return True
            username, groupname = None, None
            if entry.find(":") >= 0:
                type_, value = [s.strip() for s in entry.split(":",1)]
                if type_.lower() == "group":
                    groupname = value
                elif type_.lower() == "user":
                    username = value
                else:
                    logger.warning("invalid ACL token type '%s'"%type_)
            else:
                username, groupname = entry, entry
            if username and username == user.username:
                return True
            if groupname:
                groups = user.groups.all()
                if groups and groupname in [g.name for g in groups]:
                    return True
        return False

    def perm_read(self, user):
        if self.webdavpath and user == self.webdavpath.owner:
            return True
        return self.match_user(user,
                               self.access_lists.get(self.ACL_READ, []))

    def perm_write(self, user):
        if self.webdavpath and user == self.webdavpath.owner:
            return True
        return self.match_user(user,
                               self.access_lists.get(self.ACL_WRITE, []))

    def perm_delete(self, user):
        if self.webdavpath and user == self.webdavpath.owner:
            return True
        return self.match_user(user,
                               self.access_lists.get(self.ACL_DELETE, []))

    def perm_new_file(self, user):
        if self.webdavpath and user == self.webdavpath.owner:
            return True
        return self.match_user(user,
                               self.access_lists.get(self.ACL_NEW_FILE, []))

    def perm_acl(self, user):
        if self.webdavpath and user == self.webdavpath.owner:
            return True
        return self.match_user(user,
                               self.access_lists.get(self.ACL_ACL, []))


def get_used_quota(path):
    totalsize = 0
    totalnum = 0
    try:
        if os.path.islink(path):
            return 0, 0
        elif is_dir(path):
            for filename in os.listdir(path):
                fn = os.path.normpath("%s/%s"%(path, filename))
                addsize, addnum = get_used_quota(fn)
                totalsize += addsize
                totalnum += addnum
        else:
            totalsize = os.path.getsize(path)
            totalnum = 1
    except IOError, ioe:
        logger.warning("could not get quota for '%s'; %s"%(path, ioe))
    return totalsize, totalnum


def check_http_authorization(acl, request, webdavpath, acl_name):
    # First up, is someone trying to use HTTP authorization?
    if request.META.has_key("HTTP_AUTHORIZATION"):
        # Sure enough, let's authenticate them first
        authentication = request.META["HTTP_AUTHORIZATION"]
        spl = authentication.split(" ", 1)
        if len(spl) == 2:
            if "basic" == spl[0].lower():
                token = spl[1].strip().decode('base64')
                spl2 = token.split(":", 1)
                if len(spl2) == 2:
                    username, password = spl2
                    user = authenticate(username=username, password=password)
                    if user is not None and user.is_active:
                        login(request, user)
                        logger.info("login via basic auth '%s'"%username)
                        return None
                    else:
                        logger.warning("failed login via basic auth '%s'"
                                       %username)
    # Regardless if HTTP authorization was successful or not, let's check permissions
    funct = getattr(acl, "perm_%s"%acl_name)
    result = callable(funct) and funct(request.user) or False
    # No need to process further, we got what we wanted
    if result: 
        return None
    # If we are authenticated but still not authorized, do 405
    if request.user.is_authenticated() and not result:
        return HttpResponseNotAllowed("403 No Permission")
    # Ok, anonymous user is not allowed, let's see if the user wants to introduce himself
    response = HttpResponse("Authorization required", None, 401, "text/plain")
    if hasattr(settings, "BASIC_AUTH_REALM"):
        realm = settings.BASIC_AUTH_REALM
    else:
        realm = "django"
    response['WWW-Authenticate'] = 'Basic realm="%s"'%realm
    return response
