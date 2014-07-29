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
    return ssh_dispatch_git(access_url, username, argv)
  elif argv[0] == 'hg':
    return ssh_dispatch_hg(access_url, username, argv)
  elif argv[0] == 'svnserve':
    return ssh_dispatch_svn(access_url, username, argv)
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
  return subprocess.call(cmd)

def ssh_dispatch_hg(access_url, username, argv):
  try:
    repo_name = argv[argv.index('-R') + 1]
  except ValueError:
    try:
      repo_name = argv[argv.index('--repository') + 1]
    except ValueError:
      die('Repository not specified')
  access = get_repo_access(access_url, repo_name, username, 'hg')
  if 'r' not in access.rights:
    die('Permission denied')
  hg = os.getenv('HG', 'hg')
  cmd = [hg, '-R', access.path, 'serve', '--stdio']
  if 'w' not in access.rights:
    cmd += [
      '--config',
      'hooks.prechangegroup.readonly=echo "Error: Permission denied (read-only)" >&2',
      '--config',
      'hooks.prepushkey.readonly=echo "Error: Permission denied (read-only)" >&2',
    ]
  p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
  stdout, stderr = p.communicate()
  stderr = stderr.replace(access.path, repo_name)
  sys.stderr.write(stderr)
  return p.returncode

def ssh_dispatch_svn(access_url, username, argv):
  VCSREPO_ROOT = os.getenv('VCSREPO_ROOT')
  assert VCSREPO_ROOT is not None, 'VCSREPO_ROOT is not set'
  svnserve = os.getenv('SVNSERVE', 'svnserve')
  byname_dir = os.path.join(VCSREPO_ROOT, '.byname')
  cmd = [svnserve, '--root', byname_dir, '--tunnel']
  if username is not None:
    cmd.extend(['--tunnel-user', username])
  return subprocess.call(cmd)

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

def main():
  if len(sys.argv) == 2:
    url = sys.argv[1]
    username = None
  elif len(sys.argv) == 3:
    url, username = sys.argv[1:]
  else:
    sys.stderr.write('Usage: %s <url> [<username>]\n' % sys.argv[0])
    sys.exit(1)

  status = ssh_dispatch(url, username)
  sys.exit(status)
  
