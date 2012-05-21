from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseServerError
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
handlers.add_handler("COPY", CopyHandler())

@csrf_exempt
def default(request, **kwargs):
    path = kwargs.get("localpath")
    if not hasattr(request, "localpath"):
        return HttpResponseServerError("No 'localpath' attribute found, add webdav.util.WebdavViewMiddleware to your middleware classes")
    return handlers.handle(request)
