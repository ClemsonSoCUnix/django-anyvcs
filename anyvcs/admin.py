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

from django.contrib import admin
from models import Repo, UserRights, GroupRights

class RepoAdmin(admin.ModelAdmin):
  list_display = ['__unicode__', 'vcs']
  list_filter = ['vcs']
  search_fields = ['name']

  def get_readonly_fields(self, request, obj=None):
    if obj:
      return ['vcs']
    else:
      return []

class UserRightsAdmin(admin.ModelAdmin):
  list_display = ['__unicode__', 'repo', 'user', 'rights']
  search_fields = ['repo__name', 'user__username']

class GroupRightsAdmin(admin.ModelAdmin):
  list_display = ['__unicode__', 'repo', 'group', 'rights']
  search_fields = ['repo__name', 'group__name']

admin.site.register(Repo, RepoAdmin)
admin.site.register(UserRights, UserRightsAdmin)
admin.site.register(GroupRights, GroupRightsAdmin)
