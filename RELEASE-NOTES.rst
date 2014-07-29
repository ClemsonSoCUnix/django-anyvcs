===============================
Release Notes for django-anyvcs
===============================

2.2.0 (2014-01-22)
------------------

* Deprecate ssh_dispatch.py in favor of django-anyvcs-ssh
* Deprecate VCS_URI_{FORMAT,CONTEXT} in favor of VCSREPO_URI_{FORMAT,CONTEXT}
* Fix issue where Subversion bynames could not be in a directory hierarchy.
* Add new settings VCSREPO_{GROUP,USER}_ACL_FUNCTION which allow backwards
  lookup of rights. This fixes issues generating the authz for Subversion.

2.1.0 (2013-10-08)
------------------

Migration label: 0004

* Deprecate Repo.public_rights, instead use Repo.public_read.  Note this means
  that public write access is no longer possible.
* Add properties to Repo and settings VCSREPO_URI_FORMAT and
  VCSREPO_URI_CONTEXT to facilitate getting various URIs of a repository.
* Add a web API for Repo.repo methods.
* django_anyvcs.remote provides a python API, compatiable with the
  python-anyvcs VCSRepo API, to access the aforementioned web API.
* An empty Repo.path is now populated with a path based on a UUID, and
  arranged in subdirectories so that the top-level directory is not overrun
  with thousands or more files.
* A more useful admin panel
* Major bug fix for Subversion so that repo name can be different from path
* A few small bug fixes

2.0.1 (2013-09-30)
------------------

* Remove unused settings
* Add missing django_anyvcs/migrations/__init__.py

2.0.0 (2013-09-27)
------------------

Migration label: 0001 (see README.upgrading.md)

* Rename anyvcs to django_anyvcs to avoid conflict with [python-anyvcs][1]
* Add Repo.repo property that refers to an instance of anyvcs.common.VCSRepo
* svnserve.conf is now created in Repo.update_authz()
* A few small bug fixes

[1]: https://github.com/ScottDuckworth/python-anyvcs

1.1.1 (2013-09-04)
------------------

* ssh_dispatch.py and dispatch.ssh_dispatch() now check the exit status of
  the subcommand and raise CalledProcessError if it is non-zero and return
  normally otherwise
* Update Repo.last_modified timestamp when rights are modified
* Include migrations in setuptools manifest so that it is actually included in
  source distributions and when installed
* A few small bug fixes

1.1.0 (2013-08-30)
------------------

Migration label: 0002

* Add Repo.created and Repo.last_modified timestamp properties

1.0.0 (2013-08-30)
------------------

First release
