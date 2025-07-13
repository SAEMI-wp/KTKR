#!/usr/bin/env python
"""
새로운 Employee 계정을 생성하는 스크립트 (비대화형)
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techave_kintai.settings')
django.setup()

from attendance.models import Employee

def create_initial_employee():
    """초기값으로 새로운 Employee 계정을 생성합니다."""

    print("=== 초기 Employee 계정 생성 ===")

    # 여기에 원하는 초기값 설정
    employee_no = "200370"
    password = "0000" # 실제 사용할 안전한 비밀번호로 변경하세요!
    first_name = "セミ"
    last_name = "けん"
    email = "admin@yourけんcompany.com" # 실제 이메일로 변경
    place_work = "경영지원팀"

    try:
        employee = Employee.objects.create_user(
            employee_no=employee_no,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            place_work=place_work,
            is_superuser=True # 슈퍼유저로 설정
        )
        print("\n✅ 초기 계정 생성 완료!")
        print(f"사원번호: {employee.employee_no}")
        print(f"이름: {employee.last_name}{employee.first_name}")
        print(f"이메일: {employee.email}")
        print("\n로그인 URL: http://도메인주소/login/") # 실제 Railway 도메인으로 변경 안내
    except Exception as e:
        # 이미 존재하는 계정인 경우 오류를 무시하거나 특정 메시지 출력
        if "duplicate key" in str(e).lower() or "already exists" in str(e).lower():
            print(f"⚠️ 계정이 이미 존재합니다. (사원번호: {employee_no})")
        else:
            print(f"❌ 계정 생성 실패: {e}")
        return False
    return True

if __name__ == "__main__":
    # 이 스크립트는 매번 실행될 필요는 없으므로,
    # 개발 환경에서 한 번만 실행하거나,
    # 배포 자동화에 포함하려면 조건을 추가해야 합니다.
    create_initial_employee()