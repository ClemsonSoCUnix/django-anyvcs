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

from django.conf import settings
import getpass
import socket

VCSREPO_ROOT = settings.VCSREPO_ROOT
VCSREPO_RIGHTS_FUNCTION = getattr(settings, 'VCSREPO_RIGHTS_FUNCTION', None)
VCSREPO_USER_ACL_FUNCTION = getattr(settings, 'VCSREPO_USER_ACL_FUNCTION', None)
VCSREPO_GROUP_ACL_FUNCTION = getattr(settings, 'VCSREPO_GROUP_ACL_FUNCTION', None)

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
