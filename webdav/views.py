from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from webdav import util
from webdav_handlers import *

handlers = util.MethodHandlers()
handlers.add_handler("OPTIONS", OptionsHandler())
handlers.add_handler("PROPFIND", PropfindHandler())
handlers.add_handler("GET", GetHandler())
handlers.add_handler("HEAD", HeadHandler())
handlers.add_handler("PUT", PutHandler())
handlers.add_handler("DELETE", DeleteHandler())
handlers.add_handler("MKCOL", MakedirHandler())

@csrf_exempt
def default(request, **kwargs):
    path = kwargs.get("localpath")
    return handlers.handle(request, path)
