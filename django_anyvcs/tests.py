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

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from unittest import skipIf, skipUnless
from .models import Repo
from . import settings
from django_anyvcs import dispatch
import anyvcs.git, anyvcs.hg, anyvcs.svn
import json
import os
import shutil
import tempfile

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
      raise AssertionError("Path exists: ", path)
    except AssertionError:
      pass

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
    self.assertRaises(Exception, request.get_command)

  def test_git_cmd3(self):
    request = dispatch.get_request(['git-receive-pack', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    self.assertRaises(Exception, request.get_command)

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
    self.assertRaises(Exception, dispatch.get_request, ['git-receive-pack'])

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
        'hooks.prechangegroup.readonly=echo "Error: Permission denied (read-only)" >&2',
        '--config',
        'hooks.prepushkey.readonly=echo "Error: Permission denied (read-only)" >&2',
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
    self.assertRaises(Exception, dispatch.get_request, ['rm', '-rf', '/'])

  def test_hg_postprocess(self):
    request = dispatch.get_request(['hg', '--repository', 'bob/code'])
    request.data = {'rights': 'r', 'path': 'path/to/code'}
    result = request.postprocess('hg: cloning from path/to/code')
    expected = 'hg: cloning from bob/code'
    self.assertEqual(expected, result)
