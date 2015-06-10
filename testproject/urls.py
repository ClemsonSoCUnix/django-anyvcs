try:
  from django.conf.urls import patterns, include, url
except ImportError:
  from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
  url(r'^anyvcs/', include('django_anyvcs.urls')),
  url(r'^browse/(?P<name>\w+)/$', 'testproject.views.repo_browse'),
  url(r'^browse/(?P<name>\w+)/(?P<rev>[^/]+)/(?P<path>.*)', 'testproject.views.repo_browse'),
  url(r'^sshkeys$', 'django_sshkey.views.lookup'),
  url(r'^admin/', include(admin.site.urls)),
)
