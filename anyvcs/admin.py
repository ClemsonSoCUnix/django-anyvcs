from django.contrib import admin
from models import Repo, UserRights, GroupRights

class RepoAdmin(admin.ModelAdmin):
  list_display = ['name', 'vcs']
  list_filter = ['vcs']
  search_fields = ['name']

  def get_readonly_fields(self, request, obj=None):
    if obj:
      return ['vcs']
    else:
      return []

class UserRightsAdmin(admin.ModelAdmin):
  list_display = ['repo', 'user']
  search_fields = ['repo__name', 'user__username']

class GroupRightsAdmin(admin.ModelAdmin):
  list_display = ['repo', 'group']
  search_fields = ['repo__name', 'group__name']

admin.site.register(Repo, RepoAdmin)
admin.site.register(UserRights, UserRightsAdmin)
admin.site.register(GroupRights, GroupRightsAdmin)
