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

@register.filter
def has_admin_access(user):
    """사용자가 관리자 접근 권한이 있는지 확인합니다."""
    if user.is_superuser:
        return True
    
    # 사용자가 속한 그룹 이름들을 확인
    user_groups = [group.name for group in user.groups.all()]
    admin_positions = ['사장', '이사', '부장']
    
    return any(position in user_groups for position in admin_positions) 