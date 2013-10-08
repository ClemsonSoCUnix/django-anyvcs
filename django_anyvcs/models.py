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
  path = models.CharField(max_length=100, unique=True, blank=True, verbose_name='Relative Path', help_text='Warning: Changing this does not rename the repository on disk!')
  vcs = models.CharField(max_length=3, choices=VCS_CHOICES, default='git', verbose_name='Version Control System')
  public_read = models.BooleanField(verbose_name='Public Read Access')
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
  def public_rights(self):
    """Provided for backwards compatibility"""
    import warnings
    warn = 'public_rights is deprecated, use public_read instead'
    warnings.warn(warn, DeprecationWarning)
    if self.public_read:
      return 'r'
    else:
      return '-'

  @public_rights.setter
  def public_rights(self, value):
    import warnings
    warn = 'public_rights is deprecated, use public_read instead'
    warnings.warn(warn, DeprecationWarning)
    self.public_read = 'r' in value
    if 'w' in value:
      warn = 'write privilege for public_rights is ignored'
      warnings.warn(warn, RuntimeWarning)

  @property
  def ssh_uri(self):
    return self.get_uri('ssh')

  @property
  def anonymous_ssh_uri(self):
    return self.get_uri('anonymous-ssh')

  def get_uri(self, protocol):
    return self.format_uri(protocol, settings.VCSREPO_URI_CONTEXT) 

  def format_uri(self, protocol, context):
    context = dict(context)
    context['path'] = self.name
    fmt = settings.VCSREPO_URI_FORMAT[(self.vcs, protocol)]
    return fmt.format(**context)

  def post_save(self, created, **kwargs):
    if created:
      try:
        os.makedirs(self.abspath)
      except OSError as e:
        import errno
        if e.errno != errno.EEXIST:
          raise
      self._repo = anyvcs.create(self.abspath, self.vcs)
    if self.vcs == 'svn':
      self.update_local_files()

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
      if name_rx.match(self.name):
        if self.vcs == 'svn':
          # verify we aren't nesting repo names (e.g. a and a/b)
          # this is needed for svn because of the byname symlinks
          # is this a parent of another repo? (is this the a for another a/b)
          qs = type(self).objects.filter(name__startswith=self.name+'/')
          if qs.count() != 0:
            msg = 'This an ancestor of another repository which does not support nesting.'
            err.setdefault('name', []).append(msg)
          # is this a child of another repo? (is this the a/b for another a)
          updirs = []
          p = self.name
          while p:
            p = os.path.dirname(p)
            updirs.append(p)
          qs = type(self).objects.filter(name__in=updirs)
          qs = qs.exclude(vcs='hg')
          if qs.count() != 0:
            msg = 'This a subdirectory of another repository which does not support nesting.'
            err.setdefault('name', []).append(msg)
      else:
        err['name'] = ['Invalid name']
    if not exclude or 'path' not in exclude:
      if not self.path:
        self.path = self.name
      if name_rx.match(self.path):
        # verify we aren't nesting repo paths (e.g. a and a/b)
        # is this a parent of another repo? (is this the a for another a/b)
        if self.vcs != 'hg': # subrepos are ok for hg
          qs = type(self).objects.filter(path__startswith=self.path+'/')
          if qs.count() != 0:
            msg = 'This an ancestor of another repository which does not support nesting.'
            err.setdefault('path', []).append(msg)
        # is this a child of another repo? (is this the a/b for another a)
        updirs = []
        p = self.path
        while p:
          p = os.path.dirname(p)
          updirs.append(p)
        qs = type(self).objects.filter(path__in=updirs)
        qs = qs.exclude(vcs='hg')
        if qs.count() != 0:
          msg = 'This a subdirectory of another repository which does not support nesting.'
          err.setdefault('path', []).append(msg)
      else:
        err['path'] = ['Invalid path']
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

  def update_byname_symlink(self):
    if self.vcs == 'svn':
      import errno
      byname_dir = os.path.join(settings.VCSREPO_ROOT, '.byname')
      link_path = os.path.join(byname_dir, self.name)
      if os.path.isabs(self.path):
        target = self.path
      else:
        target = os.path.join(os.path.pardir, self.path)
      try:
        os.makedirs(byname_dir)
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise
      try:
        if target != os.readlink(link_path):
          os.unlink(link_path)
          os.symlink(target, link_path)
      except OSError as e:
        if e.errno != errno.ENOENT:
          shutil.rmtree(link_path)
        os.symlink(target, link_path)

  def update_local_files(self):
    if self.vcs == 'svn':
      self.update_authz()
      self.update_byname_symlink()

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
