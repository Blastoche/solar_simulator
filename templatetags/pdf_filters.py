"""
Filtres de template personnalisés pour la génération de PDF
"""
from django import template

register = template.Library()


@register.filter
def sum_consommation(appareils):
    """
    Somme la consommation annuelle d'une liste d'appareils
    
    Usage: {{ appareils|sum_consommation }}
    """
    try:
        return sum(app.consommation_annuelle for app in appareils)
    except (AttributeError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calcule le pourcentage d'une valeur par rapport à un total
    
    Usage: {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """
    Multiplie deux valeurs
    
    Usage: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """
    Soustrait la seconde valeur de la première
    
    Usage: {{ value|subtract:arg }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def add_values(value, arg):
    """
    Additionne deux valeurs
    
    Usage: {{ value|add_values:arg }}
    """
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Divise deux valeurs
    
    Usage: {{ value|divide:arg }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
