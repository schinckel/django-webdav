from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
import util, webdav

handlers = util.MethodHandlers()
handlers.add_handler("OPTIONS", webdav.OptionsHandler())
handlers.add_handler("PROPFIND", webdav.PropfindHandler())

@csrf_exempt
def default(request, **kwargs):
    path = kwargs.get("localpath")
    return handlers.handle(request, path)
