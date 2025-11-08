from django import template

register = template.Library()


@register.filter(name="status_label")
def status_label(value):
    """
    Convert a status identifier like 'admin_approved' into a human-readable
    label such as 'Admin Approved'.
    """
    if not value:
        return ""

    return str(value).replace("_", " ").title()

