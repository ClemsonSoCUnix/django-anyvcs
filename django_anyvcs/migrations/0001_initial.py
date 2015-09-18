# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupRights',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rights', models.CharField(default=b'rw', max_length=2, choices=[(b'-', b'Deny'), (b'r', b'Read-Only'), (b'rw', b'Read-Write')])),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_modified', models.DateTimeField(auto_now=True, null=True)),
                ('group', models.ForeignKey(to='auth.Group')),
            ],
            options={
                'db_table': 'anyvcs_grouprights',
                'verbose_name': 'Group Access Rights',
                'verbose_name_plural': 'Group Access Rights',
            },
        ),
        migrations.CreateModel(
            name='Repo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, db_index=True)),
                ('path', models.CharField(help_text=b'Either relative to VCSREPO_ROOT or absolute. Changing this will move the repository on disk.', unique=True, max_length=100, blank=True)),
                ('vcs', models.CharField(default=b'git', max_length=3, verbose_name=b'Version Control System', choices=[(b'git', b'Git'), (b'hg', b'Mercurial'), (b'svn', b'Subversion')])),
                ('public_read', models.BooleanField(default=False, verbose_name=b'Public Read Access')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_modified', models.DateTimeField(auto_now=True, null=True)),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'anyvcs_repo',
                'verbose_name': 'Repository',
                'verbose_name_plural': 'Repositories',
            },
        ),
        migrations.CreateModel(
            name='UserRights',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rights', models.CharField(default=b'rw', max_length=2, choices=[(b'-', b'Deny'), (b'r', b'Read-Only'), (b'rw', b'Read-Write')])),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_modified', models.DateTimeField(auto_now=True, null=True)),
                ('repo', models.ForeignKey(to='django_anyvcs.Repo')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'anyvcs_userrights',
                'verbose_name': 'User Access Rights',
                'verbose_name_plural': 'User Access Rights',
            },
        ),
        migrations.AddField(
            model_name='grouprights',
            name='repo',
            field=models.ForeignKey(to='django_anyvcs.Repo'),
        ),
        migrations.AlterUniqueTogether(
            name='userrights',
            unique_together=set([('repo', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='grouprights',
            unique_together=set([('repo', 'group')]),
        ),
    ]
