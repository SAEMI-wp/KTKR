from django.apps import AppConfig
from django.db.models.signals import post_migrate

def setup_permissions(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission
    from attendance.models import Employee

    # 1. 그룹 생성 및 권한 부여
    president, _ = Group.objects.get_or_create(name='社長')
    bucho, _ = Group.objects.get_or_create(name='部長')
    perms = Permission.objects.filter(content_type__app_label='attendance')
    for perm in perms:
        president.permissions.add(perm)
        bucho.permissions.add(perm)  # 부장님도 필요한 권한만 추가

    # 2. 사장님 계정 슈퍼유저화
    try:
        president_user = Employee.objects.get(employee_no='100001')
        president_user.is_superuser = True
        president_user.save()
    except Employee.DoesNotExist:
        pass

class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendance'

    def ready(self):
        post_migrate.connect(setup_permissions, sender=self)
