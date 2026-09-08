"""Template helpers for applying Design System CSS classes to form fields.

Needed because Django's built-in auth forms (AuthenticationForm,
PasswordResetForm, SetPasswordForm, PasswordChangeForm) can't be edited to
add widget attrs — this lets any template style any bound field without a
third-party dependency (e.g. django-widget-tweaks).
"""

from django import template

register = template.Library()


@register.filter(name="add_class")
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})


_MESSAGE_TAG_TO_ALERT_TYPE = {
    "error": "danger",
    "debug": "info",
}


@register.filter(name="alert_type")
def alert_type(message_tags):
    """Map django.contrib.messages tags (debug/info/success/warning/error) to
    this Design System's Alert variants (info/success/warning/danger)."""
    first_tag = (message_tags or "info").split(" ")[0]
    return _MESSAGE_TAG_TO_ALERT_TYPE.get(first_tag, first_tag)
