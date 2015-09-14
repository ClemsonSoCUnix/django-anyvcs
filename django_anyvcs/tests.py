# -*- coding: utf-8 -*-
# Copyright (c) 2014-2015, Clemson University
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
# * Neither the name of Clemson University nor the names of its
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

from django.test import TestCase
from django.test.client import Client
from django.http import Http404
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.encoding import DjangoUnicodeDecodeError
from unittest import skipIf, skipUnless
from .models import Repo
from . import settings
from django_anyvcs import dispatch, shortcuts
import anyvcs.git, anyvcs.hg, anyvcs.svn
import gzip
import json
import os
import shutil
import subprocess
import tempfile

DEVNULL = open(os.devnull, 'wb')
GIT = 'git'

URI_FORMAT = {
  ('git', 'ssh'): "{user}@{hostname}:{path}",
  ('svn', 'ssh'): "svn+ssh://{user}@{hostname}/{path}",
  ('hg', 'ssh'): "ssh://{user}@{hostname}/{path}",
  ('git', 'anonymous-ssh'): "{anonymous}@{hostname}:{path}",
  ('svn', 'anonymous-ssh'): "svn+ssh://{anonymous}@{hostname}/{path}",
  ('hg', 'anonymous-ssh'): "ssh://{anonymous}@{hostname}/{path}",
}

URI_CONTEXT = {
  'anonymous': 'anonymous',
  'user': 'user',
  'hostname': 'hostname',
}

class BaseTestCase(TestCase):
  def setUp(self):
    self.original_root = settings.VCSREPO_ROOT
    settings.VCSREPO_ROOT = tempfile.mkdtemp(prefix='anyvcs-test.')
    self.original_uri_format = settings.VCSREPO_URI_FORMAT
    settings.VCSREPO_URI_FORMAT = URI_FORMAT
    self.original_uri_context = settings.VCSREPO_URI_CONTEXT
    settings.VCSREPO_URI_CONTEXT = URI_CONTEXT

  def tearDown(self):
    Repo.objects.all().delete()
    shutil.rmtree(settings.VCSREPO_ROOT)
    settings.VCSREPO_ROOT = self.original_root
    settings.VCSREPO_URI_FORMAT = self.original_uri_format
    settings.VCSREPO_URI_CONTEXT = self.original_uri_context

  def assertPathExists(self, path):
    if isinstance(path, (tuple, list)):
      path = os.path.join(*path)
    if not os.path.exists(path):
      raise AssertionError("Path does not exist: ", path)

  def assertPathNotExists(self, path):
    if isinstance(path, (tuple, list)):
      path = os.path.join(*path)
    try:
      self.assertPathExists(path)
    except AssertionError:
      return
    raise AssertionError("Path exists: ", path)

class TestingFrameworkTestCase(BaseTestCase):

  def test_assert_path_not_exists(self):
    path = tempfile.mkdtemp(prefix='django-anyvcs-path-exists')
    self.assertPathNotExists('/path/does/not/exist')
    self.assertPathNotExists(['/path', 'does', 'not', 'exist'])
    self.assertRaises(AssertionError, self.assertPathNotExists, path)
    self.assertRaises(AssertionError, self.assertPathNotExists, ['/'] + path.split(os.path.pathsep))
    os.rmdir(path)

  def test_assert_path_exists(self):
    path = tempfile.mkdtemp(prefix='django-anyvcs-path-exists')
    self.assertRaises(AssertionError, self.assertPathExists, '/path/does/not/exist')
    self.assertRaises(AssertionError, self.assertPathExists, ['/path', 'does', 'not', 'exist'])
    self.assertPathExists(path)
    self.assertPathExists(['/'] + path.split(os.path.pathsep))
    os.rmdir(path)

class FixtureTestCase(BaseTestCase):
  fixtures = ['django_anyvcs_basic.json']

  def setUp(self):
    # Can't call super() here because fixtures are loaded before setUp()
    self.repo = Repo.objects.get(name='repo')

  def tearDown(self):
    Repo.objects.all().delete()

  def test_path_exists(self):
    self.assertPathExists(self.repo.abspath)

