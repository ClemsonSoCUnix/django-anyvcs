from django.http import HttpResponse, HttpResponseNotFound
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from . import models, settings
from models import Repo, UserRights, GroupRights
import json

def default_hosts_allow_function(request):
  remote_addr = request.META.get('REMOTE_ADDR', '')
  return remote_addr in settings.VCSREPO_HOSTS_ALLOW

def default_rights_function(repo, user):
  if user is not None:
    try:
      userrights = UserRights.objects.get(repo=repo, user=user)
      return userrights.rights
    except UserRights.DoesNotExist:
      rights = None
      for group in user.groups.all():
        try:
          grouprights = GroupRights.objects.get(repo=repo, group=group)
          if rights is None or len(grouprights.rights) < rights:
            rights = grouprights.rights
        except GroupRights.DoesNotExist:
          pass
      if rights is not None:
        return rights
  if repo.public_read_access:
    return 'r'
  return ''

def repo_access_data(repo, user, relpath=False):
  rights = None
  if settings.VCSREPO_RIGHTS_FUNCTION:
    rights = settings.VCSREPO_RIGHTS_FUNCTION(repo, user)
  if rights is None:
    rights = default_rights_function(repo, user)
  if relpath:
    path = repo.relpath
  else:
    path = repo.path
  return { 'rights': rights, 'vcs': repo.vcs, 'path': path }

def access(request, repo=None):
  if not (settings.VCSREPO_HOSTS_ALLOW_FUNCTION or default_hosts_allow_function)(request):
    raise PermissionDenied

  username = request.GET.get('u')
  user = None
  if username:
    try:
      user = User.objects.get(username=username)
    except User.DoesNotExist:
      message = 'User does not exist: %s\n' % username
      return HttpResponseNotFound(message, mimetype='text/plain')

  vcs = request.GET.get('vcs')
  qs = Repo.objects.all()
  if vcs:
    qs = qs.filter(vcs=vcs)

  if repo:
    try:
      repo = qs.get(name=repo)
    except Repo.DoesNotExist:
      message = 'Repository does not exist: %s\n' % repo
      return HttpResponseNotFound(message, mimetype='text/plain')
    data = repo_access_data(repo, user)
  else:
    repos = {}
    for repo in qs.all():
      repos[repo.name] = repo_access_data(repo, user, relpath=True)
    data = {'root': settings.VCSREPO_ROOT, 'repos': repos}
  return HttpResponse(json.dumps(data), mimetype='application/json')
