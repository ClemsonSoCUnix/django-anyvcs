===============================
Release Notes for django-anyvcs
===============================

2.4.0 (2015-09-23)
------------------

* Support for Django 1.4 through 1.8.
* Discontinue South migrations in favor of native Django migrations.
* Create the ``django_anyvcs.shortcuts`` module and write
  ``get_entry_or_404()``, ``get_directory_contents()`` and ``render_file()``.
* Bug fix: log errors which occur during repository access.

2.3.4 (2014-09-22)
------------------

* Bug fix: correct implementation of read-only Mercurial repositories

2.3.3 (2014-08-21)
------------------

* Bug fix: fix AttributeError in HgRequest.postprocess()

2.3.2 (2014-08-19)
------------------

* Bug fix: make removedirs() ignore OSError exceptions

2.3.1 (2014-08-18)
------------------

* Bug fix: fix dispatch for subversion
* Bug fix: fix dispatch with anonymous users

2.3.0 (2014-08-08)
------------------

* UserRights and GroupRights can be attached to different User and Group models
  or disabled entirely
* Directory structure of VCSREPO_ROOT was simplified
  * Backwards compatible for git and Mercurial
  * Must run "relocate path" admin action on all Subversion repositories
  * .byname directory is no longer needed
  * Directory structure is configurable, run "relocate paths" admin action to
  apply new structure
  * Default structure separates different VCS types into subdirectories
* Changing the path now moves the repository on disk
* Allow for absolute paths for repositories
* dispatch.py is now more reusable/extendable
* Default Repo ordering is now set by name
* Bug fix: Subversion authz file was not being updated when UserRights or
  GroupRights was deleted
* Bug fix: auth.Group membership changes were not picked up in Subversion authz
  file

2.2.1 (2014-07-30)
------------------

* Change license to BSD 3-clause
* Add support for Django 1.6

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
* A more useful admin site
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
