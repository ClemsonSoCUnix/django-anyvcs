django-anyvcs
=============

django-anyvcs is a Django app providing homogenous management of multiple
version control systems, and the access rights to them.  Currently supported
VCS systems are git, Mercurial, and Subversion.

Each instance of `django_anyvcs.models.Repo` corresponds to a VCS repository
on the server's disk.  You can grant access on these repos to Django `User`s
or `Group`s (from `django.contrib.auth.models`).

All repositories can be made available through the SSH access method.  The SSH
server should be configured with user public keys which force a specific
command to be run, instead of the command that was requested - this command
should be `ssh_dispatch.py`, included with django-anyvcs.  You'll probably
want to use [django-sshkey][1] to help you do this.

The `ssh_dispatch.py` program interprets the original ssh command, which
should be in the `SSH_ORIGINAL_COMMAND` environment variable (automatically
set by OpenSSH), and fulfills the request, granting and denying access as
configured in Django.

Configuration
-------------

Add `django_anyvcs` to your project's `INSTALLED_APPS`.

The `django_anyvcs.views.access` view is used by `ssh_dispatch.py`.  The URL
that maps to this view should be accessible to the host running
`ssh_dispatch.py` (usually localhost).

The `django_anyvcs.views.api_call` view is not used by any component of
django-anyvcs, but is made available to provide a web API to access the
underlying repository.  The `django_anyvcs.remote` module provides a python
API to this web API which provides an interface similar to
`anyvcs.common.VCSRepo` objects.

*IMPORTANT:* Do not make any URLs from `django_anyvcs.urls` available to the
public, as they can reveal sensitive information.

Settings
--------

django-anyvcs looks at the following variables in your project's settings.py:

`VCSREPO_ROOT` (Required)
The root directory in which all VCS repositories are stored.

`VCSREPO_RIGHTS_FUNCTION` (default: None)
If set, this function is called with two parameters: the repository being
accessed, and the user who is accessing the repository (may be None to
indicate an anonymous user).  The function should return the rights string,
which is one of '-' (deny access), 'r' (read-only access), or 'rw' (read and
write access).

`VCSREPO_USER_REVERSE_FUNCTION` (default: None)
If set, this function is called with two parameters: a repository and a rights
string which is one of '-', 'r', or 'rw'. The function should return a sequence
of users which hold exactly this level of access for the given repository.

`VCSREPO_GROUP_REVERSE_FUNCTION` (default: None)
If set, this function is called with two parameters: a repository and a rights
string which is one of '-', 'r', or 'rw'. The function should return a sequence
of groups which hold exactly this level of access for the given repository.

When used with [django-sshkey][1], a setting similar to this will tie together
the two apps:

    SSHKEY_AUTHORIZED_KEYS_OPTIONS = \
      'command="env VCSREPO_ROOT=%s /path/to/ssh_dispatch.py ' \
      'http://localhost:8000/anyvcs/access {username}",no-agent-forwarding,' \
      'no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding' % VCSREPO_ROOT

Dependencies
------------

* [python-anyvcs][2] version 1.1.0 or greater

Although not a strict dependency, django-anyvcs was designed to be used in
conjunction with [django-sshkey][1] (version 2.0.0 or greater) and would be
fairly useless without it or something that provides a similar functionality.

[1]: https://bitbucket.org/ClemsonSoCUnix/django-sshkey
[2]: https://github.com/ScottDuckworth/python-anyvcs