class CreateRepoTestCase(BaseTestCase):
  def test_invalid_names(self):
    for name in ('$', '/', 'a//b'):
      repo = Repo(name=name, path='repo', vcs='git')
      self.assertRaises(ValidationError, repo.full_clean)

  def test_invalid_paths(self):
    for path in ('.', '..', 'a/..', '../a', '.a', '.a/a', 'a/.a'):
      repo = Repo(name='repo', path=path, vcs='git')
      self.assertRaises(ValidationError, repo.full_clean)

  def test_invalid_vcs(self):
    repo = Repo(name='repo', path='repo', vcs='invalid')
    self.assertRaises(ValidationError, repo.full_clean)

  def test_git(self):
    repo = Repo(name='a', path='b', vcs='git')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'b')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'b'))
    self.assertIsInstance(repo.repo, anyvcs.git.GitRepo)

  def test_git_without_path(self):
    repo = Repo(name='a', vcs='git')
    repo.full_clean()
    repo.save()
    self.assertIsInstance(repo.repo, anyvcs.git.GitRepo)

  def test_git_absolute_path(self):
    d = tempfile.mkdtemp(prefix='anyvcs-test.')
    path = os.path.join(d, 'repo')
    repo = Repo(name='a', path=path, vcs='git')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, path)
    self.assertEqual(repo.abspath, path)
    self.assertIsInstance(repo.repo, anyvcs.git.GitRepo)
    shutil.rmtree(d)

  def test_hg(self):
    repo = Repo(name='a', path='b', vcs='hg')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'b')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'b'))
    self.assertIsInstance(repo.repo, anyvcs.hg.HgRepo)

  def test_hg_without_path(self):
    repo = Repo(name='a', vcs='hg')
    repo.full_clean()
    repo.save()
    self.assertIsInstance(repo.repo, anyvcs.hg.HgRepo)

  def test_hg_absolute_path(self):
    d = tempfile.mkdtemp(prefix='anyvcs-test.')
    path = os.path.join(d, 'repo')
    repo = Repo(name='a', path=path, vcs='hg')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, path)
    self.assertEqual(repo.abspath, path)
    self.assertIsInstance(repo.repo, anyvcs.hg.HgRepo)
    shutil.rmtree(d)

  def test_svn(self):
    repo = Repo(name='a', path='b', vcs='svn')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, os.path.join('svn', 'a'))
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'svn', 'a'))
    self.assertIsInstance(repo.repo, anyvcs.svn.SvnRepo)

  def test_svn_without_path(self):
    repo = Repo(name='a', vcs='svn')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, os.path.join('svn', 'a'))
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'svn', 'a'))
    self.assertIsInstance(repo.repo, anyvcs.svn.SvnRepo)

  def test_svn_absolute_path(self):
    d = tempfile.mkdtemp(prefix='anyvcs-test.')
    path = os.path.join(d, 'repo')
    repo = Repo(name='a', path=path, vcs='svn')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, os.path.join('svn', 'a'))
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'svn', 'a'))
    self.assertIsInstance(repo.repo, anyvcs.svn.SvnRepo)
    shutil.rmtree(d)

class ChangeRepoTestCase(BaseTestCase):
  def test_rename_git(self):
    repo = Repo(name='a', vcs='git')
    repo.full_clean()
    repo.save()
    old_path = repo.path
    repo.name = 'b'
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.name, 'b')
    self.assertEqual(repo.path, old_path)
    self.assertPathExists(repo.abspath)

  def test_move_git(self):
    repo = Repo(name='a', vcs='git')
    repo.full_clean()
    repo.save()
    old_abspath = repo.abspath
    repo.path = 'b'
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.name, 'a')
    self.assertEqual(repo.path, 'b')
    self.assertPathExists(repo.abspath)
    self.assertPathNotExists(old_abspath)

  def test_rename_svn(self):
    repo = Repo(name='a', vcs='svn')
    repo.full_clean()
    repo.save()
    repo.name = 'b'
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.name, 'b')
    self.assertEqual(repo.path, os.path.join('svn', 'b'))
    self.assertPathExists(repo.abspath)

  def test_move_svn(self):
    repo = Repo(name='a', vcs='svn')
    repo.full_clean()
    repo.save()
    repo.path = 'b'
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.name, 'a')
    self.assertEqual(repo.path, os.path.join('svn', 'a'))
    self.assertPathExists(repo.abspath)

class CannotDeleteSymlinkTestCase(BaseTestCase):
  def test(self):
    os.mkdir(os.path.join(settings.VCSREPO_ROOT, 'svn.target'))
    os.symlink('svn.target', os.path.join(settings.VCSREPO_ROOT, 'svn'))
    repo = Repo(name='a', vcs='svn')
    repo.full_clean()
    repo.save()
    repo.delete()

