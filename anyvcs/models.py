from django.db import models
from django.db.models.signals import post_save, post_delete
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
  ('-', 'Deny'),
  ('r', 'Read-Only'),
  ('rw', 'Read-Write'),
)

name_rx = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.+-]*$')

class Repo(models.Model):
  name = models.CharField(max_length=100, unique=True, db_index=True)
  vcs = models.CharField(max_length=3, choices=VCS_CHOICES, default='git')
  public_rights = models.CharField(max_length=2, choices=RIGHTS_CHOICES, default='-')

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
    if self.vcs == 'svn':
      conf_path = os.path.join(self.path, 'conf', 'svnserve.conf')
      with open(conf_path, 'w') as conf:
        conf.write('[general]\n')
        d = { '-': 'none', 'r': 'read', 'rw': 'write' }
        conf.write('anon-access = %s\n' % d[self.public_rights])
        conf.write('authz-db = authz\n')
      self.update_authz()

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

  def update_authz(self):
    if self.vcs == 'svn':
      import fcntl
      authz_path = os.path.join(self.path, 'conf', 'authz')
      d = { '-': '' }
      def rights(r):
        return d.get(r, r)
      with open(authz_path, 'a') as authz:
        authz.seek(0)
        fcntl.lockf(authz, fcntl.LOCK_EX)
        authz.truncate()
        authz.write('[groups]\n')
        for gr in self.grouprights_set.all():
          members = ','.join((u.username for u in gr.group.user_set.all()))
          authz.write('@%s = %s\n' % (gr.group.name, members))
        authz.write('\n[/]\n')
        for ur in self.userrights_set.all():
          authz.write('%s = %s\n' % (ur.user.username, rights(ur.rights)))
        for gr in self.grouprights_set.all():
          authz.write('@%s = %s\n' % (gr.group.name, rights(gr.rights)))
        authz.write('* = %s\n' % rights(self.public_rights))

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

  def post_save(self, created, **kwargs):
    self.repo.update_authz()

  def post_delete(self, **kwargs):
    self.repo.update_authz()

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

  def post_save(self, created, **kwargs):
    self.repo.update_authz()

  def post_delete(self, **kwargs):
    self.repo.update_authz()

def post_save_proxy(sender, instance, **kwargs):
  instance.post_save(**kwargs)

def post_delete_proxy(sender, instance, **kwargs):
  instance.post_delete(**kwargs)

# Repo signals
post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=Repo)
post_delete.connect(post_delete_proxy, dispatch_uid=__name__, sender=Repo)

# UserRights signals
post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=UserRights)
post_delete.connect(post_delete_proxy, dispatch_uid=__name__, sender=UserRights)

# GroupRights signals
post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=GroupRights)
post_delete.connect(post_delete_proxy, dispatch_uid=__name__, sender=GroupRights)
