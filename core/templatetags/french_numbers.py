from django import template

register = template.Library()

@register.filter
def fr_number(value):
    """Formate un nombre avec espace fine comme séparateur de milliers (format français)."""
    try:
        value = int(round(float(value)))
        return f"{value:,}".replace(",", "\u202f")
    except (ValueError, TypeError):
        return value