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
            if os.environ.get('RUN_MIGRATIONS', 'False').lower() == 'true' or os.environ.get('DJANGO_ENV', 'development') == 'development':
                from django.contrib.auth.models import Group, Permission
                from django.db.utils import OperationalError, ProgrammingError

                try:
                    # 'can_access_admin' 권한이 없으면 생성 (필요하다면)
                    # 일반적으로 권한은 모델 생성 시 자동으로 생성되므로,
                    # 이 부분은 이미 존재한다고 가정하고 get()만 사용합니다.
                    # 만약 특정 상황에서 권한이 없는 경우를 대비하려면 create_or_update_permission 함수를 만들 수 있습니다.
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
                print("Skipping permission setup in non-migration/non-development environment.")

    
