# Copyright (c) 2014, Clemson University
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the {organization} nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.db import models
from django.db.models.signals import post_save, post_delete, m2m_changed
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
hidden_path_rx = re.compile(r'(?:^|/)\.')

def makedirs(path):
  try:
    os.makedirs(path)
  except OSError as e:
    import errno
    if e.errno != errno.EEXIST:
      raise

def removedirs(path, stop=None):
  import errno
  while path != stop:
    try:
      os.rmdir(path)
      path = os.path.dirname(path)
    except OSError, e:
      if e.errno == errno.ENOTEMPTY:
        break
      raise

def post_save_proxy(sender, instance, **kwargs):
  instance.post_save(**kwargs)

def post_delete_proxy(sender, instance, **kwargs):
  instance.post_delete(**kwargs)


class Repo(models.Model):
  name = models.CharField(
    max_length = 100,
    unique = True,
    db_index = True,
  )
  path = models.CharField(
    max_length = 100,
    unique = True,
    blank = True,
    help_text = 'Either relative to VCSREPO_ROOT or absolute. Changing this will move the repository on disk.',
  )
  vcs = models.CharField(
    max_length = 3,
    default = 'git',
    choices = VCS_CHOICES,
    verbose_name = 'Version Control System',
  )
  public_read = models.BooleanField(
    default = False,
    verbose_name = 'Public Read Access',
  )
  created = models.DateTimeField(
    null = True,
    auto_now_add = True,
  )
  last_modified = models.DateTimeField(
    null = True,
    auto_now = True,
  )

  class Meta:
    db_table = 'anyvcs_repo'
    ordering = ['name']
    verbose_name = 'Repository'
    verbose_name_plural = 'Repositories'

  def __init__(self, *args, **kwargs):
    super(Repo, self).__init__(*args, **kwargs)
    self._old_path = self.path

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
      makedirs(self.abspath)
      self._repo = anyvcs.create(self.abspath, self.vcs)
    elif self._old_path != self.path:
      makedirs(os.path.dirname(self.abspath))
      old_abspath = os.path.join(settings.VCSREPO_ROOT, self._old_path)
      shutil.move(old_abspath, self.abspath)
      if not os.path.isabs(self._old_path):
        removedirs(os.path.dirname(old_abspath), settings.VCSREPO_ROOT)
    self._old_path = self.path
    if self.vcs == 'svn':
      self.update_svnserve()

  def post_delete(self, **kwargs):
    try:
      shutil.rmtree(self.abspath)
      removedirs(os.path.dirname(self.abspath), settings.VCSREPO_ROOT)
    except OSError as e:
      import errno
      if e.errno != errno.ENOENT:
        raise

  def relocate_path(self):
    if self.vcs == 'svn':
      self.path = os.path.join('svn', self.name)
    else:
      self.path = settings.VCSREPO_PATH_FUNCTION(self)

  def clean_fields(self, exclude=None):
    err = {}
    if not exclude or 'name' not in exclude:
      if not name_rx.match(self.name):
        err['name'] = ['Invalid name']
    if not exclude or 'path' not in exclude:
      if self.vcs == 'svn':
        self.path = os.path.join('svn', self.name)
      elif not self.path:
        self.path = settings.VCSREPO_PATH_FUNCTION(self)
      if hidden_path_rx.search(self.path):
        err['path'] = 'Invalid path'
      if settings.VCSREPO_CHECK_NESTED_PATHS:
        # verify we aren't nesting repo paths (e.g. a and a/b)
        # is this a parent of another repo? (is this the a for another a/b)
        if not (settings.VCSREPO_ALLOW_NESTED_PATHS or self.vcs == 'hg'):
          qs = type(self).objects.filter(path__startswith=self.path+'/')
          if qs.count() != 0:
            msg = 'This an ancestor of another repository which does not support nesting.'
            err.setdefault('path', []).append(msg)
        # is this a child of another repo? (is this the a/b for another a)
        updirs = []
        p = self.path
        while p and p != '/':
          p = os.path.dirname(p)
          updirs.append(p)
        qs = type(self).objects.filter(path__in=updirs)
        if settings.VCSREPO_ALLOW_NESTED_PATHS:
          qs = qs.exclude(vcs='hg')
        if qs.count() != 0:
          msg = 'This a subdirectory of another repository which does not support nesting.'
          err.setdefault('path', []).append(msg)
    if not exclude or 'vcs' not in exclude:
      if not filter(lambda x: x[0] == self.vcs, VCS_CHOICES):
        msg = 'Not a valid VCS type'
        err.setdefault('vcs', []).append(msg)
    if err:
      raise ValidationError(err)

  def update_svnserve(self):
    if self.vcs != 'svn':
      return
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
    with open(authz_path, 'a') as authz:
      authz.seek(0)
      fcntl.lockf(authz, fcntl.LOCK_EX)
      authz.truncate()
      if settings.VCSREPO_GROUP_ACL_FUNCTION:
        authz.write('[groups]\n')
        group_acl = settings.VCSREPO_GROUP_ACL_FUNCTION(self)
        for g in group_acl.keys():
          members = ','.join((u.username for u in g.user_set.all()))
          authz.write('@%s = %s\n' % (g.name, members))
      authz.write('\n[/]\n')
      if settings.VCSREPO_USER_ACL_FUNCTION:
        user_acl = settings.VCSREPO_USER_ACL_FUNCTION(self)
        for u, r in user_acl.iteritems(): 
          authz.write('%s = %s\n' % (u.username, d.get(r, r)))
      if settings.VCSREPO_USE_GROUP_RIGHTS:
        for g, r in group_acl.iteritems():
          authz.write('@%s = %s\n' % (g.name, d.get(r, r)))
      if self.public_read:
        authz.write('* = r\n')

