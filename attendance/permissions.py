"""
권한 관리 모듈
Django 권한 시스템을 활용한 중앙화된 권한 체크 로직
"""

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

# 권한 상수 정의
PERMISSIONS = {
    'ADMIN_ACCESS': 'attendance.can_access_admin',
    'EMPLOYEE_VIEW': 'attendance.view_employee',
    'EMPLOYEE_ADD': 'attendance.add_employee',
    'EMPLOYEE_CHANGE': 'attendance.change_employee',
    'EMPLOYEE_DELETE': 'attendance.delete_employee',
    'MONTHLY_VIEW': 'attendance.view_attendancemonthly',
    'MONTHLY_ADD': 'attendance.add_attendancemonthly',
    'MONTHLY_CHANGE': 'attendance.change_attendancemonthly',
    'MONTHLY_DELETE': 'attendance.delete_attendancemonthly',
    'DAILY_VIEW': 'attendance.view_attendancedaily',
    'DAILY_ADD': 'attendance.add_attendancedaily',
    'DAILY_CHANGE': 'attendance.change_attendancedaily',
    'DAILY_DELETE': 'attendance.delete_attendancedaily',
    'PAYSLIP_VIEW': 'attendance.view_payslip',
    'PAYSLIP_ADD': 'attendance.add_payslip',
    'PAYSLIP_CHANGE': 'attendance.change_payslip',
    'PAYSLIP_DELETE': 'attendance.delete_payslip',
    'PAID_LEAVE_VIEW': 'attendance.view_paidleave',
    'PAID_LEAVE_ADD': 'attendance.add_paidleave',
    'PAID_LEAVE_CHANGE': 'attendance.change_paidleave',
    'PAID_LEAVE_DELETE': 'attendance.delete_paidleave',
}

# 근무지 그룹 정의
WORK_PLACE_GROUPS = {
    '営業部': ['営業部'],
    '管理部': ['管理部'],
    '日立グループ': ['日立1部', '日立2部'],
    '東京グループ': ['東京1部', '東京2部', '東京3部'],
    '中部事業所': ['中部事業所'],
}

# 그룹별 권한 매핑
GROUP_PERMISSIONS = {
    '社長': [
        PERMISSIONS['ADMIN_ACCESS'],
        PERMISSIONS['EMPLOYEE_VIEW'], PERMISSIONS['EMPLOYEE_ADD'], 
        PERMISSIONS['EMPLOYEE_CHANGE'], PERMISSIONS['EMPLOYEE_DELETE'],
        PERMISSIONS['MONTHLY_VIEW'], PERMISSIONS['MONTHLY_ADD'],
        PERMISSIONS['MONTHLY_CHANGE'], PERMISSIONS['MONTHLY_DELETE'],
        PERMISSIONS['DAILY_VIEW'], PERMISSIONS['DAILY_ADD'],
        PERMISSIONS['DAILY_CHANGE'], PERMISSIONS['DAILY_DELETE'],
        PERMISSIONS['PAYSLIP_VIEW'], PERMISSIONS['PAYSLIP_ADD'],
        PERMISSIONS['PAYSLIP_CHANGE'], PERMISSIONS['PAYSLIP_DELETE'],
        PERMISSIONS['PAID_LEAVE_VIEW'], PERMISSIONS['PAID_LEAVE_ADD'],
        PERMISSIONS['PAID_LEAVE_CHANGE'], PERMISSIONS['PAID_LEAVE_DELETE'],
    ],
    '部長': [
        PERMISSIONS['ADMIN_ACCESS'],
        PERMISSIONS['EMPLOYEE_VIEW'],
        PERMISSIONS['MONTHLY_VIEW'], PERMISSIONS['MONTHLY_CHANGE'],
        PERMISSIONS['DAILY_VIEW'], PERMISSIONS['DAILY_CHANGE'],
        PERMISSIONS['PAID_LEAVE_VIEW'],
    ],
    '役員': [
        PERMISSIONS['ADMIN_ACCESS'],
        PERMISSIONS['EMPLOYEE_VIEW'],
        PERMISSIONS['MONTHLY_VIEW'],
        PERMISSIONS['DAILY_VIEW'],
        PERMISSIONS['PAYSLIP_VIEW'],
        PERMISSIONS['PAID_LEAVE_VIEW'],
    ],
}

