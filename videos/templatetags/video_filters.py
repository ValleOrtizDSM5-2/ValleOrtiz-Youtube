# videos/templatetags/video_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Template filter para obtener valores de diccionarios"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_attribute(obj, attr_name):
    """Obtener atributo de un objeto"""
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    elif isinstance(obj, dict) and attr_name in obj:
        return obj[attr_name]
    return None

@register.filter
def divide(value, arg):
    """Dividir valor por argumento"""
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def split_by_comma(value):
    """Split string by comma and return list"""
    if not value:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    return []

@register.filter(name='trim')
def trim_filter(value):
    """Trim whitespace from both sides"""
    if isinstance(value, str):
        return value.strip()
    return value

# Alias para strip (por si prefieres usar strip)
@register.filter
def strip(value):
    """Strip whitespace from both sides"""
    if isinstance(value, str):
        return value.strip()
    return value

@register.filter
def default_if_none(value, default_value):
    """Return default value if value is None"""
    if value is None:
        return default_value
    return value

@register.filter
def youtube_embed_url(video_id):
    """Generate YouTube embed URL from video ID"""
    if not video_id:
        return ""
    return f"https://www.youtube.com/embed/{video_id}"

@register.filter
def youtube_watch_url(video_id):
    """Generate YouTube watch URL from video ID"""
    if not video_id:
        return ""
    return f"https://www.youtube.com/watch?v={video_id}"