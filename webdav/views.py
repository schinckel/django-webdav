from django.views.decorators.csrf import csrf_exempt
from browncloud import webdav

@csrf_exempt
def default(request, **kwargs):
    print request.body
    response = webdav.get_response(request, kwargs.get("localpath"))
    return response
