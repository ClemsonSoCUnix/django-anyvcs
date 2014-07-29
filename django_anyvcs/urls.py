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

try:
  from django.conf.urls import patterns, url
except ImportError:
  from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('django_anyvcs.views',
  url(r'^access/(?P<repo>.+)$', 'access'),
  url(r'^api/(?P<repo>.+)/(?P<attr>\w+)$', 'api_call'),
)
