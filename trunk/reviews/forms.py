"""
Review components for Django's form library.
"""
import datetime
from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.text import get_text_list
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode
from reviews.models import Review


REVIEW_MAX_LENGTH = getattr(settings,'REVIEW_MAX_LENGTH', 3000)
REVIEWS_ALLOW_PROFANITIES = getattr(settings,'REVIEWS_ALLOW_PROFANITIES', False)


class ReviewForm(forms.ModelForm):
    
    content = forms.CharField(label=_('Review Content'), widget=forms.Textarea,
                                max_length=REVIEW_MAX_LENGTH)
    
    content_type  = forms.CharField(widget=forms.HiddenInput)
    object_pk     = forms.CharField(widget=forms.HiddenInput)

    
    class Meta:
        model = Review
        exclude = ('user',)

    def __init__(self, target_object, data=None, initial=None):
        self.target_object = target_object
        if initial is None:
            initial = {}
        initial.update(self.generate_object_data())

        if initial is None:
            initial = {}
        super(ReviewForm, self).__init__(data=data, initial=initial)
        
    def generate_object_data(self):
        """Generate a dict of security data for "initial" data."""
        object_dict =   {
            'content_type'  : str(self.target_object._meta),
            'object_pk'     : str(self.target_object._get_pk_val()),
        }
        return object_dict
    
    def get_review_object(self):
        """
        Return a new (unsaved) review object based on the information in this
        form. Assumes that the form is already validated and will throw a
        ValueError if not.

        Does not set any of the fields that would come from a Request object
        (i.e. ``user``).
        """
        if not self.is_valid():
            raise ValueError("get_review_object may only be called on valid forms")

        new = Review(
            content_type = ContentType.objects.get_for_model(self.target_object),
            object_pk    = force_unicode(self.target_object._get_pk_val()),
            title    = self.cleaned_data["title"],
            content   = self.cleaned_data["content"],
            rating     = self.cleaned_data["rating"],
            date  = datetime.datetime.now(),
        )

        return new


    
    def clean_content(self):
        """
        If REVIEWS_ALLOW_PROFANITIES is False, check that the review doesn't
        contain anything in PROFANITIES_LIST.
        """
        content = self.cleaned_data["content"]
        if REVIEWS_ALLOW_PROFANITIES == False:
            bad_words = [w for w in settings.PROFANITIES_LIST if w in content.lower()]
            if bad_words:
                plural = len(bad_words) > 1
                raise forms.ValidationError(ngettext(
                    "he word %s is not allowed here.",
                    "The words %s are not allowed here.", plural) % \
                    get_text_list(['"%s%s%s"' % (i[0], '-'*(len(i)-2), i[-1]) for i in bad_words], 'and'))
        return content
