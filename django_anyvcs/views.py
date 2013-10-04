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

from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from . import models, settings
from models import Repo, UserRights, GroupRights
import json

class DictEncoder(json.JSONEncoder):
  def default(self, o):
    if hasattr(o, '__dict__'):
      return o.__dict__
    else:
      return unicode(o)

dictencoder = DictEncoder()

def JsonResponse(data, *args, **kwargs):
  kwargs.setdefault('mimetype', 'application/json')
  json = dictencoder.encode(data)
  return HttpResponse(json, *args, **kwargs)

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
  return repo.public_rights

def repo_access_data(repo, user):
  rights = None
  if settings.VCSREPO_RIGHTS_FUNCTION:
    rights = settings.VCSREPO_RIGHTS_FUNCTION(repo, user)
  if rights is None:
    rights = default_rights_function(repo, user)
  return { 'rights': rights, 'vcs': repo.vcs, 'path': repo.abspath }

def access(request, repo):
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

  try:
    repo = qs.get(name=repo)
  except Repo.DoesNotExist:
    message = 'Repository does not exist: %s\n' % repo
    return HttpResponseNotFound(message, mimetype='text/plain')
  data = repo_access_data(repo, user)
  return JsonResponse(data)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_call(request, repo, attr):
  from collections import Callable
  try:
    repo = Repo.objects.get(name=repo)
  except Repo.DoesNotExist:
    message = 'Repository does not exist: %s\n' % repo
    return HttpResponseNotFound(message, mimetype='text/plain')
  if not hasattr(repo.repo, attr):
    message = 'Attribute does not exist'
    return HttpResponseNotFound(message, mimetype='text/plain')
  attr = getattr(repo.repo, attr)
  if request.method == 'POST':
    if not isinstance(attr, Callable):
      message = 'Attribute is not callable'
      return HttpResponseNotFound(message, mimetype='text/plain')
    kwargs = json.load(request)
    try:
      data = attr(**kwargs)
    except Exception as e:
      import traceback
      data = {
        'module': type(e).__module__,
        'class': type(e).__name__,
        'args': e.args,
        'str': str(e),
        'traceback': traceback.format_exc(),
      }
      return JsonResponse(data, status=400)
    return JsonResponse(data)
  else:
    return JsonResponse(attr)
