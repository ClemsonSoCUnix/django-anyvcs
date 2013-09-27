Upgrading and Downgrading
=========================

django-anyvcs is equipped with [South][1] migrations.  This makes changes to
the database schema in upgrades or downgrades a simple process.  Migrations
will only be present on minor version changes.

To use South migrations, you must have the south app in your project's
INSTALLED_APPS.

The following table maps django-anyvcs version to migration labels:

    Version   App Name        Label   Notes
    1.0.x     anyvcs          0001
    1.1.x     anyvcs          0002
    2.0.x     django_anyvcs   0001    See Upgrading from 1.1.x to 2.x below


To upgrade, install the new version of django-anyvcs and then migrate your
project to its corresponding label from the table above using the following
command:

    python manage.py migrate <app_name> <label>

To downgrade, perform the migration down to the label of the desired version
before installing the older django-anyvcs.


Upgrading from 1.1.x to 2.x
---------------------------

django-anyvcs 2.x renames the anyvcs app to django_anyvcs so that there is not
a name clash with the [python-anyvcs][2] module.  However, the database table
names are not changed.

To upgrade, all references to the anyvcs module must be changed to
django_anyvcs.  This includes all instances of "import anyvcs" or
"from anyvcs import ..." and all references to anyvcs in url patterns, views,
or templates, as well as updating INSTALLED_APPS in settings.py.

Once you have made those changes you will need to fake the initial migration
for django_anyvcs:

    python manage.py migrate --fake django_anyvcs 0001_initial

This completes the upgrade process.  The only thing that remains is the two
existing migration records in the south_migrationhistory table from the now
nonexistent anyvcs app.  These records do not cause any problems, but they can
be removed at your discrection using the following SQL statement on your
database:

    DELETE FROM south_migrationhistory WHERE app_name="anyvcs";

[1]: http://south.aeracode.org/
[2]: https://github.com/ScottDuckworth/python-anyvcs
