from django.conf import settings

VCSREPO_ROOT = settings.VCSREPO_ROOT
VCSREPO_HOSTS_ALLOW = getattr(settings, 'VCSREPO_HOSTS_ALLOW', ('127.0.0.1', '::1', '::ffff:127.0.0.1'))
VCSREPO_HOSTS_ALLOW_FUNCTION = getattr(settings, 'VCSREPO_HOSTS_ALLOW_FUNCTION', None)
VCSREPO_RIGHTS_FUNCTION = getattr(settings, 'VCSREPO_RIGHTS_FUNCTION', None)
GIT = getattr(settings, 'GIT', 'git')
HG = getattr(settings, 'HG', 'hg')
BZR = getattr(settings, 'BZR', 'bzr')
SVNADMIN = getattr(settings, 'SVNADMIN', 'svnadmin')
