from django import template

from core.admin_dashboard import dashboard_summary

register = template.Library()


@register.simple_tag
def admin_dashboard_summary():
    return dashboard_summary()
