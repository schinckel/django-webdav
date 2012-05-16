from webdav.models import WebdavPath
from django.contrib import admin

class WebdavPathAdmin(admin.ModelAdmin):
    fields = ['url_path', 'local_path', 'quota', 'read_access', 'write_access', 'new_file_access', 'delete_access']

admin.site.register(WebdavPath, WebdavPathAdmin)
