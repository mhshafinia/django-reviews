from django.conf.urls.defaults import *
from django.conf import settings
from reviews.views import post_review

urlpatterns = patterns('',
                       url(r'^post/$', post_review, name='reviews-post-review'),
)
