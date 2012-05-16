import os
import logging
from django.db import models

logger = logging.getLogger("webdav")

class WebdavPath(models.Model):
    url_path = models.CharField(max_length=1024)
    local_path = models.CharField(max_length=1024)

    def get_local_path(self, path):
        return os.path.normpath("%s/%s"%(self.local_path, path[len(self.url_path):]))

    @classmethod
    def get_match_path_to_dir(cls, path):
        webdav_paths = cls.objects.all()
        for wdp in webdav_paths:
            if path.startswith(os.path.normpath(wdp.url_path)):
                if not os.path.isdir(wdp.local_path):
                    logger.warning("trying to access '%s' using non-existant local path '%s'"%(wdp.url_path, wdp.local_path))
                    return None
                return wdp
        logger.debug("didn't find any defined paths for '%s'"%path)            
        return None
        
