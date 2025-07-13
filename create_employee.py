#!/usr/bin/env python
"""
새로운 Employee 계정을 생성하는 스크립트
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techave_kintai.settings')
django.setup()

from attendance.models import Employee

def create_employee_from_args(employee_no, password, first_name, last_name, email, place_work, is_superuser=False):
    """명령줄 인수를 받아 새로운 Employee 계정을 생성합니다."""

    print("=== 새로운 Employee 계정 생성 ===")

    try:
        employee = Employee.objects.create_user(
            employee_no=employee_no,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            place_work=place_work,
            is_superuser=is_superuser # 인수로 받도록 변경
        )
        print("\n✅ 계정 생성 완료!")
        print(f"사원번호: {employee.employee_no}")
        print(f"이름: {employee.last_name}{employee.first_name}")
        print(f"이메일: {employee.email}")
        print("\n로그인 URL: http://127.0.0.1:8000/login/")
    except Exception as e:
        print(f"❌ 계정 생성 실패: {e}")
        return False
    return True

def list_employees():
    """기존 Employee 목록을 출력합니다."""
    print("\n=== 기존 Employee 목록 ===")
    employees = Employee.objects.all().order_by('employee_no')
    if not employees:
        print("등록된 Employee가 없습니다.")
        return
    for emp in employees:
        print(f"사원번호: {emp.employee_no} | 이름: {emp.last_name}　{emp.first_name} | 이메일: {emp.email} | 부서: {emp.place_work}")


if __name__ == "__main__":
    # 명령줄 인수가 충분한지 확인 (스크립트 이름 제외 6개 필요)
    if len(sys.argv) == 1:
        print("Employee 계정 관리 도구")
        print("1. 새 계정 생성 (예: python create_employee.py create <사원번호> <비밀번호> <명> <성> <이메일> <부서> [is_superuser True/False])")
        print("2. 기존 계정 목록 보기 (예: python create_employee.py list)")
        print("\n선택하세요.")
    elif sys.argv[1] == "create":
        if len(sys.argv) < 7: # 최소 6개 인자 + 'create' 명령
            print("사용법: python create_employee.py create <사원번호> <비밀번호> <명> <성> <이메일> <부서> [is_superuser True/False]")
            sys.exit(1)

        # is_superuser는 옵션이므로 기본값을 False로 설정하고, 8번째 인자가 있다면 True로 설정
        is_superuser_arg = sys.argv[8].lower() == 'true' if len(sys.argv) > 8 else False

        create_employee_from_args(
            employee_no=sys.argv[2],
            password=sys.argv[3],
            first_name=sys.argv[4],
            last_name=sys.argv[5],
            email=sys.argv[6],
            place_work=sys.argv[7],
            is_superuser=is_superuser_arg
        )
    elif sys.argv[1] == "list":
        list_employees()
    else:
        print("잘못된 명령입니다. 'create' 또는 'list'를 사용하세요.")