class LookupTestCase(BaseTestCase):
  @classmethod
  def setUpClass(cls):
    super(LookupTestCase, cls).setUpClass()
    cls.user1 = User.objects.create(username='user1')
    cls.user2 = User.objects.create(username='user2')
    cls.group1 = Group.objects.create(name='group1')
    cls.group2 = Group.objects.create(name='group2')
    cls.group1.user_set.add(cls.user1)
    cls.group2.user_set.add(cls.user2)

  @classmethod
  def tearDownClass(cls):
    User.objects.all().delete()
    Group.objects.all().delete()
    super(LookupTestCase, cls).tearDownClass()

  def test_public_read_anonymous(self):
    vcs = 'git'
    for public_read, public_rights in ((False, '-'), (True, 'r')):
      repo = Repo.objects.create(
        name = 'repo',
        path = 'repo',
        vcs = vcs,
        public_read = public_read,
      )
      client = Client()
      url = reverse('django_anyvcs.views.access', args=(repo.name,))
      response = client.get(url)
      self.assertEqual(response.status_code, 200)
      self.assertIn('Content-Type', response)
      self.assertEqual(response['Content-Type'], 'application/json')
      document = json.loads(response.content)
      self.assertIn('path', document)
      self.assertEqual(document['path'], os.path.join(settings.VCSREPO_ROOT, 'repo'))
      self.assertIn('vcs', document)
      self.assertEqual(document['vcs'], vcs)
      self.assertIn('rights', document)
      self.assertEqual(document['rights'], public_rights)
      repo.delete()

  def test_public_read_user(self):
    vcs = 'hg'
    for public_read, public_rights in ((False, '-'), (True, 'r')):
      repo = Repo.objects.create(
        name = 'repo',
        path = 'repo',
        vcs = vcs,
        public_read = public_read,
      )
      client = Client()
      url = reverse('django_anyvcs.views.access', args=(repo.name,))
      response = client.get(url, {'u': self.user1.username})
      self.assertEqual(response.status_code, 200)
      self.assertIn('Content-Type', response)
      self.assertEqual(response['Content-Type'], 'application/json')
      document = json.loads(response.content)
      self.assertIn('path', document)
      self.assertEqual(document['path'], os.path.join(settings.VCSREPO_ROOT, 'repo'))
      self.assertIn('vcs', document)
      self.assertEqual(document['vcs'], vcs)
      self.assertIn('rights', document)
      self.assertEqual(document['rights'], public_rights)
      repo.delete()

  @skipUnless(
    settings.VCSREPO_USE_USER_RIGHTS,
    "not using UserRights"
  )
  def test_user_overrides_public_read(self):
    from .models import UserRights
    vcs = 'git'
    for public_read, public_rights in ((False, '-'), (True, 'r')):
      for user_rights in ('-', 'r', 'rw'):
        repo = Repo.objects.create(
          name = 'repo',
          path = 'repo',
          vcs = vcs,
          public_read = public_read,
        )
        UserRights.objects.create(
          repo = repo,
          user = self.user1,
          rights = user_rights,
        )
        client = Client()
        url = reverse('django_anyvcs.views.access', args=(repo.name,))
        response = client.get(url, {'u': self.user1.username})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Type', response)
        self.assertEqual(response['Content-Type'], 'application/json')
        document = json.loads(response.content)
        self.assertIn('path', document)
        self.assertEqual(document['path'], os.path.join(settings.VCSREPO_ROOT, 'repo'))
        self.assertIn('vcs', document)
        self.assertEqual(document['vcs'], vcs)
        self.assertIn('rights', document)
        self.assertEqual(document['rights'], user_rights)
        repo.delete()

  @skipUnless(
    settings.VCSREPO_USE_GROUP_RIGHTS,
    "not using GroupRights"
  )
  def test_group_overrides_public_read(self):
    from .models import GroupRights
    vcs = 'hg'
    for public_read, public_rights in ((False, '-'), (True, 'r')):
      for group_rights in ('-', 'r', 'rw'):
        repo = Repo.objects.create(
          name = 'repo',
          path = 'repo',
          vcs = vcs,
          public_read = public_read,
        )
        GroupRights.objects.create(
          repo = repo,
          group = self.group1,
          rights = group_rights,
        )
        client = Client()
        url = reverse('django_anyvcs.views.access', args=(repo.name,))
        response = client.get(url, {'u': self.user1.username})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Type', response)
        self.assertEqual(response['Content-Type'], 'application/json')
        document = json.loads(response.content)
        self.assertIn('path', document)
        self.assertEqual(document['path'], os.path.join(settings.VCSREPO_ROOT, 'repo'))
        self.assertIn('vcs', document)
        self.assertEqual(document['vcs'], vcs)
        self.assertIn('rights', document)
        self.assertEqual(document['rights'], group_rights)
        repo.delete()

  @skipUnless(
    settings.VCSREPO_USE_USER_RIGHTS and settings.VCSREPO_USE_GROUP_RIGHTS,
    "not using UserRights and GroupRights"
  )
  def test_user_overrides_group_rights(self):
    from .models import UserRights, GroupRights
    vcs = 'git'
    for group_rights in ('-', 'r', 'rw'):
      for user_rights in ('-', 'r', 'rw'):
        repo = Repo.objects.create(
          name = 'repo',
          path = 'repo',
          vcs = vcs,
        )
        UserRights.objects.create(
          repo = repo,
          user = self.user1,
          rights = user_rights,
        )
        GroupRights.objects.create(
          repo = repo,
          group = self.group1,
          rights = group_rights,
        )
        client = Client()
        url = reverse('django_anyvcs.views.access', args=(repo.name,))
        response = client.get(url, {'u': self.user1.username})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Type', response)
        self.assertEqual(response['Content-Type'], 'application/json')
        document = json.loads(response.content)
        self.assertIn('path', document)
        self.assertEqual(document['path'], os.path.join(settings.VCSREPO_ROOT, 'repo'))
        self.assertIn('vcs', document)
        self.assertEqual(document['vcs'], vcs)
        self.assertIn('rights', document)
        self.assertEqual(document['rights'], user_rights)
        repo.delete()

  def test_rights_function(self):
    repo = Repo.objects.create(
      name = 'repo',
      path = 'repo',
      vcs = 'git',
    )
    original_rights_function = settings.VCSREPO_RIGHTS_FUNCTION
    try:
      for rights in ('-', 'r', 'rw'):
        def f(r, u):
          self.assertEqual(repo, r)
          self.assertEqual(self.user1, u)
          return rights
        settings.VCSREPO_RIGHTS_FUNCTION = f
        client = Client()
        url = reverse('django_anyvcs.views.access', args=(repo.name,))
        response = client.get(url, {'u': self.user1.username})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Type', response)
        self.assertEqual(response['Content-Type'], 'application/json')
        document = json.loads(response.content)
        self.assertIn('rights', document)
        self.assertEqual(document['rights'], rights)
    finally:
      settings.VCSREPO_RIGHTS_FUNCTION = original_rights_function

