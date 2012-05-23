from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseServerError
from webdav import util
from webdav_handlers import *

webdav_handlers = util.MethodHandlers()
webdav_handlers.add_handler("OPTIONS", OptionsHandler())
webdav_handlers.add_handler("PROPFIND", PropfindHandler())
webdav_handlers.add_handler("GET", GetHandler())
webdav_handlers.add_handler("HEAD", HeadHandler())
webdav_handlers.add_handler("PUT", PutHandler())
webdav_handlers.add_handler("DELETE", DeleteHandler())
webdav_handlers.add_handler("MKCOL", MakedirHandler())
webdav_handlers.add_handler("COPY", CopyHandler())
webdav_handlers.add_handler("MOVE", MoveHandler())

@csrf_exempt
def default(request, **kwargs):
    path = kwargs.get("localpath")
    if not hasattr(request, "localpath"):
        return HttpResponseServerError("No 'localpath' attribute found, add webdav.util.WebdavViewMiddleware to your middleware classes")
    return webdav_handlers.handle(request)
