# attendance/apps.py

from django.apps import AppConfig
import os

class AttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendance'

    def ready(self):
        # 이 ready() 메서드는 Django가 모든 앱을 로드하고
        # 데이터베이스가 준비된 후에 단 한 번만 실행됩니다.
        # collectstatic 빌드 중에는 실행되지 않습니다.

        # 개발 환경에서만 이 코드를 실행하도록 하는 것이 좋습니다.
        # 프로덕션 환경에서는 관리자 페이지에서 수동으로 설정하거나,
        # 별도의 데이터 마이그레이션 스크립트를 사용하는 것이 더 안전합니다.
        # Railway 빌드 시에는 DJANGO_ENV가 'development'가 아니므로,
        # RUN_MIGRATIONS 환경 변수를 사용하거나, 단순히 IS_BUILD_PHASE가 아닐 때만 실행되게 할 수 있습니다.
        # 여기서는 Django 기본 동작에 따라 ready()는 빌드 후 런타임에 실행됨을 가정합니다.
        
        # 다만, 만약을 대비하여 IS_BUILD_PHASE가 False일 때만 실행하도록 명시적으로 조건을 추가합니다.
        # os.environ.get('IS_BUILD_PHASE', 'False').lower() == 'true' 이 True이면 빌드 단계이므로,
        # False일 때 (즉, 런타임 단계일 때)만 아래 코드를 실행합니다.
        if os.environ.get('IS_BUILD_PHASE', 'False').lower() != 'true':
            from django.contrib.auth.models import Group, Permission
            from django.db.utils import OperationalError, ProgrammingError

            try:
                # 'can_access_admin' 권한이 없으면 생성 (필요하다면)
                perm, created = Permission.objects.get_or_create(
                    codename='can_access_admin',
                    defaults={'name': 'Can access admin pages', 'content_type': None} # content_type은 나중에 적절히 설정
                )
                if created:
                    print("Created 'can_access_admin' permission.")

                # 그룹을 가져오거나 생성
                president, created_pres = Group.objects.get_or_create(id=1, defaults={'name': '社長'})
                if created_pres:
                    print(f"Created group: {president.name}")

                bucho, created_bucho = Group.objects.get_or_create(id=3, defaults={'name': '部長'})
                if created_bucho:
                    print(f"Created group: {bucho.name}")
                
                # 권한 부여
                if perm not in president.permissions.all():
                    president.permissions.add(perm)
                    print(f'{president.name} グループに管理者ページアクセス権限を付与しました。')
                
                if perm not in bucho.permissions.all():
                    bucho.permissions.add(perm)
                    print(f'{bucho.name} グループに管理者ページアクセス権限を付与しました。')

            except (OperationalError, ProgrammingError) as e:
                print(f"Database not ready or tables missing. Skipping permission setup. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during permission setup: {e}")
        else:
            print("IS_BUILD_PHASE is True. Skipping permission setup in ready() method.")