class SvnAuthzTestCase(BaseTestCase):
  def setUp(self):
    from ConfigParser import RawConfigParser
    super(SvnAuthzTestCase, self).setUp()
    repo = Repo(name='a', vcs='svn')
    repo.full_clean()
    repo.save()
    self.repo = repo
    self.authz = os.path.join(repo.abspath, 'conf', 'authz')
    self.config = RawConfigParser(allow_no_value=True)
    self.user1 = User.objects.create(username='user1')
    self.user2 = User.objects.create(username='user2')
    self.group1 = Group.objects.create(name='group1')
    self.group1.user_set.add(self.user1)

  def tearDown(self):
    User.objects.all().delete()
    Group.objects.all().delete()
    super(SvnAuthzTestCase, self).tearDown()

  @skipUnless(
    settings.VCSREPO_USE_USER_RIGHTS
    and settings.VCSREPO_USER_MODEL == 'auth.User',
    "not using UserRights with auth.User"
  )
  def test_add_user_rights(self):
    from .models import UserRights
    rights = UserRights.objects.create(
      repo = self.repo,
      user = self.user1,
      rights = 'r',
    )
    self.config.read(self.authz)
    self.assertTrue(self.config.has_section('/'))
    self.assertTrue(self.config.has_option('/', self.user1.username))
    self.assertEqual(self.config.get('/', self.user1.username), 'r')

  @skipUnless(
    settings.VCSREPO_USE_USER_RIGHTS
    and settings.VCSREPO_USER_MODEL == 'auth.User',
    "not using UserRights with auth.User"
  )
  def test_remove_user_rights(self):
    from .models import UserRights
    rights = UserRights.objects.create(
      repo = self.repo,
      user = self.user1,
      rights = 'r',
    )
    rights.delete()
    self.config.read(self.authz)
    self.assertTrue(self.config.has_section('/'))
    self.assertFalse(self.config.has_option('/', self.user1.username))

  @skipUnless(
    settings.VCSREPO_USE_GROUP_RIGHTS
    and settings.VCSREPO_USER_MODEL == 'auth.User'
    and settings.VCSREPO_GROUP_MODEL == 'auth.Group',
    "not using GroupRights with auth.User and auth.Group"
  )
  def test_add_group_rights(self):
    from .models import GroupRights
    rights = GroupRights.objects.create(
      repo = self.repo,
      group = self.group1,
      rights = 'r',
    )
    g = '@' + self.group1.name
    self.config.read(self.authz)
    self.assertTrue(self.config.has_section('groups'))
    self.assertTrue(self.config.has_option('groups', g))
    self.assertEqual(self.config.get('groups', g), self.user1.username)
    self.assertTrue(self.config.has_section('/'))
    self.assertTrue(self.config.has_option('/', g))
    self.assertEqual(self.config.get('/', g), 'r')

  @skipUnless(
    settings.VCSREPO_USE_GROUP_RIGHTS
    and settings.VCSREPO_USER_MODEL == 'auth.User'
    and settings.VCSREPO_GROUP_MODEL == 'auth.Group',
    "not using GroupRights with auth.User and auth.Group"
  )
  def test_remove_group_rights(self):
    from .models import GroupRights
    rights = GroupRights.objects.create(
      repo = self.repo,
      group = self.group1,
      rights = 'r',
    )
    rights.delete()
    g = '@' + self.group1.name
    self.config.read(self.authz)
    if self.config.has_section('groups'):
      self.assertFalse(self.config.has_option('groups', g))
    self.assertTrue(self.config.has_section('/'))
    self.assertFalse(self.config.has_option('/', g))

  @skipUnless(
    settings.VCSREPO_USE_GROUP_RIGHTS
    and settings.VCSREPO_USER_MODEL == 'auth.User'
    and settings.VCSREPO_GROUP_MODEL == 'auth.Group',
    "not using GroupRights with auth.User and auth.Group"
  )
  def test_add_user_to_group(self):
    from .models import GroupRights
    rights = GroupRights.objects.create(
      repo = self.repo,
      group = self.group1,
      rights = 'r',
    )
    self.group1.user_set.add(self.user2)
    g = '@' + self.group1.name
    self.config.read(self.authz)
    self.assertTrue(self.config.has_section('groups'))
    self.assertTrue(self.config.has_option('groups', g))
    members = set(map(str.strip, self.config.get('groups', g).split(',')))
    self.assertEqual(members, set([self.user1.username, self.user2.username]))
    self.assertTrue(self.config.has_section('/'))
    self.assertTrue(self.config.has_option('/', g))
    self.assertEqual(self.config.get('/', g), 'r')

  @skipUnless(
    settings.VCSREPO_USE_GROUP_RIGHTS
    and settings.VCSREPO_USER_MODEL == 'auth.User'
    and settings.VCSREPO_GROUP_MODEL == 'auth.Group',
    "not using GroupRights with auth.User and auth.Group"
  )
  def test_remove_user_from_group(self):
    from .models import GroupRights
    rights = GroupRights.objects.create(
      repo = self.repo,
      group = self.group1,
      rights = 'r',
    )
    self.group1.user_set.remove(self.user1)
    g = '@' + self.group1.name
    self.config.read(self.authz)
    self.assertTrue(self.config.has_section('groups'))
    self.assertTrue(self.config.has_option('groups', g))
    self.assertEqual(self.config.get('groups', g), '')
    self.assertTrue(self.config.has_section('/'))
    self.assertTrue(self.config.has_option('/', g))
    self.assertEqual(self.config.get('/', g), 'r')

