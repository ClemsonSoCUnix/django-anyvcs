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

from anyvcs.common import PathDoesNotExist, attrdict
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.utils.encoding import force_text

import mimetypes
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

def get_directory_contents(repo, rev, path, key=None, reverse=False,
                           parents=True, reverse_func=None,
                           resolve_commits=False, **kw):
  '''
  Get repository contents suitable for using in a template context.

  With `key` and `reverse`, modify the sort order via `sorted()` of the
  directory contents. The default is to sort by name.

  With `parents` modify whether or not to include links to parent directories.
  The default is to include them.

  Provide a callable `reverse_func` to transform an entry into a URL. The
  default is to generate relative links.

  With `resolve_commits`, also include the commit log entry which last modified
  the entry. The default is to not. This forces commits to be reported from the
  call to `VCSRepo.ls()`.

  '''
  path = _normpath(path)
  key = key or (lambda e: e.name)

  # Force the report commit flag if not specified and resolve_commits is True.
  report = tuple(kw.get('report', ()))
  if resolve_commits and not 'commit' in report:
    report += ('commit',)
    kw['report'] = report

  contents = sorted(repo.repo.ls(rev, path, **kw), key=key, reverse=reverse)

  # Use relative paths by default for the URL.
  reverse_func = reverse_func or (lambda e: e.name)

  # Loop over the contents and add extra information in.
  cache = {}
  for entry in contents:
    if entry.type != 'l':
      entry.url = reverse_func(entry)
    # XXX The check for the commit is a hack around python-anyvcs#65
    if resolve_commits and 'commit' in entry:
      commit = entry.commit
      try:
        entry.log = cache[commit]
      except KeyError:
        entry.log = cache[commit] = repo.repo.log(revrange=commit)

  # Add parent directories if requested.
  parent_path = _normpath(_pardir(path))
  if path != '/' and parents:
    entry = attrdict(name='..', path=parent_path.lstrip('/'), type='d')
    entry.url = reverse_func(entry)
    contents.insert(0, entry)
  return contents

def render_file(template, repo, rev, path, file_mimetype=None,
                encoding='utf-8', extra_context=None, textfilter=None,
                raw=False, contents=None, catch_encoding_errors=False, **kw):
  '''
  Render a file to a template, or return the raw contents of the file if it is
  not a text file.

  With `file_mimetype` you can modify the mimetype of the file. The default is
  to detect the mimetype via the path and `mimetypes.guess_type()`. The
  default `encoding` can also be changed. You should catch the encoding errors
  which correspond to your chosen codec.

  `extra_context` may be a dict-like object which are passed into context for
  the template. By default, only `contents`, `rev`, and `path` are passed into
  the template.

  With `textfilter`, you can provide a filter function which modifies the
  decoded text contents of the file. The function must take the file contents,
  the path, and the file's mimetype as its three positional arguments. The
  function is only called if the file is detected to be a text file.

  If `raw` is True, the file will unconditionally be returned in its original
  form.

  If `contents` is given, the contents of the file are not retrieved, and it is
  assumed that `contents` contains the contents of the file.

  If `catch_encoding_errors` is True, encoding errors are handled by returning
  the raw file. Otherwise, you must handle the encoding errors.

  '''
  if contents is None:
    contents = repo.repo.cat(rev, path)

  if file_mimetype is None:
    file_mimetype, _ = mimetypes.guess_type(path)
    file_mimetype = file_mimetype or 'application/octet-stream'

  if raw or not file_mimetype.startswith('text/'):
    return HttpResponse(contents, content_type=file_mimetype)

  try:
    decoded_contents = force_text(contents, encoding=encoding)
  except:
    if not catch_encoding_errors:
      raise
    return HttpResponse(contents, content_type=file_mimetype)

  if textfilter is not None:
    decoded_contents = textfilter(decoded_contents, path, file_mimetype)

  context = {
    'repo': repo,
    'contents': decoded_contents,
    'rev': rev,
    'path': path,
  }
  if extra_context is not None:
    context.update(extra_context)

  return render_to_response(template, context, **kw)

def _normpath(path):
  path = os.path.normpath(path)
  if path in ('.', '/'):
    return '/'
  return path

def _pardir(path, levels=1):
  args = ['..'] * levels
  return os.path.join(path, *args)
