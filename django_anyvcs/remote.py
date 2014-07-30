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

import httplib
import json
from urlparse import urlparse
from anyvcs.common import VCSRepo, PathDoesNotExist, BadFileType, attrdict, \
                          CommitLogEntry

class BadResponse(Exception):
  def __init__(self, status, reason, content_type, body=None):
    self.status = status
    self.reason = reason
    self.content_type = content_type
    self.body = body

  def __str__(self):
    return 'Server returned %s %s; Content-Type=%s' % (
      self.status, self.reason, self.content_type)

class VCSRepo(object):
  def __init__(self, api_url):
    url = urlparse(api_url)
    assert url.scheme == 'http'
    self._url = url
    self._conn = httplib.HTTPConnection(url.netloc)
    self._path = url.path.rstrip('/') + '/'

  def _getresponse(self):
    response = self._conn.getresponse()
    ct = response.getheader('Content-Type')
    body = response.read()
    if response.status == 200:
      if ct == 'application/json':
        data = json.loads(body)
        return data
    if response.status == 400:
      if ct == 'application/json':
        data = json.loads(body)
        if data.get('module') == 'anyvcs.common':
          klass = data.get('class')
          args = data.get('args', [])
          if klass == 'BadFileType':
            raise BadFileType(*args)
          if klass == 'PathDoesNotExist':
            raise PathDoesNotExist(*args)
    raise BadResponse(response.status, response.reason, ct, body)

  def _get(self, attr):
    method = 'GET'
    url = self._path + attr
    self._conn.request(method, url)
    return self._getresponse()

  def _post(self, attr, **kwargs):
    method = 'POST'
    url = self._path + attr
    body = json.dumps(kwargs)
    headers = {'Content-Type': 'application/json'}
    self._conn.request(method, url, body, headers)
    return self._getresponse()

  @property
  def path(self):
    return self._get('path')

  def ls(self, rev, path, recursive=False, recursive_dirs=False,
         directory=False, report=[]):
    if isinstance(report, (tuple, list)):
      report = ','.join(report)
    result = self._post('ls', rev=rev, path=path, recursive=recursive,
                        recursive_dirs=recursive_dirs, directory=directory,
                        report=','.join(report))
    return [attrdict(x) for x in result]

  def cat(self, rev, path):
    return self._post('cat', rev=rev, path=path)

  def readlink(self, rev, path):
    return self._post('readlink', rev=rev, path=path)

  def branches(self):
    return self._post('branches')

  def tags(self):
    return self._post('tags')

  def heads(self):
    return self._post('heads')

  def empty(self):
    return self._post('empty')

  def log(self, revrange=None, limit=None, firstparent=False, merges=None,
          path=None, follow=False):
    if isinstance(revrange, tuple):
      revrange = ','.join(revrange)
    result = self._post('log', revrange=revrange, limit=limit,
                        firstparent=firstparent, merges=merges, path=path,
                        follow=follow)
    if isinstance(result, list):
      return [CommitLogEntry(**x) for x in result]
    else:
      return CommitLogEntry(**result)

  def diff(self, rev_a, rev_b, path=None):
    return self._post('diff', rev_a=rev_a, rev_b=rev_b, path=path)

  def ancestor(self, rev1, rev2):
    return self._post('ancestor', rev1=rev1, rev2=rev2)

class GitRepo(VCSRepo):
  """Mirrors the functionality of anyvcs.git.GitRepo"""

  pass

class HgRepo(VCSRepo):
  """Mirrors the functionality of anyvcs.hg.HgRepo"""

  def bookmarks(self):
    return self._post('bookmarks')

class SvnRepo(VCSRepo):
  """Mirrors the functionality of anyvcs.svn.SvnRepo"""

  def proplist(self, rev, path=None):
    return self._post('proplist', rev=rev, path=path)

  def propget(self, prop, rev, path=None):
    return self._post('propget', prop=prop, rev=rev, path=path)

  def youngest(self):
    return self._post('youngest')
