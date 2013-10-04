# Copyright 2013 Scott Duckworth
#
# This file is part of django-anyvcs.
#
# django-anyvcs is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-anyvcs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with django-anyvcs.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, post_delete
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from . import settings
import anyvcs
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

name_rx = re.compile(r'^(?:[a-zA-Z0-9][a-zA-Z0-9_.+-]*/)*(?:[a-zA-Z0-9][a-zA-Z0-9_.+-]*)$')

class Repo(models.Model):
  name = models.CharField(max_length=100, unique=True, db_index=True)
  path = models.CharField(max_length=100, unique=True, blank=True)
  vcs = models.CharField(max_length=3, choices=VCS_CHOICES, default='git')
  public_read = models.BooleanField()
  created = models.DateTimeField(auto_now_add=True, null=True)
  last_modified = models.DateTimeField(auto_now=True, null=True)

  class Meta:
    db_table = 'anyvcs_repo'
    verbose_name = 'Repository'
    verbose_name_plural = 'Repositories'

  def __unicode__(self):
    return self.name

  @property
  def abspath(self):
    return os.path.join(settings.VCSREPO_ROOT, self.path)

  @property
  def repo(self):
    try:
      return self._repo
    except AttributeError:
      self._repo = anyvcs.open(self.abspath, self.vcs)
      return self._repo

  @property
  def ssh_uri(self):
    return self.get_uri('ssh')

  def get_uri(self, protocol):
    return self.format_uri(protocol, settings.VCSREPO_URI_CONTEXT) 

  def format_uri(self, protocol, context):
    context = dict(context)
    context['path'] = self.name
    fmt = settings.VCSREPO_URI_FORMAT[(self.vcs, protocol)]
    return fmt.format(**context)

  def post_save(self, created, **kwargs):
    if created:
      self._repo = anyvcs.create(self.abspath, self.vcs)
    if self.vcs == 'svn':
      self.update_authz()

  def post_delete(self, **kwargs):
    shutil.rmtree(self.abspath)
    d = os.path.dirname(self.abspath)
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
    err = {}
    if not exclude or 'name' not in exclude:
      if not name_rx.match(self.name):
        err['name'] = ['Invalid name']
    if not exclude or 'path' not in exclude:
      if not self.path:
        self.path = self.name
      if not name_rx.match(self.path):
        err['path'] = ['Invalid path']
      if 'path' not in err:
        # verify we aren't nesting repos (excluding hg parents, subrepos are ok)
        # is this a parent directory of an existing repo?
        if self.vcs != 'hg':
          qs = type(self).objects.filter(path__startswith=self.path+'/')
          if qs.count() != 0:
            msg = 'This an ancestor of another repository which does not support nesting.'
            err.setdefault('path', []).append(msg)
        # is this a subdirectory of an existing repo?
        updirs = []
        p = self.path
        while p:
          p = os.path.dirname(p)
          updirs.append(p)
        qs = type(self).objects.filter(~Q(vcs='hg')).filter(path__in=updirs)
        if qs.count() != 0:
          msg = 'This a subdirectory of another repository which does not support nesting.'
          err.setdefault('path', []).append(msg)
    if not exclude or 'vcs' not in exclude:
      if not filter(lambda x: x[0] == self.vcs, VCS_CHOICES):
        msg = 'Not a valid VCS type'
        err.setdefault('vcs', []).append(msg)
    if err:
      raise ValidationError(err)

  def update_authz(self):
    if self.vcs == 'svn':
      import fcntl
      conf_path = os.path.join(self.abspath, 'conf', 'svnserve.conf')
      with open(conf_path, 'a') as conf:
        conf.seek(0)
        fcntl.lockf(conf, fcntl.LOCK_EX)
        conf.truncate()
        conf.write('[general]\n')
        if self.public_read:
          conf.write('anon-access = read\n')
        conf.write('authz-db = authz\n')
      authz_path = os.path.join(self.abspath, 'conf', 'authz')
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
        if self.public_read:
          authz.write('* = r\n')

class UserRights(models.Model):
  repo = models.ForeignKey(Repo, db_index=True)
  user = models.ForeignKey(User, db_index=True)
  rights = models.CharField(max_length=2, choices=RIGHTS_CHOICES, default='rw')
  created = models.DateTimeField(auto_now_add=True, null=True)
  last_modified = models.DateTimeField(auto_now=True, null=True)

  class Meta:
    db_table = 'anyvcs_userrights'
    unique_together = ('repo', 'user')
    verbose_name = 'User Access Rights'
    verbose_name_plural = 'User Access Rights'

  def __unicode__(self):
    return u'%s/%s' % (self.repo, self.user)

  def post_save(self, created, **kwargs):
    self.repo.update_authz()
    self.repo.last_modified = self.last_modified
    self.repo.save()

  def pre_delete(self, **kwargs):
    self.repo.update_authz()
    self.repo.last_modified = self.last_modified
    self.repo.save()

class GroupRights(models.Model):
  repo = models.ForeignKey(Repo, db_index=True)
  group = models.ForeignKey(Group, db_index=True)
  rights = models.CharField(max_length=2, choices=RIGHTS_CHOICES, default='rw')
  created = models.DateTimeField(auto_now_add=True, null=True)
  last_modified = models.DateTimeField(auto_now=True, null=True)

  class Meta:
    db_table = 'anyvcs_grouprights'
    unique_together = ('repo', 'group')
    verbose_name = 'Group Access Rights'
    verbose_name_plural = 'Group Access Rights'

  def __unicode__(self):
    return u'%s/%s' % (self.repo, self.group)

  def post_save(self, created, **kwargs):
    self.repo.update_authz()
    self.repo.last_modified = self.last_modified
    self.repo.save()

  def pre_delete(self, **kwargs):
    self.repo.update_authz()
    self.repo.last_modified = self.last_modified
    self.repo.save()

def post_save_proxy(sender, instance, **kwargs):
  instance.post_save(**kwargs)

def pre_delete_proxy(sender, instance, **kwargs):
  instance.pre_delete(**kwargs)

def post_delete_proxy(sender, instance, **kwargs):
  instance.post_delete(**kwargs)

# Repo signals
post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=Repo)
post_delete.connect(post_delete_proxy, dispatch_uid=__name__, sender=Repo)

# UserRights signals
post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=UserRights)
pre_delete.connect(pre_delete_proxy, dispatch_uid=__name__, sender=UserRights)

# GroupRights signals
post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=GroupRights)
pre_delete.connect(pre_delete_proxy, dispatch_uid=__name__, sender=GroupRights)
