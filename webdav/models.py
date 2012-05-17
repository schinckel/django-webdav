import os
import logging
from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger("webdav")

def _recurse_file_size(d):
    total = 0
    if os.path.isdir(d):
        for filename in os.listdir(d):
            fn = os.path.normpath("%s/%s"%(d, filename))
            total += _recurse_file_size(fn)
    else:
        total = os.path.getsize(d)
    return total


class WebdavPath(models.Model):
    QUOTA_SIZE_MULT = 1024 * 1024 # megs

    url_path = models.CharField(max_length=1024)
    local_path = models.CharField(max_length=1024)
    quota = models.IntegerField()
    owner = models.ForeignKey(User)

    def get_local_path(self, path):
        return os.path.normpath("%s/%s"%(self.local_path, path[len(self.url_path):]))

    @classmethod
    def get_match_path_to_dir(cls, path):
        webdav_paths = cls.objects.all()
        path = os.path.dirname(path)
        # 'tis broken. both /blah and /blah/stuff will match /blash/stuff/other
        # probably have one base dir and go from there...
        for wdp in webdav_paths:
            if path.startswith(os.path.normpath(wdp.url_path)):
                if not os.path.isdir(wdp.local_path):
                    logger.warning("trying to access '%s' using non-existant local path '%s'"%(wdp.url_path, wdp.local_path))
                    return None
                return wdp
        logger.debug("didn't find any defined paths for '%s'"%path)            
        return None
        
    def get_used_quota(self):
        if not os.path.isdir(self.local_path):
            logger.warning("trying to get quota for '%s' using non-existant local path '%s'"%(self.url_path, self.local_path))
            return 0
        return _recurse_file_size(self.local_path)
