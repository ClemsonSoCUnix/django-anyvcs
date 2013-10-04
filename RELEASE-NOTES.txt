Release Notes for django-anyvcs
===============================

2.0.1 (2013-09-30)
------------------

* Remove unused settings
* Add missing django_anyvcs/migrations/__init__.py

2.0.0 (2013-09-27)
------------------

Migration required: 0001 (see README.upgrading.md)

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

Migration required: 0002

* Add Repo.created and Repo.last_modified timestamp properties

1.0.0 (2013-08-30)
------------------

First release
