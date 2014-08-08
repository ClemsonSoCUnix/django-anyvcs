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

def path_function(repo):
  import hashlib
  import os
  h = hashlib.sha1(repo.name).hexdigest()
  p = [
    repo.vcs,
    h[0:2],
    h[2:4],
    h[4:],
  ]
  return os.path.join(*p)

def rights_function(repo, user):
  from . import settings
  if user is not None:
    if settings.VCSREPO_USE_USER_RIGHTS:
      from .models import UserRights
      try:
        userrights = UserRights.objects.get(repo=repo, user=user)
        return userrights.rights
      except UserRights.DoesNotExist:
        pass
    if settings.VCSREPO_USE_GROUP_RIGHTS:
      from .models import GroupRights
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
  if repo.public_read:
    return 'r'
  return '-'

def user_acl_function(repo):
  return dict((x.user, x.rights) for x in repo.userrights_set.all())

def group_acl_function(repo):
  return dict((x.group, x.rights) for x in repo.grouprights_set.all())
