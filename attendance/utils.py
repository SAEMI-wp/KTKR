from typing import List, Optional
from datetime import date, time
from .models import Employee, AttendanceMonthly, AttendanceDaily
from .structures import DailyData, MonthlyData

def convert_daily_to_structure(daily_model: AttendanceDaily, 
                              break_minutes: int = 60,
                              standard_work_hours: float = 8.0) -> DailyData:
    """AttendanceDaily 모델을 DailyData 구조체로 변환 (break_minutes는 분 단위)"""
    return DailyData(
        date=daily_model.date,
        work_type=daily_model.work_type,
        start_time=daily_model.start_time,
        end_time=daily_model.end_time,
        alternative_work_date=daily_model.alternative_work_date,
        notes=daily_model.notes,
        is_required=daily_model.is_required,
        is_confirmed=daily_model.is_confirmed,
        break_minutes=break_minutes,
        standard_work_hours=standard_work_hours
    )

def convert_monthly_to_structure(monthly_model: AttendanceMonthly) -> MonthlyData:
    """AttendanceMonthly 모델을 MonthlyData 구조체로 변환"""
    # 일별 데이터 리스트 생성
    daily_list = []
    daily_models = AttendanceDaily.objects.filter(
        monthly_attendance=monthly_model
    ).order_by('date')
    
    for daily_model in daily_models:
        daily_data = convert_daily_to_structure(
            daily_model,
            break_minutes=monthly_model.break_minutes,
            standard_work_hours=monthly_model.standard_work_hours
        )
        daily_list.append(daily_data)
    
    return MonthlyData(
        employee_id=monthly_model.employee.employee_no,
        year=monthly_model.year,
        month=monthly_model.month,
        project_name=monthly_model.project_name,
        base_calendar=monthly_model.base_calendar,
        break_minutes=monthly_model.break_minutes,
        standard_work_hours=monthly_model.standard_work_hours,
        daily_list=daily_list
    )

def get_or_create_monthly_structure(employee: Employee, year: str, month: str) -> Optional[MonthlyData]:
    """월별 구조체를 가져오거나 생성"""
    # DB에서 월별 데이터 조회
    monthly_model = AttendanceMonthly.objects.filter(
        employee=employee,
        year=year,
        month=month.zfill(2)
    ).first()
    
    if monthly_model:
        # 기존 데이터가 있으면 구조체로 변환
        monthly_data = convert_monthly_to_structure(monthly_model)
        # 모든 일별 시간 계산
        monthly_data.calculate_all_daily_hours()
        return monthly_data
    else:
        # DB에 없으면 None 반환
        return None

def save_daily_from_structure(daily_data: DailyData, monthly_model: AttendanceMonthly) -> AttendanceDaily:
    """DailyData 구조체를 DB에 저장"""
    # 기존 데이터가 있는지 확인
    existing_daily = AttendanceDaily.objects.filter(
        monthly_attendance=monthly_model,
        date=daily_data.date
    ).first()
    
    if existing_daily:
        # 기존 데이터 업데이트
        existing_daily.work_type = daily_data.work_type
        existing_daily.start_time = daily_data.start_time
        existing_daily.end_time = daily_data.end_time
        existing_daily.alternative_work_date = daily_data.alternative_work_date
        existing_daily.notes = daily_data.notes
        existing_daily.is_confirmed = daily_data.is_confirmed
        existing_daily.is_required = daily_data.is_required
        existing_daily.save()
        return existing_daily
    else:
        # 새 데이터 생성
        return AttendanceDaily.objects.create(
            monthly_attendance=monthly_model,
            date=daily_data.date,
            work_type=daily_data.work_type,
            start_time=daily_data.start_time,
            end_time=daily_data.end_time,
            alternative_work_date=daily_data.alternative_work_date,
            notes=daily_data.notes,
            is_confirmed=daily_data.is_confirmed,
            is_required=daily_data.is_required,
        )

def update_monthly_from_structure(monthly_data: MonthlyData, employee: Employee) -> AttendanceMonthly:
    """MonthlyData 구조체를 DB에 저장/업데이트"""
    # 기존 월별 데이터 조회
    monthly_model = AttendanceMonthly.objects.filter(
        employee=employee,
        year=monthly_data.year,
        month=monthly_data.month
    ).first()
    
    if monthly_model:
        # 기존 데이터 업데이트
        monthly_model.project_name = monthly_data.project_name
        monthly_model.base_calendar = monthly_data.base_calendar
        monthly_model.break_minutes = monthly_data.break_minutes
        monthly_model.standard_work_hours = monthly_data.standard_work_hours
        monthly_model.save()
    else:
        # 새 데이터 생성
        monthly_model = AttendanceMonthly.objects.create(
            employee=employee,
            year=monthly_data.year,
            month=monthly_data.month,
            project_name=monthly_data.project_name,
            base_calendar=monthly_data.base_calendar,
            break_minutes=monthly_data.break_minutes,
            standard_work_hours=monthly_data.standard_work_hours
        )
    
    # 일별 데이터도 함께 저장
    for daily_data in monthly_data.daily_list:
        save_daily_from_structure(daily_data, monthly_model)
    
    return monthly_model 