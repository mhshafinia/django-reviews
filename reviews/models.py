import datetime
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

##########
# Models #
##########


class Review(models.Model):
    """
    A review.
    """
    
    rating = models.PositiveSmallIntegerField(_('rating'))
    title = models.CharField(_('title'), max_length=255)
    content = models.TextField(_('review'))
    date = models.DateTimeField(_('rated on'), editable=False)
    
    user = models.ForeignKey(User, verbose_name=_('user'), null=True,
                             blank=True)
    
    # Content-object field
    content_type   = models.ForeignKey(ContentType,
            related_name="content_type_set_for_%(class)s")
    object_pk      = models.TextField(_('object ID'))
    content_object = generic.GenericForeignKey(ct_field="content_type", fk_field="object_pk")



    class Meta:
        ordering = ('-date',)
        verbose_name = _('review')
        verbose_name_plural = _('reviews')

    def __unicode__(self):
        return self.title

    def save(self):
        if not self.id:
            self.date = datetime.datetime.now()
        super(Review, self).save()
