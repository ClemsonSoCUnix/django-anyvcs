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

from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from . import models, settings
from .models import Repo
import json

try:
  from django.contrib.auth import get_user_model
except ImportError:
  from django.contrib.auth.models import User
  def get_user_model():
    return User

class DictEncoder(json.JSONEncoder):
  def default(self, o):
    if hasattr(o, '__dict__'):
      return o.__dict__
    else:
      return unicode(o)

dictencoder = DictEncoder()

def JsonResponse(data, *args, **kwargs):
  kwargs.setdefault('content_type', 'application/json')
  json = dictencoder.encode(data)
  return HttpResponse(json, *args, **kwargs)

def repo_access_data(repo, user):
  rights = settings.VCSREPO_RIGHTS_FUNCTION(repo, user)
  return { 'rights': rights, 'vcs': repo.vcs, 'path': repo.abspath }

def access(request, repo):
  username = request.GET.get('u')
  user = None
  if username:
    UserModel = get_user_model()
    try:
      user = UserModel.objects.get(username=username)
    except UserModel.DoesNotExist:
      message = 'User does not exist: %s\n' % username
      return HttpResponseNotFound(message, content_type='text/plain')

  vcs = request.GET.get('vcs')
  qs = Repo.objects.all()
  if vcs:
    qs = qs.filter(vcs=vcs)

  try:
    repo = qs.get(name=repo)
  except Repo.DoesNotExist:
    message = 'Repository does not exist: %s\n' % repo
    return HttpResponseNotFound(message, content_type='text/plain')
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
    return HttpResponseNotFound(message, content_type='text/plain')
  if not hasattr(repo.repo, attr):
    message = 'Attribute does not exist'
    return HttpResponseNotFound(message, content_type='text/plain')
  attr = getattr(repo.repo, attr)
  if request.method == 'POST':
    if not isinstance(attr, Callable):
      message = 'Attribute is not callable'
      return HttpResponseNotFound(message, content_type='text/plain')
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
