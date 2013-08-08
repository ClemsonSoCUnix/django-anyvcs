from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from . import settings
import os
import re
import shutil
import subprocess

VCS_CHOICES = (
  ('git', 'Git'),
  ('hg', 'Mercurial'),
  ('svn', 'Subversion'),
)
RIGHTS_CHOICES = (
  ('', 'None'),
  ('r', 'Read-Only'),
  ('rw', 'Read-Write'),
)

name_rx = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.+-]+$')

class Repo(models.Model):
  name = models.CharField(max_length=100, unique=True, db_index=True)
  vcs = models.CharField(max_length=3, choices=VCS_CHOICES, default='git')
  public_rights = models.CharField(max_length=2, choices=RIGHTS_CHOICES, default='', blank=True)

  class Meta:
    verbose_name = 'Repository'
    verbose_name_plural = 'Repositories'

  def __unicode__(self):
    return self.name

  @property
  def relpath(self):
    return self.name

  @property
  def path(self):
    return os.path.join(settings.VCSREPO_ROOT, self.relpath)

  def post_save(self, created, **kwargs):
    if created:
      if self.vcs == 'git':
        cmd = [settings.GIT, 'init', '--bare', self.path]
      elif self.vcs == 'hg':
        cmd = [settings.HG, 'init', self.path]
      elif self.vcs == 'svn':
        cmd = [settings.SVNADMIN, 'create', self.path]
      else:
        assert False, self.vcs
      subprocess.check_call(cmd)

  def post_delete(self, **kwargs):
    shutil.rmtree(self.path)
    d = os.path.dirname(self.path)
    while d != settings.VCSREPO_ROOT:
      try:
        os.rmdir(d)
        d = os.path.dirname(d)
      except OSError, e:
        import errno
        if e.errno != errno.ENOTEMPTY:
          raise
        break

  def clean_fields(self, exclude=None):
    if not exclude or 'name' not in exclude:
      if not name_rx.match(self.name):
        msg = 'Invalid name'
        raise ValidationError({'name': [msg]})

class UserRights(models.Model):
  repo = models.ForeignKey(Repo, db_index=True)
  user = models.ForeignKey(User, db_index=True)
  rights = models.CharField(max_length=2, choices=RIGHTS_CHOICES, default='rw')

  class Meta:
    unique_together = ('repo', 'user')
    verbose_name = 'User Access Rights'
    verbose_name_plural = 'User Access Rights'

  def __unicode__(self):
    return u'%s/%s' % (self.repo, self.user)

class GroupRights(models.Model):
  repo = models.ForeignKey(Repo, db_index=True)
  group = models.ForeignKey(Group, db_index=True)
  rights = models.CharField(max_length=2, choices=RIGHTS_CHOICES, default='rw')

  class Meta:
    unique_together = ('repo', 'group')
    verbose_name = 'Group Access Rights'
    verbose_name_plural = 'Group Access Rights'

  def __unicode__(self):
    return u'%s/%s' % (self.repo, self.group)

@receiver(post_save, sender=Repo, dispatch_uid=__name__)
def post_save_proxy(sender, instance, **kwargs):
  instance.post_save(**kwargs)

@receiver(post_delete, sender=Repo, dispatch_uid=__name__)
def post_delete_proxy(sender, instance, **kwargs):
  instance.post_delete(**kwargs)
