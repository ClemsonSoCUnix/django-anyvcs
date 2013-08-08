import json
import os
import shlex
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

  # Git
  if argv[0] in ('git-receive-pack', 'git-upload-pack', 'git-upload-archive'):
    for arg in argv[1:]:
      if not arg.startswith('-'):
        repo_name = arg
        break
    else:
      die('Repository not specified')
    if repo_name[0] == '/':
      repo_name = repo_name[1:]
    access = get_repo_access(access_url, repo_name, username, 'git')
    if 'r' not in access.rights:
      die('Permission denied')
    if argv[0] == 'git-receive-pack' and 'w' not in access.rights:
      die('Permission denied (read only)')
    args = ['git', 'shell', '-c', "%s '%s'" % (argv[0], access.path)]
    os.execvp(args[0], args)

  # Mercurial
  if argv[0] == 'hg':
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
    sys.exit()

  # Subversion
  if argv[0] == 'svnserve':
    root, repos = get_repo_access(access_url, None, username, 'svn')
    args = ['svnserve', '-t', '-r', root]
    os.execvp(args[0], args)

  die('Command not allowed: %s' % cmd)

def get_repo_access(access_url, repo_name, username, vcs):
  query = {}
  if username is not None:
    query['u'] = username
  if vcs is not None:
    query['vcs'] = vcs
  if repo_name is None:
    url = '%s/?%s' % (access_url, urllib.urlencode(query))
  else:
    url = '%s/%s?%s' % (access_url, repo_name, urllib.urlencode(query))
  response = urllib.urlopen(url)
  code = response.getcode()
  mime = response.info().gettype()
  if code == 200:
    if mime != 'application/json':
      die('Backend returned mimetype %s' % mime)
    data = json.load(response)
    if repo_name is None:
      repos = {}
      for k,v in data['repos'].iteritems():
        repos[k] = RepoAccess(**v)
      return (data['root'], repos)
    else:
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