def has_permission(user, permission_codename):
    """
    사용자가 특정 권한을 가지고 있는지 확인
    """
    if user.is_superuser:
        return True
    return user.has_perm(permission_codename)

def has_group_permission(user, group_name):
    """
    사용자가 특정 그룹의 권한을 가지고 있는지 확인
    """
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()

def permission_required(permission_codename, redirect_url=None):
    """
    권한 체크 데코레이터
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not has_permission(request.user, permission_codename):
                if redirect_url:
                    messages.error(request, '권한이 없습니다.')
                    return redirect(redirect_url)
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def group_permission_required(group_name, redirect_url=None):
    """
    그룹 권한 체크 데코레이터
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not has_group_permission(request.user, group_name):
                if redirect_url:
                    messages.error(request, '권한이 없습니다.')
                    return redirect(redirect_url)
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def can_access_employee_data(user, target_employee):
    """
    사용자가 특정 직원의 데이터에 접근할 수 있는지 확인
    """
    if user.is_superuser:
        return True
    
    # 사장님은 모든 직원 데이터 접근 가능
    if has_group_permission(user, '社長'):
        return True
    
    # 부장님은 근무지 그룹별로 접근 가능
    if has_group_permission(user, '部長'):
        user_place = (user.place_work or '').strip()
        target_place = (target_employee.place_work or '').strip()
        
        # 같은 근무지인 경우
        if user_place == target_place:
            return True
        
        # 근무지 그룹별 접근 권한 확인
        for group_name, places in WORK_PLACE_GROUPS.items():
            if user_place in places and target_place in places:
                return True
        
        return False
    
    # 일반 직원은 자신의 데이터만 접근 가능
    return user.employee_no == target_employee.employee_no

def get_user_permissions(user):
    """
    사용자가 가지고 있는 모든 권한 반환
    """
    if user.is_superuser:
        return list(PERMISSIONS.values())
    
    permissions = []
    for group_name, group_perms in GROUP_PERMISSIONS.items():
        if has_group_permission(user, group_name):
            permissions.extend(group_perms)
    
    # 중복 제거
    return list(set(permissions))

def get_accessible_work_places(user):
    """
    사용자가 접근할 수 있는 근무지 목록 반환
    """
    if user.is_superuser or has_group_permission(user, '社長'):
        # 모든 근무지 접근 가능
        all_places = set()
        for places in WORK_PLACE_GROUPS.values():
            all_places.update(places)
        return list(all_places)
    
    if has_group_permission(user, '部長'):
        user_place = (user.place_work or '').strip()
        accessible_places = set()
        
        # 근무지 그룹별 접근 권한 확인
        for group_name, places in WORK_PLACE_GROUPS.items():
            if user_place in places:
                accessible_places.update(places)
                break
        
        return list(accessible_places)
    
    # 일반 직원은 자신의 근무지만 접근 가능
    return [user.place_work] if user.place_work else []

def get_work_place_group(place_work):
    """
    근무지가 속한 그룹명 반환
    """
    place_work = (place_work or '').strip()
    for group_name, places in WORK_PLACE_GROUPS.items():
        if place_work in places:
            return group_name
    return None

def setup_group_permissions():
    """
    그룹별 권한 설정 (마이그레이션 후 실행)
    """
    for group_name, permission_codenames in GROUP_PERMISSIONS.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"✅ 그룹 생성: {group_name}")
        
        # 기존 권한 제거
        group.permissions.clear()
        
        # 새 권한 추가
        for codename in permission_codenames:
            try:
                permission = Permission.objects.get(codename=codename.split('.')[-1])
                group.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"⚠️ 권한을 찾을 수 없음: {codename}")
        
        print(f"✅ {group_name} 그룹에 {len(permission_codenames)}개 권한 설정")