class RepoUriTestCase(BaseTestCase):
  def test_svn(self):
    svn = Repo.objects.create(name='svn', vcs='svn', path='thesvn')
    correct = 'svn+ssh://user@hostname/svn'
    self.assertEqual(svn.ssh_uri, correct)
    svn.delete()

  def test_git(self):
    git = Repo.objects.create(name='git', vcs='git', path='thegit')
    correct = 'user@hostname:git'
    self.assertEqual(git.ssh_uri, correct)
    git.delete()

  def test_hg(self):
    hg = Repo.objects.create(name='hg', vcs='hg', path='thehg')
    correct = 'ssh://user@hostname/hg'
    self.assertEqual(hg.ssh_uri, correct)
    hg.delete()

  def test_anonymous_svn(self):
    svn = Repo.objects.create(name='svn', vcs='svn', path='thesvn')
    correct = 'svn+ssh://anonymous@hostname/svn'
    self.assertEqual(svn.anonymous_ssh_uri, correct)
    svn.delete()

  def test_anonymous_git(self):
    git = Repo.objects.create(name='git', vcs='git', path='thegit')
    correct = 'anonymous@hostname:git'
    self.assertEqual(git.anonymous_ssh_uri, correct)
    git.delete()

  def test_anonymous_hg(self):
    hg = Repo.objects.create(name='hg', vcs='hg', path='thehg')
    correct = 'ssh://anonymous@hostname/hg'
    self.assertEqual(hg.anonymous_ssh_uri, correct)
    hg.delete()

