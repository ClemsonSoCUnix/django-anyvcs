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

from django.conf import settings
import getpass
import socket

def default_path(repo):
  import os
  import uuid
  h = uuid.uuid1().hex
  p = [
    repo.vcs,
    h[0:2],
    h[2:4],
    h[4:6],
    h[6:8],
    h[8:],
  ]
  return os.path.join(*p)

def default_user_acl_function(repo):
  return dict((x.user, x.rights) for x in repo.userrights_set.all())

def default_group_acl_function(repo):
  return dict((x.group, x.rights) for x in repo.grouprights_set.all())

VCSREPO_ROOT = settings.VCSREPO_ROOT
VCSREPO_PATH_FUNCTION = getattr(settings, 'VCSREPO_RELPATH_FUNCTION', default_path)

VCSREPO_RIGHTS_FUNCTION = getattr(settings, 'VCSREPO_RIGHTS_FUNCTION', None)
VCSREPO_USER_ACL_FUNCTION = getattr(settings, 'VCSREPO_USER_ACL_FUNCTION', default_user_acl_function)
VCSREPO_GROUP_ACL_FUNCTION = getattr(settings, 'VCSREPO_GROUP_ACL_FUNCTION', default_group_acl_function)

if hasattr(settings, 'VCS_URI_FORMAT'):
  import warnings
  warn = "VCS_URI_FORMAT is deprecated; use VCSREPO_URI_FORMAT"
  warnings.warn(warn, DeprecationWarning)
  VCSREPO_URI_FORMAT = settings.VCS_URI_FORMAT
else:
  VCSREPO_URI_FORMAT = getattr(settings, 'VCSREPO_URI_FORMAT', {})
VCSREPO_URI_FORMAT.setdefault(('git', 'ssh'), '{user}@{hostname}:{path}')
VCSREPO_URI_FORMAT.setdefault(('svn', 'ssh'), 'svn+ssh://{user}@{hostname}/{path}')
VCSREPO_URI_FORMAT.setdefault(('hg', 'ssh'), 'ssh://{user}@{hostname}/{path}')
VCSREPO_URI_FORMAT.setdefault(('git', 'anonymous-ssh'), '{anonymous}@{hostname}:{path}')
VCSREPO_URI_FORMAT.setdefault(('svn', 'anonymous-ssh'), 'svn+ssh://{anonymous}@{hostname}/{path}')
VCSREPO_URI_FORMAT.setdefault(('hg', 'anonymous-ssh'), 'ssh://{anonymous}@{hostname}/{path}')

if hasattr(settings, 'VCS_URI_CONTEXT'):
  import warnings
  warn = "VCS_URI_CONTEXT is deprecated; use VCSREPO_URI_CONTEXT"
  warnings.warn(warn, DeprecationWarning)
  VCSREPO_URI_CONTEXT = settings.VCS_URI_CONTEXT
else:
  VCSREPO_URI_CONTEXT = getattr(settings, 'VCSREPO_URI_CONTEXT', {})
VCSREPO_URI_CONTEXT.setdefault('anonymous', 'anonymous')
VCSREPO_URI_CONTEXT.setdefault('user', getpass.getuser())
VCSREPO_URI_CONTEXT.setdefault('hostname', socket.gethostname())
