from django.core.exceptions import ObjectDoesNotExist
from django import http
from django.db import models
from reviews.forms import ReviewForm
from utilities import render_response
import urllib
from django.http import HttpResponseRedirect



class ReviewPostBadRequest(http.HttpResponseBadRequest):
    """
    Response returned when a review post is invalid. If ``DEBUG`` is on a
    nice-ish error message will be displayed (for debugging purposes), but in
    production mode a simple opaque 400 page will be displayed.
    """
    def __init__(self, why):
        super(ReviewPostBadRequest, self).__init__()
        if settings.DEBUG:
            self.content = render_to_string("reviews/400-debug.html", {"why": why})


def post_review(request, template_name='reviews/photo_upload.html', next=None):

    if request.method == 'POST':
        # Fill out some initial data fields from an authenticated user, if present
        data = request.POST.copy()
    
        # Look up the object we're trying to review about
        ctype = data.get("content_type")
        object_pk = data.get("object_pk")
        if ctype is None or object_pk is None:
            return ReviewPostBadRequest("Missing content_type or object_pk field.")
        try:
            model = models.get_model(*ctype.split(".", 1))
            target = model._default_manager.get(pk=object_pk)
        except TypeError:
            return ReviewPostBadRequest(
                "Invalid content_type value: %r" % escape(ctype))
        except AttributeError:
            return ReviewPostBadRequest(
                "The given content-type %r does not resolve to a valid model." % \
                    escape(ctype))
        except ObjectDoesNotExist:
            return ReviewPostBadRequest(
                "No object matching content-type %r and object PK %r exists." % \
                    (escape(ctype), escape(object_pk)))
    
        # Construct the review form
        form = ReviewForm(target, data=data)
    
        # If there are errors or if we requested a preview show the review
        if form.errors:
            template_list = [
                "reviews/%s_%s_preview.html" % tuple(str(model._meta).split(".")),
                "reviews/%s_preview.html" % model._meta.app_label,
                "reviews/preview.html",
            ]
            return render_to_response(
                template_list, {
                    "review" : form.data.get("review", ""),
                    "form" : form,
                }, 
                RequestContext(request, {})
            )
    
        # Otherwise create the review
        review = form.get_review_object()
        if request.user.is_authenticated():
            review.user = request.user
    
        # Save the review
        review.save()
        return HttpResponseRedirect(data.get('next'))
    else:
        add_form = ReviewForm()

    return render_response(request, template_name, { 'form': add_form, })

