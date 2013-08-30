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

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from anyvcs.models import Repo, UserRights, GroupRights
from anyvcs import settings
import json
import os
import shutil
import tempfile

class BaseTestCase(TestCase):
  def setUp(self):
    self.original_root = settings.VCSREPO_ROOT
    settings.VCSREPO_ROOT = tempfile.mkdtemp(prefix='anyvcs-test.')
    self.original_rights_function = settings.VCSREPO_RIGHTS_FUNCTION
    settings.VCSREPO_RIGHTS_FUNCTION = None

  def tearDown(self):
    Repo.objects.all().delete()
    shutil.rmtree(settings.VCSREPO_ROOT)
    settings.VCSREPO_ROOT = self.original_root
    settings.VCSREPO_RIGHTS_FUNCTION = self.original_rights_function

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

  def test_invalid_public_rights(self):
    repo = Repo(name='repo', path='repo', vcs='git', public_rights='invalid')
    self.assertRaises(ValidationError, repo.full_clean)

  def test_git(self):
    repo = Repo(name='a', path='b', vcs='git')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'b')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'b'))

  def test_git_without_path(self):
    repo = Repo(name='a', vcs='git')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'a')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'a'))

  def test_hg(self):
    repo = Repo(name='a', path='b', vcs='hg')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'b')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'b'))

  def test_hg_without_path(self):
    repo = Repo(name='a', vcs='hg')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'a')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'a'))

  def test_svn(self):
    repo = Repo(name='a', path='b', vcs='svn')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'b')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'b'))

  def test_svn_without_path(self):
    repo = Repo(name='a', vcs='svn')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.path, 'a')
    self.assertEqual(repo.abspath, os.path.join(settings.VCSREPO_ROOT, 'a'))

  def test_public_deny(self):
    repo = Repo(name='a', path='a', vcs='git', public_rights='-')
    repo.full_clean()
    repo.save()
    self.assertEqual(repo.public_rights, '-')

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

  def test_public_rights_anonymous(self):
    vcs = 'git'
    for public_rights in ('-', 'r', 'rw'):
      repo = Repo.objects.create(
        name = 'repo',
        path = 'repo',
        vcs = vcs,
        public_rights = public_rights,
      )
      client = Client()
      url = reverse('anyvcs.views.access', args=(repo.name,))
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

  def test_public_rights_user(self):
    vcs = 'hg'
    for public_rights in ('-', 'r', 'rw'):
      repo = Repo.objects.create(
        name = 'repo',
        path = 'repo',
        vcs = vcs,
        public_rights = public_rights,
      )
      client = Client()
      url = reverse('anyvcs.views.access', args=(repo.name,))
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

  def test_user_overrides_public_rights(self):
    vcs = 'git'
    for public_rights in ('-', 'r', 'rw'):
      for user_rights in ('-', 'r', 'rw'):
        repo = Repo.objects.create(
          name = 'repo',
          path = 'repo',
          vcs = vcs,
          public_rights = public_rights,
        )
        UserRights.objects.create(
          repo = repo,
          user = self.user1,
          rights = user_rights,
        )
        client = Client()
        url = reverse('anyvcs.views.access', args=(repo.name,))
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

  def test_group_overrides_public_rights(self):
    vcs = 'hg'
    for public_rights in ('-', 'r', 'rw'):
      for group_rights in ('-', 'r', 'rw'):
        repo = Repo.objects.create(
          name = 'repo',
          path = 'repo',
          vcs = vcs,
          public_rights = public_rights,
        )
        GroupRights.objects.create(
          repo = repo,
          group = self.group1,
          rights = group_rights,
        )
        client = Client()
        url = reverse('anyvcs.views.access', args=(repo.name,))
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
    public_rights = '-'
    for group_rights in ('-', 'r', 'rw'):
      for user_rights in ('-', 'r', 'rw'):
        repo = Repo.objects.create(
          name = 'repo',
          path = 'repo',
          vcs = vcs,
          public_rights = public_rights,
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
        url = reverse('anyvcs.views.access', args=(repo.name,))
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
      public_rights = '-',
    )
    for rights in ('-', 'r', 'rw'):
      def f(r, u):
        self.assertEqual(repo, r)
        self.assertEqual(self.user1, u)
        return rights
      settings.VCSREPO_RIGHTS_FUNCTION = f
      client = Client()
      url = reverse('anyvcs.views.access', args=(repo.name,))
      response = client.get(url, {'u': self.user1.username})
      self.assertEqual(response.status_code, 200)
      self.assertIn('Content-Type', response)
      self.assertEqual(response['Content-Type'], 'application/json')
      document = json.loads(response.content)
      self.assertIn('rights', document)
      self.assertEqual(document['rights'], rights)
