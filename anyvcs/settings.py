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

VCSREPO_ROOT = settings.VCSREPO_ROOT
VCSREPO_HOSTS_ALLOW = getattr(settings, 'VCSREPO_HOSTS_ALLOW', ('127.0.0.1', '::1', '::ffff:127.0.0.1'))
VCSREPO_HOSTS_ALLOW_FUNCTION = getattr(settings, 'VCSREPO_HOSTS_ALLOW_FUNCTION', None)
VCSREPO_RIGHTS_FUNCTION = getattr(settings, 'VCSREPO_RIGHTS_FUNCTION', None)
GIT = getattr(settings, 'GIT', 'git')
HG = getattr(settings, 'HG', 'hg')
SVNADMIN = getattr(settings, 'SVNADMIN', 'svnadmin')
