import os
import logging
from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger("webdav")

class WebdavPath(models.Model):
    QUOTA_SIZE_MULT = 1024 * 1024 # megs

    url_path = models.CharField(max_length=1024)
    local_path = models.CharField(max_length=1024)
    quota = models.IntegerField()
    max_num_files = models.IntegerField()
    owner = models.ForeignKey(User)

    def get_local_path(self, path):
        return os.path.normpath("%s/%s"%(self.local_path, path[len(self.url_path)-1:]))

    @classmethod
    def get_match_path_to_dir(cls, path):
        webdav_paths = cls.objects.all()
        if not path.startswith("/"):
            path = "/%s"%path
        path = os.path.dirname(path)
        found = []
        for wdp in webdav_paths:
            if (path.startswith(os.path.normpath(wdp.url_path))
                and os.path.isdir(wdp.local_path)):
                found.append(wdp)
        if found:
            # return the longest matching wdp
            found.sort(lambda a, b: cmp(len(a.url_path), len(b.url_path)))
            return found[-1]
        logger.debug("didn't find any defined paths for '%s'"%path)        
        return None
        

