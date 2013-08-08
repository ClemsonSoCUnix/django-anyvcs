from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('anyvcs.views',
  url(r'^access/(?P<repo>.+)$', 'access'),
)
