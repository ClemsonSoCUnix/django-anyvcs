# Copyright (c) 2014-2016, Clemson University
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
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from . import settings
from .models import Repo

import logging
import os
import sys

logger = logging.getLogger(__name__)

VCSREPO_ROOT = os.getenv('VCSREPO_ROOT')
GIT = os.getenv('GIT', 'git')
HG = os.getenv('HG', 'hg')
SVNSERVE = os.getenv('SVNSERVE', 'svnserve')


class DispatchException(Exception):
  pass


class Request(object):
  postprocess = None

  def __init__(self, argv, username):
    self.argv = argv
    self.username = username
    self.repo_name = None
    self.data = {}
    self.write = True  # True if a write could have occurred

  @property
  def repo(self):
    try:
      return self._repo
    except AttributeError:
      self._repo = Repo.objects.get(name=self.repo_name)
      return self._repo

  def add_data(self, data):
    self.data.update(data)
    self.write = self.write and ('w' in self.data['rights'])

  def load_data(self, url, params=None):
    import json
    import urllib
    if params:
      url += '?' + urllib.urlencode(params)
    response = urllib.urlopen(url)
    status = response.getcode()
    content_type = response.info().gettype()
    if status == 200:
      data = json.load(response)
      self.add_data(data)
    else:
      if content_type == 'text/plain':
        raise DispatchException(response.readline().strip())
      if content_type == 'application/json':
        data = json.load(response)
        if isinstance(data, dict) and 'error' in data:
          raise DispatchException(data['error'])
        if isinstance(data, basestring):
          raise DispatchException(data)
      raise DispatchException('Backend failed', status)

  def get_command(self):
    raise NotImplementedError

  def run_command(self):
    import subprocess
    cmd = self.get_command()
    if not self.postprocess:
      return subprocess.call(cmd)
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    stderr = self.postprocess(stderr)
    sys.stderr.write(stderr)
    return p.returncode


class GitRequest(Request):
  vcs = 'git'

  def __init__(self, argv, username):
    super(GitRequest, self).__init__(argv, username)
    for arg in argv[1:]:
      if not arg.startswith('-'):
        repo_name = arg
        break
    else:
      raise DispatchException('Repository not specified')
    repo_name = repo_name.lstrip('/')
    if repo_name.endswith('.git'):
      repo_name = repo_name[:-4]
    self.repo_name = repo_name
    if self.argv[0] != 'git-receive-pack':
      self.write = False

  def get_command(self):
    rights = self.data['rights']
    path = self.data['path']
    if 'r' not in rights:
      raise DispatchException('Permission denied')
    if self.argv[0] == 'git-receive-pack':
      if 'w' not in rights:
        raise DispatchException('Permission denied (read only)')
    cmd = [GIT, 'shell', '-c', "%s '%s'" % (self.argv[0], path)]
    return cmd


class HgRequest(Request):
  vcs = 'hg'

  def __init__(self, argv, username):
    super(HgRequest, self).__init__(argv, username)
    for i in range(1, len(argv) - 1):
      if argv[i] in ('-R', '--repository'):
        repo_name = argv[i + 1]
        break
    else:
      raise DispatchException('Repository not specified')
    self.repo_name = repo_name.lstrip('/')

  def get_command(self):
    rights = self.data['rights']
    path = self.data['path']
    if 'r' not in rights:
      raise DispatchException('Permission denied')
    cmd = [HG, '-R', path, 'serve', '--stdio']
    if 'w' not in rights:
      hook = 'echo "Error: Permission denied (read-only)" >&2; false'
      cmd += [
        '--config', 'hooks.prechangegroup.readonly=' + hook,
        '--config', 'hooks.prepushkey.readonly=' + hook,
      ]
    return cmd

  def postprocess(self, text):
    return text.replace(self.data['path'], self.repo_name)


class SvnRequest(Request):
  vcs = 'svn'

  def get_command(self):
    assert VCSREPO_ROOT is not None, 'VCSREPO_ROOT is not set'
    svn_dir = os.path.join(VCSREPO_ROOT, 'svn')
    cmd = [SVNSERVE, '--root', svn_dir, '--tunnel']
    if self.username is not None:
      cmd.extend(['--tunnel-user', self.username])
    return cmd


def parse_command(cmd):
  import shlex
  try:
    argv = shlex.split(cmd)
  except ValueError as e:
    raise DispatchException('Illegal command', e)
  if not argv:
    raise DispatchException('Command not specified')
  return argv


def get_request(argv, username=None):
  if argv[0] in ('git-receive-pack', 'git-upload-pack', 'git-upload-archive'):
    return GitRequest(argv, username)
  if argv[0] == 'hg':
    return HgRequest(argv, username)
  if argv[0] == 'svnserve':
    return SvnRequest(argv, username)
  raise DispatchException('Command not allowed', argv[0])


def ssh_dispatch(access_url, username):
  cmd = os.getenv('SSH_ORIGINAL_COMMAND', '')
  try:
    argv = parse_command(cmd)
    request = get_request(argv, username)
    if request.repo_name:
      url = '%s/%s' % (access_url, request.repo_name)
      params = {'vcs': request.vcs}
      if username:
        params['u'] = username
      request.load_data(url, params)
    rc = request.run_command()
    if request.write and settings.VCSREPO_RECALCULATE_DISK_SIZE:
      request.repo.recalculate_disk_size()
      request.repo.save()
    return rc
  except DispatchException as e:
    sys.stderr.write('Error: ' + str(e) + '\n')
    sys.exit(1)
  except:
    message = 'Unhandled error during command dispatch'
    logger.error(message, exc_info=True)
    sys.stderr.write('%s\n' % message)
    sys.exit(1)


def main():
  argc = len(sys.argv)
  if argc < 2 or argc > 3:
    sys.stderr.write('Usage: %s <access-url> [<username>]\n' % sys.argv[0])
    sys.exit(1)
  url = sys.argv[1]
  username = None
  if argc == 3:
    username = sys.argv[2]

  status = ssh_dispatch(url, username)
  sys.exit(status)

if __name__ == '__main__':
  main()
