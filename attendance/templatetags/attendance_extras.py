from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """문자열을 구분자로 분할합니다."""
    return value.split(arg)

@register.filter
def get_item(lst, index):
    """리스트에서 인덱스로 아이템을 가져옵니다."""
    try:
        return lst[index]
    except (IndexError, TypeError):
        return "" 