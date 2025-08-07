#!/usr/bin/env python
"""
Railway 배포환경용 Admin Auth 설정 스크립트
기본 그룹, 권한, 슈퍼유저 설정
"""

import os
import django

# ジャンゴ 設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techave_kintai.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from attendance.models import Employee
from django.db import connection

def setup_railway_auth():
    """Railway 環境用の基本認証設定"""
    print("🚀 Railway Admin Auth 設定を開始します...")
    
    # 1. 基本グループの作成
    print("📋 基本グループの作成中...")
    groups_data = {
        '1': '社長',
        '2': '役員', 
        '100': '部長',
        '101': '担当部長',
        '102': '主幹技師',
        '104': '技師',
        '105': '企画員',
        '106': '社員',
    }
    
    created_groups = {}
    for code, name in groups_data.items():
        group, created = Group.objects.get_or_create(name=name)
        created_groups[code] = group
        if created:
            print(f"✅ 그룹 생성: {name} (코드: {code})")
        else:
            print(f"ℹ️ 기존 그룹: {name} (코드: {code})")
    
    # 2. 권한 설정
    print("\n🔐 권한 설정 중...")
    try:
        # attendance 앱의 모든 권한 가져오기
        attendance_permissions = Permission.objects.filter(
            content_type__app_label='attendance'
        )
        
        # 社長 그룹에 모든 권한 부여
        president_group = created_groups['1']
        for perm in attendance_permissions:
            president_group.permissions.add(perm)
        print(f"✅ 社長 그룹에 {attendance_permissions.count()}개 권한 부여")
        
        # 部長 그룹에 필요한 권한만 부여
        bucho_group = created_groups['100']
        bucho_permissions = attendance_permissions.filter(
            codename__in=['can_access_admin', 'view_employee', 'view_attendancemonthly', 'view_attendancedaily']
        )
        for perm in bucho_permissions:
            bucho_group.permissions.add(perm)
        print(f"✅ 部長 그룹에 {bucho_permissions.count()}개 권한 부여")
        
    except Exception as e:
        print(f"⚠️ 권한 설정 중 오류: {e}")
    
    # 3. 기본 슈퍼유저 생성 (없는 경우)
    print("\n👤 기본 슈퍼유저 확인 중...")
    try:
        # 사장님 계정 확인 (100001)
        president_user, created = Employee.objects.get_or_create(
            employee_no='100001',
            defaults={
                'first_name': '社長',
                'last_name': '管理者',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
                'employee_group': '1'
            }
        )
        
        if created:
            president_user.set_password('admin1234')  # 기본 비밀번호
            president_user.save()
            print("✅ 기본 슈퍼유저 생성: 100001 (비밀번호: admin1234)")
        else:
            # 기존 사용자를 슈퍼유저로 설정
            if not president_user.is_superuser:
                president_user.is_superuser = True
                president_user.is_staff = True
                president_user.employee_group = '1'
                president_user.save()
                print("✅ 기존 사용자를 슈퍼유저로 설정: 100001")
            else:
                print("ℹ️ 기존 슈퍼유저: 100001")
        
        # 社長 그룹에 추가
        president_group.user_set.add(president_user)
        
    except Exception as e:
        print(f"⚠️ 슈퍼유저 설정 중 오류: {e}")
    
    # 4. employee_group 테이블 생성 (필요한 경우)
    print("\n🗄️ employee_group 테이블 확인 중...")
    try:
        with connection.cursor() as cursor:
            # MySQL 호환 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_group (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    group_code VARCHAR(10) UNIQUE NOT NULL,
                    group_name VARCHAR(50) NOT NULL
                )
            """)
            
            # 기본 데이터 삽입 (MySQL 호환)
            for code, name in groups_data.items():
                cursor.execute("""
                    INSERT IGNORE INTO employee_group (group_code, group_name) 
                    VALUES (%s, %s)
                """, [code, name])
            
            print("✅ employee_group 테이블 설정 완료")
            
    except Exception as e:
        print(f"⚠️ employee_group 테이블 설정 중 오류: {e}")
    
    print("\n🎉 Railway Admin Auth 설정이 완료되었습니다!")
    print("\n📝 다음 단계:")
    print("1. Railway에 코드 배포")
    print("2. Railway에서 'python setup_railway_auth.py' 실행")
    print("3. 기본 로그인: 100001 / admin1234")

if __name__ == '__main__':
    setup_railway_auth() 