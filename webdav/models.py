from django.db import models

class WebdavPath(models.Model):
    url_path = models.CharField(max_length=1024)
    local_path = models.CharField(max_length=1024)
