Upgrading and Downgrading
=========================

From django-anyvcs 1.1 to 2.3, South_ migrations were provided. Starting with
2.4, South support was discontinued in favor of the Django native migration
system.

The following table maps django-anyvcs version to migration labels:

+---------+---------------+-------+---------------------------------------+
| Version | App Name      | Label | Notes                                 |
+=========+===============+=======+=======================================+
| 1.0     | anyvcs        | 0001  |                                       |
+---------+---------------+-------+---------------------------------------+
| 1.1     | anyvcs        | 0002  |                                       |
+---------+---------------+-------+---------------------------------------+
| 2.0     | django_anyvcs | 0001  | See Upgrading from 1.1.x to 2.x below |
+---------+---------------+-------+---------------------------------------+
| 2.1     | django_anyvcs | 0004  |                                       |
+---------+---------------+-------+---------------------------------------+
| 2.4     | django_anyvcs | 0001  | Start using Django migrations         |
+---------+---------------+-------+---------------------------------------+

To upgrade, install the new version of django-anyvcs and then migrate your
project to its corresponding label from the table above using the following
command::

  python manage.py migrate <app_name> <label>

To downgrade, perform the migration down to the label of the desired version
before installing the older django-anyvcs.

Upgrading from <=2.3.x to 2.4.x
-------------------------------

Starting with django-anyvcs 2.4, South support is discontinued in favor of
Django's native migration system. The preferred upgrade path for pre-2.4
installations of django-anyvcs is:

1. Upgrade to South 1.0+.
2. Upgrade to django-anyvcs 2.3 using the South migrations.
3. Remove south from your ``INSTALLED_APPS``.
4. Upgrade to Django 1.7+ and django-anyvcs 2.4+.
5. Run ``python manage.py migrate --fake-initial``.

You may also read Django's instructions on `upgrading from south`_.

.. _`upgrading from south`: https://docs.djangoproject.com/en/dev/topics/migrations/#upgrading-from-south

Upgrading from pre-2.3
----------------------

django-anyvcs 2.3 reorganizes the VCSREPO_ROOT directory structure.  The
changes are fully backwards compatible with git and Mercurial, but temporarily
breaks accessing Subversion over SSH.  To fix this, enter the Django admin
site, select all Subversion repositories and run the "relocate path" action.

If you want the new directory structure applied to git and Mercurial
repositories as well, run the "relocate path" action on them as well.

Upgrading from 1.1.x to 2.x
---------------------------

django-anyvcs 2.x renames the anyvcs app to django_anyvcs so that there is not
a name clash with the python-anyvcs_ module.  However, the database table
names are not changed.

To upgrade, all references to the anyvcs module must be changed to
django_anyvcs.  This includes all instances of "import anyvcs" or
"from anyvcs import ..." and all references to anyvcs in url patterns, views,
or templates, as well as updating INSTALLED_APPS in settings.py.

Once you have made those changes you will need to fake the initial migration
for django_anyvcs::

  python manage.py migrate --fake django_anyvcs 0001_initial

This completes the upgrade process.  The only thing that remains is the two
existing migration records in the south_migrationhistory table from the now
nonexistent anyvcs app.  These records do not cause any problems, but they can
be removed at your discrection using the following SQL statement on your
database::

  DELETE FROM south_migrationhistory WHERE app_name="anyvcs";

.. _South: http://south.aeracode.org/
.. _python-anyvcs: https://github.com/ScottDuckworth/python-anyvcs
