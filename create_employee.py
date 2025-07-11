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

def create_employee():
    """새로운 Employee 계정을 생성합니다."""
    
    print("=== 새로운 Employee 계정 생성 ===")
    
    # 사용자 입력 받기
    employee_no = input("社員番号(6字): ").strip()
    password = input("パスワード: ").strip()
    first_name = input("名: ").strip()
    last_name = input("性: ").strip()
    email = input("メール: ").strip()
    place_work = input("部署").strip()
    
    try:
        # Employee 모델 생성
        employee = Employee.objects.create_user(
            employee_no=employee_no,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            place_work=place_work,
            is_superuser=1
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
        print(f"사원번호: {emp.employee_no} | 이름: {emp.last_name}　{emp.first_name}")

if __name__ == "__main__":
    print("Employee 계정 관리 도구")
    print("1. 새 계정 생성")
    print("2. 기존 계정 목록 보기")
    choice = input("\n선택하세요 (1 또는 2): ").strip()
    if choice == "1":
        create_employee()
    elif choice == "2":
        list_employees()
    else:
        print("잘못된 선택입니다.") 