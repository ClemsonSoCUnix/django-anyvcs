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

import json
import os
import shlex
import subprocess
import sys
import urllib
from collections import namedtuple

RepoAccess = namedtuple('RepoAccess', 'path vcs rights')

def die(message):
  sys.stderr.write('Error: ')
  sys.stderr.write(message)
  if not message.endswith('\n'):
    sys.stderr.write('\n')
  sys.exit(1)

def ssh_dispatch(access_url, username):
  cmd = os.getenv('SSH_ORIGINAL_COMMAND', '')
  try:
    argv = shlex.split(cmd)
  except ValueError as e:
    die('Illegal command: %s' % e)
  if not argv:
    die('Command not specified')

  if argv[0] in ('git-receive-pack', 'git-upload-pack', 'git-upload-archive'):
    ssh_dispatch_git(access_url, username, argv)
  elif argv[0] == 'hg':
    ssh_dispatch_hg(access_url, username, argv)
  elif argv[0] == 'svnserve':
    ssh_dispatch_svn(access_url, username, argv)
  else:
    die('Command not allowed: %s' % cmd)

def ssh_dispatch_git(access_url, username, argv):
  for arg in argv[1:]:
    if not arg.startswith('-'):
      repo_name = arg
      break
  else:
    die('Repository not specified')
  if repo_name[0] == '/':
    repo_name = repo_name[1:]
  if repo_name.endswith('.git'):
    repo_name = repo_name[:-4]
  access = get_repo_access(access_url, repo_name, username, 'git')
  if 'r' not in access.rights:
    die('Permission denied')
  if argv[0] == 'git-receive-pack':
    if 'w' not in access.rights:
      die('Permission denied (read only)')
  git = os.getenv('GIT', 'git')
  cmd = [git, 'shell', '-c', "%s '%s'" % (argv[0], access.path)]
  subprocess.check_call(cmd)

def ssh_dispatch_hg(access_url, username, argv):
  try:
    repo_name = argv[argv.index('-R') + 1]
  except ValueError:
    try:
      repo_name = argv[argv.index('--repository') + 1]
    except ValueError:
      die('Repository not specified')
  access = get_repo_access(access_url, repo_name, username, 'hg')
  import mercurial.dispatch
  if 'r' not in access.rights:
    die('Permission denied')
  hgcmd = ['-R', access.path, 'serve', '--stdio']
  if 'w' not in access.rights:
    hgcmd += [
      '--config',
      'hooks.prechangegroup.readonly=python:%s.hg_readonly' % __name__,
      '--config',
      'hooks.prepushkey.readonly=python:%s.hg_readonly' % __name__,
    ]
  mercurial.dispatch.dispatch(mercurial.dispatch.request(hgcmd))

def ssh_dispatch_svn(access_url, username, argv):
  VCSREPO_ROOT = os.getenv('VCSREPO_ROOT')
  assert VCSREPO_ROOT is not None, 'VCSREPO_ROOT is not set'
  svnserve = os.getenv('SVNSERVE', 'svnserve')
  cmd = [svnserve, '--root', VCSREPO_ROOT, '--tunnel', '--tunnel-user', username]
  subprocess.check_call(cmd)

def get_repo_access(access_url, repo_name, username, vcs):
  query = {}
  if username is not None:
    query['u'] = username
  if vcs is not None:
    query['vcs'] = vcs
  url = '%s/%s?%s' % (access_url, repo_name, urllib.urlencode(query))
  response = urllib.urlopen(url)
  code = response.getcode()
  mime = response.info().gettype()
  if code == 200:
    if mime != 'application/json':
      die('Backend returned mimetype %s' % mime)
    data = json.load(response)
    return RepoAccess(**data)
  elif code == 404:
    if mime == 'text/plain':
      die(response.read())
    die('Not found')
  else:
    sys.stderr.write('Error: Backend returned code %s\n' % code)
    sys.stderr.write(response.read())
    sys.exit(1)

def hg_readonly(ui, **kwargs):
  ui.warn('Error: Permission denied (read only)\n')
  return 1