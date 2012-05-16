from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
import util
from webdav_handlers import *

handlers = util.MethodHandlers()
handlers.add_handler("OPTIONS", OptionsHandler())
handlers.add_handler("PROPFIND", PropfindHandler())
handlers.add_handler("GET", GetHandler())

@csrf_exempt
def default(request, **kwargs):
    path = kwargs.get("localpath")
    return handlers.handle(request, path)
