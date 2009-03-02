from django import template
from django.conf import settings
from django.template import Library, Node, TemplateSyntaxError, Variable, resolve_variable
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode

from reviews.models import Review
from reviews.forms import ReviewForm

register = template.Library()


class BaseReviewNode(template.Node):
    """
    Base helper class (abstract) for handling the get_review_* template tags.
    Looks a bit strange, but the subclasses below should make this a bit more
    obvious.
    """

    #@classmethod
    def handle_token(cls, parser, token):
        """Class method to parse get_review_list/count/form and return a Node."""
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% get_whatever for obj as varname %}
        if len(tokens) == 5:
            if tokens[3] != 'as':
                raise template.TemplateSyntaxError("Third argument in %r must be 'as'" % tokens[0])
            return cls(
                object_expr = parser.compile_filter(tokens[2]),
                as_varname = tokens[4],
            )

        # {% get_whatever for app.model pk as varname %}
        elif len(tokens) == 6:
            if tokens[4] != 'as':
                raise template.TemplateSyntaxError("Fourth argument in %r must be 'as'" % tokens[0])
            return cls(
                ctype = BaseReviewNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr = parser.compile_filter(tokens[3]),
                as_varname = tokens[5]
            )

        else:
            raise template.TemplateSyntaxError("%r tag requires 4 or 5 arguments" % tokens[0])

    handle_token = classmethod(handle_token)

    #@staticmethod
    def lookup_content_type(token, tagname):
        try:
            app, model = token.split('.')
            return ContentType.objects.get(app_label=app, model=model)
        except ValueError:
            raise template.TemplateSyntaxError("Third argument in %r must be in the format 'app.model'" % tagname)
        except ContentType.DoesNotExist:
            raise template.TemplateSyntaxError("%r tag has non-existant content-type: '%s.%s'" % (tagname, app, model))
    lookup_content_type = staticmethod(lookup_content_type)

    def __init__(self, ctype=None, object_pk_expr=None, object_expr=None, as_varname=None, review=None):
        if ctype is None and object_expr is None:
            raise template.TemplateSyntaxError("Review nodes must be given either a literal object or a ctype and object pk.")
        self.review_model = Review
        self.as_varname = as_varname
        self.ctype = ctype
        self.object_pk_expr = object_pk_expr
        self.object_expr = object_expr
        self.review = review

    def render(self, context):
        qs = self.get_query_set(context)
        context[self.as_varname] = self.get_context_value_from_queryset(context, qs)
        return ''

    def get_query_set(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if not object_pk:
            return self.review_model.objects.none()

        qs = self.review_model.objects.filter(
            content_type = ctype,
            object_pk    = smart_unicode(object_pk),
        )

        return qs

    def get_target_ctype_pk(self, context):
        if self.object_expr:
            try:
                obj = self.object_expr.resolve(context)
            except template.VariableDoesNotExist:
                return None, None
            return ContentType.objects.get_for_model(obj), obj.pk
        else:
            return self.ctype, self.object_pk_expr.resolve(context, ignore_failures=True)

    def get_context_value_from_queryset(self, context, qs):
        """Subclasses should override this."""
        raise NotImplementedError


class ReviewsForObjectNode(Node):
    def __init__(self, obj, context_var):
        self.obj = Variable(obj)
        self.context_var = context_var

    def render(self, context):
        context[self.context_var] = \
            Review.objects.get_for_object(self.obj.resolve(context))
        return ''


def do_reviews_for_object(parser, token):
    """
    Retrieves a list of ``Review`` objects associated with an object and
    stores them in a context variable.

    Usage::

       {% reviews_for_object [object] as [varname] %}

    Example::

        {% reviews_for_object foo_object as review_list %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise TemplateSyntaxError(_('%s review requires exactly three arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s review must be 'as'") % bits[0])
    return ReviewsForObjectNode(bits[1], bits[3])

class RenderReviewFormNode(BaseReviewNode):
    """Render the review form directly"""
    
    #@classmethod
    def handle_token(cls, parser, token):
        """Class method to parse render_review_form and return a Node."""
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% render_review_form for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_review_form for app.models pk %}
        elif len(tokens) == 4:
            return cls(
                ctype = BaseReviewNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr = parser.compile_filter(tokens[3])
            )
    handle_token = classmethod(handle_token)


    def get_form(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            return ReviewForm(ctype.get_object_for_this_type(pk=object_pk))
        else:
            return None

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "reviews/%s/%s/form.html" % (ctype.app_label, ctype.model),
                "reviews/%s/form.html" % ctype.app_label,
                "reviews/form.html"
            ]
            context.push()
            formstr = render_to_string(template_search_list, {"form" : self.get_form(context)}, context)
            context.pop()
            return formstr
        else:
            return ''

#@register.tag
def render_review_form(parser, token):
    """
    Render the review form (as returned by ``{% render_review_form %}``) through
    the ``reviews/form.html`` template.

    Syntax::

        {% render_review_form for [object] %}
        {% render_review_form for [app].[model] [object_id] %}
    """
    return RenderReviewFormNode.handle_token(parser, token)

register.tag(render_review_form)


class ReviewCountNode(BaseReviewNode):
    """Insert a count of reviews into the context."""
    def get_context_value_from_queryset(self, context, qs):
        return qs.count()


#@register.tag
def get_review_count(parser, token):
    """
    Gets the review count for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_review_count for [object] as [varname]  %}
        {% get_review_count for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_review_count for event as review_count %}
        {% get_review_count for calendar.event event.id as review_count %}
        {% get_review_count for calendar.event 17 as review_count %}

    """
    return ReviewCountNode.handle_token(parser, token)

register.tag(get_review_count)

class ReviewAvgRatingNode(BaseReviewNode):
    """Insert an average of ratings ."""
    def get_context_value_from_queryset(self, context, qs):
        cnt = 0
        sum = 0
        avg = None
        for review in qs.all():
            sum += review.rating
            cnt += 1
        if cnt > 0:
            avg = float(float(sum) / float(cnt))
        return avg


#@register.tag
def get_review_avg_ratings(parser, token):
    """
    Gets the review count for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_review_count for [object] as [varname]  %}
        {% get_review_count for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_review_avg_ratings for event as review_count %}
        {% get_review_avg_ratings for calendar.event event.id as review_count %}
        {% get_review_avg_ratings for calendar.event 17 as review_count %}

    """
    return ReviewAvgRatingNode.handle_token(parser, token)

register.tag(get_review_avg_ratings)