class RequestTestCase(BaseTestCase):

  def setUp(self):
    self.original_dispatch_VCSREPO_ROOT = dispatch.VCSREPO_ROOT
    dispatch.VCSREPO_ROOT = settings.VCSREPO_ROOT

  def tearDown(self):
    dispatch.VCSREPO_ROOT = self.original_dispatch_VCSREPO_ROOT

  def test_git_cmd1(self):
    request = dispatch.get_request(['git-upload-pack', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    cmd = request.get_command()
    expected = ['git', 'shell', '-c',
                "git-upload-pack 'path/to/code'"]
    self.assertEqual(expected, cmd)

  def test_git_cmd2(self):
    request = dispatch.get_request(['git-upload-pack', 'bob/code'])
    request.data = {'rights': '', 'path': 'path/to/code'}
    self.assertRaises(dispatch.DispatchException, request.get_command)

  def test_git_cmd3(self):
    request = dispatch.get_request(['git-receive-pack', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    self.assertRaises(dispatch.DispatchException, request.get_command)

  def test_git_cmd4(self):
    request = dispatch.get_request(['git-upload-pack', '--someflag', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    cmd = request.get_command()
    expected = ['git', 'shell', '-c',
                "git-upload-pack 'path/to/code'"]
    self.assertEqual(expected, cmd)

  def test_git_repo_name1(self):
    request = dispatch.get_request(['git-upload-pack', 'bob/code'])
    self.assertEqual('bob/code', request.repo_name)

  def test_git_repo_name1(self):
    request = dispatch.get_request(['git-upload-pack', 'bob/code.git'])
    self.assertEqual('bob/code', request.repo_name)

  def test_git_noname(self):
    self.assertRaises(dispatch.DispatchException, dispatch.get_request, ['git-receive-pack'])

  def test_hg_cmd1(self):
    '''Repository specified with -R
    '''
    request = dispatch.get_request(['hg', '-R', 'bob/code'])
    request.data = {'rights': 'rw', 'path': 'path/to/code'}
    cmd = request.get_command()
    expected = ['hg', '-R', 'path/to/code', 'serve', '--stdio']
    self.assertEqual(expected, cmd)

  def test_hg_cmd2(self):
    '''Repository specified with --repository
    '''
    request = dispatch.get_request(['hg', '--repository', 'bob/code'])
    request.data = {'rights': 'rw', 'path': 'path/to/code'}
    cmd = request.get_command()
    expected = ['hg', '-R', 'path/to/code', 'serve', '--stdio']
    self.assertEqual(expected, cmd)

  def test_hg_cmd3(self):
    '''Read-only access.
    '''
    request = dispatch.get_request(['hg', '--repository', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    cmd = request.get_command()
    expected = ['hg', '-R', 'path/to/code', 'serve', '--stdio',
        '--config',
        'hooks.prechangegroup.readonly=echo "Error: Permission denied (read-only)" >&2; false',
        '--config',
        'hooks.prepushkey.readonly=echo "Error: Permission denied (read-only)" >&2; false',
    ]
    self.assertEqual(expected, cmd)

  def test_svn_cmd1(self):
    '''Without username.
    '''
    request = dispatch.get_request(['svnserve', '--root', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    cmd = request.get_command()
    expected = ['svnserve',
                '--root',  os.path.join(settings.VCSREPO_ROOT, 'svn'),
                '--tunnel']
    self.assertEqual(expected, cmd)

  def test_svn_cmd2(self):
    '''With username.
    '''
    request = dispatch.get_request(['svnserve', '--root', 'bob/code'], 'bob')
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    cmd = request.get_command()
    expected = ['svnserve',
                '--root',  os.path.join(settings.VCSREPO_ROOT, 'svn'),
                '--tunnel',
                '--tunnel-user', 'bob']
    self.assertEqual(expected, cmd)

  def test_bad_command1(self):
    self.assertRaises(dispatch.DispatchException, dispatch.get_request, ['rm', '-rf', '/'])

  def test_hg_postprocess(self):
    request = dispatch.get_request(['hg', '--repository', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    result = request.postprocess('hg: cloning from path/to/code')
    expected = 'hg: cloning from bob/code'
    self.assertEqual(expected, result)

class PristineTestCase(BaseTestCase):
  '''
  Normal, pristine repository.
  '''

  def setUp(self):
    super(PristineTestCase, self).setUp()
    self.repo = Repo(name='repo', vcs='git')
    self.repo.full_clean()
    self.repo.save()

  def test_get_entry_or_404_fail1(self):
    self.assertRaises(Http404, shortcuts.get_entry_or_404,
                      self.repo, 'notexist', 'notexist')

class NormalContentsTestCase(BaseTestCase):
  '''
  Repository with some contents for testing purposes.

  * rev1: One of every file type, including subdirs.
  * rev2: Empty tree.
  * rev3: Text and binary files.

  Structure at rev1:
  .
  ├── a
  ├── b
  │   └── c
  └── d -> a

  Structure at rev3:
  .
  ├── encoding.txt
  ├── text.txt
  └── binary.gz

  '''

  def setUp(self):
    super(NormalContentsTestCase, self).setUp()
    self.repo = Repo(name='repo', vcs='git')
    self.repo.full_clean()
    self.repo.save()

    # Basic repository setup.
    wc = tempfile.mktemp()
    cmd = [GIT, 'clone', '-q', self.repo.abspath, wc]
    subprocess.check_call(cmd, stderr=DEVNULL)
    setup_git(cwd=wc)

    # rev1 setup
    with open(os.path.join(wc, 'a'), 'w') as fp: pass
    os.makedirs(os.path.join(wc, 'b'))
    with open(os.path.join(wc, 'b', 'c'), 'w') as fp: pass
    os.symlink('a', os.path.join(wc, 'd'))
    cmd = [GIT, 'add', '-A', '.']
    subprocess.check_call(cmd, cwd=wc)
    cmd = [GIT, 'commit', '-q', '-m', 'initial commit']
    subprocess.check_call(cmd, cwd=wc)

    # rev2 setup
    cmd = [GIT, 'rm', '-rq', '.']
    subprocess.check_call(cmd, cwd=wc)
    cmd = [GIT, 'commit', '-q', '-m', 'remove all files']
    subprocess.check_call(cmd, cwd=wc)

    # rev3 setup
    with open(os.path.join(wc, 'text.txt'), 'w') as fp:
      fp.write('hello\n')
    with open(os.path.join(wc, 'encoding.txt'), 'w') as fp:
      fp.write(u'P\xe9rez\n'.encode('latin1'))
    with gzip.open(os.path.join(wc, 'binary.gz'), 'wb') as fp:
      fp.write('hello\n')
    cmd = [GIT, 'add', '-A', '.']
    subprocess.check_call(cmd, cwd=wc)
    cmd = [GIT, 'commit', '-q', '-m', 'text and binary file']
    subprocess.check_call(cmd, cwd=wc)

    # Push the result.
    cmd = [GIT, 'push', '-q', '-u', 'origin', 'master']
    subprocess.check_call(cmd, cwd=wc, stdout=DEVNULL)

    # Set up some easy names.
    self.branch = 'master'
    self.rev1 = self.repo.repo.canonical_rev(self.branch + '~2')
    self.rev2 = self.repo.repo.canonical_rev(self.branch + '~1')
    self.rev3 = self.repo.repo.canonical_rev(self.branch + '~0')
    shutil.rmtree(wc)
    self.repo = Repo.objects.get()

  def test_get_entry_or_404_file1(self):
    '''Standard file test'''
    entry = shortcuts.get_entry_or_404(self.repo, self.rev1, '/a')
    self.assertEqual('a', entry.path)
    self.assertEqual('f', entry.type)

  def test_get_entry_or_404_file2(self):
    '''File in directory structure test'''
    entry = shortcuts.get_entry_or_404(self.repo, self.rev1, '/b/c')
    self.assertEqual('b/c', entry.path)
    self.assertEqual('f', entry.type)

  def test_get_entry_or_404_dir1(self):
    '''Standard directory test'''
    entry = shortcuts.get_entry_or_404(self.repo, self.rev1, '/b')
    self.assertEqual('b', entry.path)
    self.assertEqual('d', entry.type)

  def test_get_entry_or_404_dir2(self):
    '''Listing contents of empty tree should not 404'''
    entry = shortcuts.get_entry_or_404(self.repo, self.rev2, '/')
    self.assertEqual('/', entry.path)
    self.assertEqual('d', entry.type)

  def test_get_entry_or_404_link1(self):
    '''Standard link test'''
    entry = shortcuts.get_entry_or_404(self.repo, self.rev1, '/d')
    self.assertEqual('d', entry.path)
    self.assertEqual('l', entry.type)

  def test_get_entry_or_404_report1(self):
    '''Keyword arguments should pass through'''
    entry = shortcuts.get_entry_or_404(self.repo, self.rev1, '/a',
                                       report=('commit',))
    self.assertEqual('a', entry.path)
    self.assertEqual('f', entry.type)
    self.assertEqual(self.rev1, entry.commit)

  def test_get_entry_or_404_fail1(self):
    '''Bad paths raise 404'''
    self.assertRaises(Http404, shortcuts.get_entry_or_404,
                      self.repo, self.rev1, 'notexist')

  def test_get_entry_or_404_fail2(self):
    '''Bad revisions raise 404'''
    self.assertRaises(Http404, shortcuts.get_entry_or_404,
                      self.repo, 'notexist', '/a')

  def test_get_entry_or_404_fail3(self):
    '''Extra bad path test for the empty tree case'''
    self.assertRaises(Http404, shortcuts.get_entry_or_404,
                      self.repo, self.rev2, 'a')

  def test_get_directory_contents1(self):
    '''Basic usage'''
    result = shortcuts.get_directory_contents(self.repo, self.rev1, '/')
    expected = [
      {'name': 'a', 'path': 'a', 'type': 'f', 'url': 'a'},
      {'name': 'b', 'path': 'b', 'type': 'd', 'url': 'b'},
      {'name': 'd', 'path': 'd', 'type': 'l'},
    ]
    self.assertEqual(result, expected)

  def test_get_directory_contents2(self):
    '''Keyword arguments are passed through'''
    result = shortcuts.get_directory_contents(self.repo, self.rev1, '/',
                                              report=('target',))
    expected = [
      {'name': 'a', 'path': 'a', 'type': 'f', 'url': 'a'},
      {'name': 'b', 'path': 'b', 'type': 'd', 'url': 'b'},
      {'name': 'd', 'path': 'd', 'type': 'l', 'target': 'a'},
    ]
    self.assertEqual(result, expected)

  def test_get_directory_contents3(self):
    '''Test reverse sort parameter'''
    result = shortcuts.get_directory_contents(self.repo, self.rev1, '/',
                                              reverse=True)
    expected = [
      {'name': 'd', 'path': 'd', 'type': 'l'},
      {'name': 'b', 'path': 'b', 'type': 'd', 'url': 'b'},
      {'name': 'a', 'path': 'a', 'type': 'f', 'url': 'a'},
    ]
    self.assertEqual(result, expected)

  def test_get_directory_contents4(self):
    '''Test sort key parameter'''
    result = shortcuts.get_directory_contents(self.repo, self.rev1, '/',
                                              key=lambda e: e.type)
    expected = [
      {'name': 'b', 'path': 'b', 'type': 'd', 'url': 'b'},
      {'name': 'a', 'path': 'a', 'type': 'f', 'url': 'a'},
      {'name': 'd', 'path': 'd', 'type': 'l'},
    ]
    self.assertEqual(result, expected)

  def test_get_directory_contents5(self):
    '''Test resolve_commits'''
    result = [e.log.rev for e in
              shortcuts.get_directory_contents(self.repo, self.rev1, '/',
                                               resolve_commits=True)]
    log = self.repo.repo.log(revrange=self.rev1)
    expected = [self.rev1] * 3
    self.assertEqual(result, expected)

  def test_get_directory_contents_subdir1(self):
    '''Basic usage'''
    result = shortcuts.get_directory_contents(self.repo, self.rev1, '/b')
    expected = [
      {'name': '..', 'path': '', 'type': 'd', 'url': '..'},
      {'name': 'c', 'path': 'b/c', 'type': 'f', 'url': 'c'},
    ]
    self.assertEqual(result, expected)

  def test_get_directory_contents_subdir2(self):
    '''Disallow parent paths'''
    result = shortcuts.get_directory_contents(self.repo, self.rev1, '/b',
                                              parents=False)
    expected = [
      {'name': 'c', 'path': 'b/c', 'type': 'f', 'url': 'c'},
    ]
    self.assertEqual(result, expected)

  def test_get_directory_contents_subdir3(self):
    '''Using a custom reverse_func'''
    reverse_func = lambda e: 'http://example.com/repo/' + e.path
    result = shortcuts.get_directory_contents(self.repo, self.rev1, '/b',
                                              reverse_func=reverse_func)
    expected = [
      {'name': '..', 'path': '', 'type': 'd', 'url': 'http://example.com/repo/'},
      {'name': 'c', 'path': 'b/c', 'type': 'f', 'url': 'http://example.com/repo/b/c'},
    ]
    self.assertEqual(result, expected)

  def test_render_file1(self):
    '''Basic text gets rendered into the template'''
    result = shortcuts.render_file('raw.html',
                                   self.repo, self.rev3, '/text.txt')
    self.assertEqual('text/html; charset=utf-8', result['Content-Type'])

  def test_render_file2(self):
    '''Raw argument adds mimetype and returns the file.'''
    result = shortcuts.render_file('raw.html',
                                   self.repo, self.rev3, '/text.txt',
                                   raw=True)
    self.assertEqual('text/plain', result['Content-Type'])

  def test_render_file3(self):
    '''Test raw flag with mimetype override'''
    result = shortcuts.render_file('raw.html',
                                   self.repo, self.rev3, '/text.txt',
                                   file_mimetype='text/x-csrc',
                                   raw=True)
    self.assertEqual('text/x-csrc', result['Content-Type'])

  def test_render_file4(self):
    '''Non-text files get passed through raw.'''
    result = shortcuts.render_file('raw.html',
                                   self.repo, self.rev3, '/binary.gz')
    self.assertEqual('application/octet-stream', result['Content-Type'])

  def test_render_file5(self):
    '''Encoding errors are properly raised.'''
    with self.assertRaises(DjangoUnicodeDecodeError):
      shortcuts.render_file('raw.html',
                            self.repo, self.rev3, '/encoding.txt')

  def test_render_file6(self):
    '''The `catch_endcoding_errors` argument handles encoding errors.'''
    result = shortcuts.render_file('raw.html',
                                   self.repo, self.rev3, '/encoding.txt',
                                   catch_encoding_errors=True)
    self.assertEqual('text/plain', result['Content-Type'])

  def test_render_file7(self):
    '''Test the textfilter parameter'''
    def textfilter(contents, path, mimetype):
      self.assertIsInstance(contents, basestring)
      self.assertEqual('/text.txt', path)
      self.assertEqual('text/plain', mimetype)
      return 'test - ' + contents
    response = shortcuts.render_file('raw.html',
                                     self.repo, self.rev3, '/text.txt',
                                     textfilter=textfilter)
    self.assertEqual('test - hello\n\n', response.content)

  def test_render_file8(self):
    '''Test the context'''
    response = self.client.get('/browse/repo/%s/text.txt' % self.rev3)
    self.assertEqual(self.repo.pk, response.context['repo'].pk)
    self.assertEqual('/text.txt', response.context['path'])
    self.assertEqual(self.rev3, response.context['rev'])
    self.assertIsInstance(response.context['contents'], basestring)


def setup_git(**kw):
  cmd = [GIT, 'config', 'user.name', 'Test User']
  subprocess.check_call(cmd, **kw)
  cmd = [GIT, 'config', 'user.email', 'test@example.com']
  subprocess.check_call(cmd, **kw)
