django-anyvcs is a Django app providing homogenous management of multiple
version control systems, and the access rights to them.  Currently supported
VCS systems are git, Mercurial, and Subversion.

The app has no required external dependencies, but was designed to be used in
conjunction with [django-sshkey][1].

Configuration
-------------

django-anyvcs looks at the following variables in your project's settings.py:

`VCSREPO_ROOT` (Required)
The root directory in which all VCS repositories are stored.

`VCSREPO_RIGHTS_FUNCTION` (default: None)
If set, this function is called with two parameters: the repository being
accessed, and the user who is accessing the repository (may be None to
indicate an anonymous user).  The function should return the rights string,
which is one of '-' (deny access), 'r' (read-only access), or 'rw' (read and
write access).

`VCSREPO_HOSTS_ALLOW` (default: IPv4 and IPv6 localhost addresses)
A list or tuple containing IP addresses which are allowed to access the
access rights view.

`VCSREPO_HOSTS_ALLOW_FUNCTION` (default: None)
If set, this function is called with a single parameter being the IP address
of the client trying to access the access rights view.  The function should
return True to allow access or False to deny access.

Dispatching VCS Requests
------------------------

The `ssh_dispatch.py` script can be used to dispatch VCS requests via SSH.
The SSH server should be forced to run the `ssh_dispatch.py` command via
the `command` option in the `authorized_keys` file.  The environment variable
``SSH_ORIGINAL_COMMAND must be set with the original command that was run via
SSH.  Any commands that are not recognized will throw an error.

[1]: https://bitbucket.org/ClemsonSoCUnix/django-sshkey "django-sshkey"
