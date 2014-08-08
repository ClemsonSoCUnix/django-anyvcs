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

from django.contrib import admin
from . import settings
from .models import Repo

def update_svnserve(modeladmin, request, queryset):
  for obj in queryset:
    obj.update_svnserve()
update_svnserve.short_description = 'Update svnserve.conf'

def relocate_path(modeladmin, request, queryset):
  for obj in queryset:
    obj.relocate_path()
    obj.save()

class RepoAdmin(admin.ModelAdmin):
  list_display = ['__unicode__', 'path', 'vcs']
  list_filter = ['vcs']
  search_fields = ['name', 'path']
  actions = [
    update_svnserve,
    relocate_path,
  ]

  def get_readonly_fields(self, request, obj=None):
    if obj:
      return ['abspath', 'vcs']
    else:
      return []

  def abspath(self, instance):
    return instance.abspath
  abspath.short_description = 'Full Path'

admin.site.register(Repo, RepoAdmin)

if settings.VCSREPO_USE_USER_RIGHTS:
  from .models import UserRights

  class UserRightsAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'repo', 'user', 'rights']
    search_fields = ['repo__name', 'user__username']

  admin.site.register(UserRights, UserRightsAdmin)

if settings.VCSREPO_USE_GROUP_RIGHTS:
  from .models import GroupRights

  class GroupRightsAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'repo', 'group', 'rights']
    search_fields = ['repo__name', 'group__name']

  admin.site.register(GroupRights, GroupRightsAdmin)
