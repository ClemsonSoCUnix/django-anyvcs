# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserRights.created'
        db.add_column('anyvcs_userrights', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True), keep_default=False)

        # Adding field 'UserRights.last_modified'
        db.add_column('anyvcs_userrights', 'last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True), keep_default=False)

        # Adding field 'GroupRights.created'
        db.add_column('anyvcs_grouprights', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True), keep_default=False)

        # Adding field 'GroupRights.last_modified'
        db.add_column('anyvcs_grouprights', 'last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True), keep_default=False)

        # Adding field 'Repo.created'
        db.add_column('anyvcs_repo', 'created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True), keep_default=False)

        # Adding field 'Repo.last_modified'
        db.add_column('anyvcs_repo', 'last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserRights.created'
        db.delete_column('anyvcs_userrights', 'created')

        # Deleting field 'UserRights.last_modified'
        db.delete_column('anyvcs_userrights', 'last_modified')

        # Deleting field 'GroupRights.created'
        db.delete_column('anyvcs_grouprights', 'created')

        # Deleting field 'GroupRights.last_modified'
        db.delete_column('anyvcs_grouprights', 'last_modified')

        # Deleting field 'Repo.created'
        db.delete_column('anyvcs_repo', 'created')

        # Deleting field 'Repo.last_modified'
        db.delete_column('anyvcs_repo', 'last_modified')


    models = {
        'anyvcs.grouprights': {
            'Meta': {'unique_together': "(('repo', 'group'),)", 'object_name': 'GroupRights'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['anyvcs.Repo']"}),
            'rights': ('django.db.models.fields.CharField', [], {'default': "'rw'", 'max_length': '2'})
        },
        'anyvcs.repo': {
            'Meta': {'object_name': 'Repo'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'blank': 'True'}),
            'public_rights': ('django.db.models.fields.CharField', [], {'default': "'-'", 'max_length': '2'}),
            'vcs': ('django.db.models.fields.CharField', [], {'default': "'git'", 'max_length': '3'})
        },
        'anyvcs.userrights': {
            'Meta': {'unique_together': "(('repo', 'user'),)", 'object_name': 'UserRights'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'repo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['anyvcs.Repo']"}),
            'rights': ('django.db.models.fields.CharField', [], {'default': "'rw'", 'max_length': '2'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['anyvcs']
