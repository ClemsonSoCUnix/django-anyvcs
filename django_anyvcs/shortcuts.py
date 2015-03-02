# Copyright (c) 2014-2015, Clemson University
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
# * Neither the name of Clemson University nor the names of its
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

from anyvcs.common import PathDoesNotExist
from django.http import Http404

import os

def get_entry_or_404(repo, rev, path, **kw):
  '''
  Get entry via `repo.repo.ls()` or raise Http404.

  Keyword arguments are passed along to the call to `ls()`.

  '''
  if not rev in repo.repo:
    raise Http404
  try:
    return repo.repo.ls(rev, path, directory=True, **kw)[0]
  except PathDoesNotExist:
    raise Http404

def get_directory_contents(repo, rev, path, key=None, parents=True, links=None,
                           reverse_func=None, **kw):
  '''
  Get repository contents suitable for using in a template context.

  '''
  path = _normpath(path)
  contents = repo.repo.ls(rev, path, **kw)

  # Use relative paths by default for the URL.
  reverse_func = reverse_func or (lambda p: p)

  # Loop over the contents and add extra information in.
  for entry in contents:
    if entry.type != 'l':
      entry.url = reverse_func(entry.name)

  # Add parent directories if requested.
  parent_path = _normpath(_pardir(path))
  if path != '/' and parents:
    entry = {
      'name': '..',
      'path': '..',
      'type': 'd',
      'url': reverse_func('..'),
    }
    contents.insert(0, entry)
  return contents

def _normpath(path):
  path = os.path.normpath(path)
  if path in ('.', '/'):
    return '/'
  return path

def _pardir(path, levels=1):
  args = ['..'] * levels
  return os.path.join(path, *args)
