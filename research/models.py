from django.db import models


# Create your models here.
class ClonedRepository(models.Model):
    repo_url = models.URLField(primary_key=True, max_length=500)
    local_path = models.CharField(max_length=500)
    repo_map = models.JSONField(null=True, blank=True)
    primary_language = models.CharField(max_length=50, null=True, blank=True)
    cloned_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
