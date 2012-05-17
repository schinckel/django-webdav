from webdav.models import WebdavPath
from django.contrib import admin

class WebdavPathAdmin(admin.ModelAdmin):
    fields = ['url_path', 'local_path', 'quota', 'owner']

admin.site.register(WebdavPath, WebdavPathAdmin)
