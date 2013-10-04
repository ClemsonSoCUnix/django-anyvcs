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
VCSREPO_URI_FORMAT = getattr(settings, 'VCS_URI_FORMAT', {})
VCSREPO_URI_FORMAT.setdefault(('git', 'ssh'), '{user}@{hostname}:{path}')
VCSREPO_URI_FORMAT.setdefault(('svn', 'ssh'), 'svn+ssh://{user}@{hostname}/{path}')
VCSREPO_URI_FORMAT.setdefault(('hg', 'ssh'), 'ssh://{user}@{hostname}/{path}')
VCSREPO_URI_CONTEXT = getattr(settings, 'VCS_URI_CONTEXT', {})
VCSREPO_URI_CONTEXT.setdefault('user', getpass.getuser())
VCSREPO_URI_CONTEXT.setdefault('hostname', socket.gethostname())
