from django import forms
from django import template

register = template.Library()


@register.filter
def bootstrap_field(field):
    """Django 폼의 검증과 값을 유지하면서 Bootstrap 입력창 클래스를 추가합니다."""
    widget = field.field.widget
    if isinstance(widget, forms.Select):
        css_class = 'form-select'
    elif isinstance(widget, forms.CheckboxInput):
        css_class = 'form-check-input'
    else:
        css_class = 'form-control'
    classes = widget.attrs.get('class', '').split()
    if css_class not in classes:
        classes.append(css_class)
    attrs = {}
    descriptions = widget.attrs.get('aria-describedby', '').split()
    if field.help_text:
        descriptions.append(f'{field.auto_id}_help')
    if field.errors:
        classes.append('is-invalid')
        attrs['aria-invalid'] = 'true'
        descriptions.append(f'{field.auto_id}_errors')
    if descriptions:
        attrs['aria-describedby'] = ' '.join(dict.fromkeys(descriptions))
    attrs['class'] = ' '.join(classes)
    return field.as_widget(attrs=attrs)


@register.filter
def is_checkbox_group(field):
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)