# Repo signals
post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=Repo)
post_delete.connect(post_delete_proxy, dispatch_uid=__name__, sender=Repo)


if settings.VCSREPO_USE_USER_RIGHTS:
  class UserRights(models.Model):
    repo = models.ForeignKey(
      Repo,
      db_index = True,
    )
    user = models.ForeignKey(
      settings.VCSREPO_USER_MODEL,
      db_index = True,
    )
    rights = models.CharField(
      max_length = 2,
      default = 'rw',
      choices = RIGHTS_CHOICES,
    )
    created = models.DateTimeField(
      null = True,
      auto_now_add = True,
    )
    last_modified = models.DateTimeField(
      null = True,
      auto_now = True,
    )

    class Meta:
      db_table = 'anyvcs_userrights'
      unique_together = ('repo', 'user')
      verbose_name = 'User Access Rights'
      verbose_name_plural = 'User Access Rights'

    def __unicode__(self):
      return u'%s/%s' % (self.repo, self.user)

    def post_save(self, created, **kwargs):
      self.repo.update_svnserve()
      self.repo.last_modified = self.last_modified
      self.repo.save()

    def post_delete(self, **kwargs):
      try:
        self.repo.update_svnserve()
        self.repo.last_modified = self.last_modified
        self.repo.save()
      except Repo.DoesNotExist:
        pass

  # UserRights signals
  post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=UserRights)
  post_delete.connect(post_delete_proxy, dispatch_uid=__name__, sender=UserRights)


if settings.VCSREPO_USE_GROUP_RIGHTS:
  class GroupRights(models.Model):
    repo = models.ForeignKey(
      Repo,
      db_index = True,
    )
    group = models.ForeignKey(
      settings.VCSREPO_GROUP_MODEL,
      db_index = True,
    )
    rights = models.CharField(
      max_length = 2,
      default = 'rw',
      choices = RIGHTS_CHOICES,
    )
    created = models.DateTimeField(
      null = True,
      auto_now_add = True,
    )
    last_modified = models.DateTimeField(
      null = True,
      auto_now = True,
    )

    class Meta:
      db_table = 'anyvcs_grouprights'
      unique_together = ('repo', 'group')
      verbose_name = 'Group Access Rights'
      verbose_name_plural = 'Group Access Rights'

    def __unicode__(self):
      return u'%s/%s' % (self.repo, self.group)

    def post_save(self, created, **kwargs):
      self.repo.update_svnserve()
      self.repo.last_modified = self.last_modified
      self.repo.save()

    def post_delete(self, **kwargs):
      try:
        self.repo.update_svnserve()
        self.repo.last_modified = self.last_modified
        self.repo.save()
      except Repo.DoesNotExist:
        pass

  # GroupRights signals
  post_save.connect(post_save_proxy, dispatch_uid=__name__, sender=GroupRights)
  post_delete.connect(post_delete_proxy, dispatch_uid=__name__, sender=GroupRights)

  if (
    settings.VCSREPO_USER_MODEL == 'auth.User'
    and settings.VCSREPO_GROUP_MODEL == 'auth.Group'
  ):
    from django.contrib.auth.models import User

    def group_member_changed(instance, action, **kwargs):
      if action.startswith('post_'):
        qs = GroupRights.objects.filter(group=instance, repo__vcs='svn')
        for gr in qs.select_related('repo'):
          gr.repo.update_svnserve()

    m2m_changed.connect(group_member_changed, dispatch_uid=__name__, sender=User.groups.through)
