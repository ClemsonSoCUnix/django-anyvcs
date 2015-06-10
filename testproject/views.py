from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django_anyvcs.models import Repo
from django_anyvcs.shortcuts import get_entry_or_404, get_directory_contents

def repo_browse(request, name, rev=None, path=None):
  repo = get_object_or_404(Repo, name=name)
  rev = rev or 'HEAD'
  path = path or '/'
  path = '/' + path.lstrip('/')
  entry = get_entry_or_404(repo, rev, path)

  rev = repo.repo.canonical_rev(rev)

  if entry.type == 'd':
    reverse_func = lambda e: reverse(repo_browse, args=[name, rev, e.path])
    report = (
      'size',
      'target',
      'executable'
      'commit',
    )
    contents = get_directory_contents(repo, rev, path,
                                      report=report,
                                      resolve_commits=True,
                                      reverse_func=reverse_func)
    context = {
      'repo': repo,
      'path': path,
      'contents': contents,
    }
    return render(request, 'repo_browse_dir.html', context)
  elif entry.type == 'f':
    contents = repo.repo.cat(rev, path)
    context = {
      'repo': repo,
      'path': path,
      'contents': contents,
    }
    return render(request, 'repo_browse_file.html', context)
  else:
    return redirect(repo_browse, name)
