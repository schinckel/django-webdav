import os, datetime
from xml.dom import minidom as dom
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound

def format_ctime(ctime):
    return datetime.date.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S UTC")


def list_directory(serverpath, localpath):
    st = os.stat(localpath)
    l = ["<?xml version=\"1.0\" encoding=\"utf-8\"?>",
         "<D:multistatus xmlns:D=\"DAV:\">",
         " <D:response>",
         "  <D:href>%s</D:href>"%serverpath,
         "  <D:propstat>",
         "   <D:prop>",
         "    <D:creationdate>%s</D:creationdate>"%(format_ctime(st.st_ctime)),
         "    <D:getlastmodified>%s</D:getlastmodified>"%(format_ctime(st.st_mtime)),
         "    <D:getcontentlength>%d</D:getcontentlength>"%st.st_size,
         "    <D:displayname>%s</D:displayname>"%localpath,         
         "    <D:resourcetype><D:collection/></D:resourcetype>",
         "    <D:supportedlock>",
         "     <D:lockentry>",
         "      <D:lockscope><D:exclusive/></D:lockscope>",
         "      <D:locktype><D:write/></D:locktype>",
         "     </D:lockentry>",
         "     <D:lockentry>",
         "      <D:lockscope><D:shared/></D:lockscope>",
         "      <D:locktype><D:write/></D:locktype>",
         "     </D:lockentry>",
         "    </D:supportedlock>",
         "   </D:prop>",
         "   <D:status>HTTP/1.1 200 OK</D:status>",
         "  </D:propstat>",
         " </D:response>",
         ]
    if os.path.isdir(localpath):
        filenames = os.listdir(localpath)
        for filename in filenames:
            fn = "%s%s"%(localpath, filename)
            st = os.stat(fn)
            l += [" <D:response>",
                  "  <D:href>%s%s</D:href>"%(serverpath, filename),
                  "  <D:propstat>",
                  "   <D:prop>",
                  "    <D:creationdate>%s</D:creationdate>"%(format_ctime(st.st_ctime)),
                  "    <D:getlastmodified>%s</D:getlastmodified>"%(format_ctime(st.st_mtime)),
                  "    <D:getcontentlength>%d</D:getcontentlength>"%st.st_size,
                  "    <D:displayname>%s</D:displayname>"%localpath,         
                  (os.path.isdir(fn) and "    <D:resourcetype><D:collection/></D:resourcetype>" or ""),
                  "    <D:supportedlock>",
                  "     <D:lockentry>",
                  "      <D:lockscope><D:exclusive/></D:lockscope>",
                  "      <D:locktype><D:write/></D:locktype>",
                  "     </D:lockentry>",
                  "     <D:lockentry>",
                  "      <D:lockscope><D:shared/></D:lockscope>",
                  "      <D:locktype><D:write/></D:locktype>",
                  "     </D:lockentry>",
                  "    </D:supportedlock>",
                  "   </D:prop>",
                  "   <D:status>HTTP/1.1 200 OK</D:status>",
                  "  </D:propstat>",
                  " </D:response>",
                  ]
            # no more files
    l += ["</D:multistatus>",]
    s = "\n".join(l)
    return s.encode("utf-8")


def get_response_options(request, localpath):
    response = HttpResponse()
    response["Allow"] = ["OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE", "MKCOL, PROPFIND, PROPPATCH, LOCK, UNLOCK, ORDERPATCH"]
    response["DAV"] = "1, 2, ordered-collections"
    return response
        

def get_response_propfind(request, localpath):
    if not localpath:
        return HttpResponseBadRequest("Invalid path")
    if not os.path.isdir(localpath): # TODO: only find defined dirs
        return HttpResponseNotFound()
    doc = dom.parseString(request.body)
    if not doc:
        return HttpResponseBadRequest("Invalid request")
    xml = list_directory(request.path, localpath)
    response = HttpResponse(xml,
                            None,
                            207,
                            "text/xml; charset=\"utf-8\"")
    response["DAV"] = "2"
    return response
        
def get_response(request, localpath):
    if request.method == "OPTIONS":
        return get_response_options(request, localpath)
    elif request.method == "PROPFIND":
        return get_response_propfind(request, localpath)
    return HttpResponseBadRequest("Invalid request")    
    

