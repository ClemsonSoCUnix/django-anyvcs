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
from django_anyvcs.models import Repo, UserRights, GroupRights
from django_anyvcs import settings
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
    self.original_rights_function = settings.VCSREPO_RIGHTS_FUNCTION
    self.original_uri_format = settings.VCSREPO_URI_FORMAT
    settings.VCSREPO_URI_FORMAT = URI_FORMAT
    self.original_uri_context = settings.VCSREPO_URI_CONTEXT
    settings.VCSREPO_URI_CONTEXT = URI_CONTEXT
    settings.VCSREPO_RIGHTS_FUNCTION = None

  def tearDown(self):
    Repo.objects.all().delete()
    shutil.rmtree(settings.VCSREPO_ROOT)
    settings.VCSREPO_ROOT = self.original_root
    settings.VCSREPO_RIGHTS_FUNCTION = self.original_rights_function
    settings.VCSREPO_URI_FORMAT = self.original_uri_format
    settings.VCSREPO_URI_CONTEXT = self.original_uri_context

class CreateRepoTestCase(BaseTestCase):
  def test_invalid_names(self):
    for name in ('$', '/', 'a//b'):
      repo = Repo(name=name, path='repo', vcs='git')
      self.assertRaises(ValidationError, repo.full_clean)

  def test_invalid_paths(self):
    for path in ('/a', '.hidden', 'a//b', '../a', 'a/..', 'a/../b'):
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

  def test_svn(self):
    repo = Repo(name='a', path='b', vcs='svn')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'b')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'b'))
    self.assertIsInstance(repo.repo, anyvcs.svn.SvnRepo)

  def test_svn_without_path(self):
    repo = Repo(name='a', vcs='svn')
    repo.full_clean()
    repo.save()
    self.assertIsInstance(repo.repo, anyvcs.svn.SvnRepo)

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

  def test_user_overrides_public_read(self):
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

  def test_group_overrides_public_read(self):
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

  def test_user_overrides_group_rights(self):
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

class SvnBynameTestCase(BaseTestCase):
  def setUp(self):
    super(BaseTestCase, self).setUp()
    self.repo1 = Repo(name='a/b/c/svn1', vcs='svn')
    self.repo2 = Repo(name='a/svn2', vcs='svn')
    self.repo3 = Repo(name='svn3', vcs='svn')
    self.repo1.full_clean()
    self.repo1.save()
    self.repo2.full_clean()
    self.repo2.save()
    self.repo3.full_clean()
    self.repo3.save()
    self.byname_dir = os.path.join(settings.VCSREPO_ROOT, '.byname')

  def tearDown(self):
    Repo.objects.all().delete()
    super(BaseTestCase, self).tearDown()

  def assertByname(self, repo):
    byname_path = os.path.join(self.byname_dir, repo.name)
    byname_parent, filename = os.path.split(byname_path)
    self.assertPathExists(byname_path)
    abspath = os.path.normpath(os.path.join(byname_parent, os.readlink(byname_path)))
    self.assertEqual(repo.abspath, abspath)

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

  def test_created(self):
    self.assertByname(self.repo1)
    self.assertByname(self.repo2)
    self.assertByname(self.repo3)

  def test_move(self):
    old_link = os.path.join(self.byname_dir, self.repo1.name)
    self.repo1.name = 'svn1'
    self.repo1.save()
    self.assertByname(self.repo1)
    self.assertPathNotExists([self.byname_dir, 'a', 'b', 'c'])
    self.assertPathNotExists([self.byname_dir, 'a', 'b'])
    self.assertPathExists([self.byname_dir, 'a'])
    self.assertByname(self.repo2)
    self.assertByname(self.repo3)

    ## go back to initial state
    old_link = os.path.join(self.byname_dir, self.repo1.name)
    self.repo1.name = 'a/b/c/svn1'
    self.repo1.save()
    self.assertPathNotExists(old_link)
    self.assertByname(self.repo1)
    self.assertByname(self.repo2)
    self.assertByname(self.repo3)

  def test_idempotent_save(self):
    ## saving twice shouldn't remove the symlink
    self.assertByname(self.repo1)
    self.repo1.save()
    self.assertByname(self.repo1)
