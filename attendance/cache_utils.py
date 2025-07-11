"""
Redis 캐싱 유틸리티 모듈
월별 근태 데이터의 캐싱을 담당하는 유틸리티 함수들을 제공합니다.
"""
import json
import pickle
from typing import Optional, Dict, Any
from datetime import datetime, date
from django.core.cache import cache
from django.conf import settings
from .models import Employee, AttendanceMonthly
from .structures import MonthlyData
from .utils import get_or_create_monthly_structure


def generate_cache_key(employee_id: str, year: str, month: str) -> str:
    """
    캐시 키를 생성합니다.
    
    Args:
        employee_id: 사원번호
        year: 년도
        month: 월
        
    Returns:
        캐시 키 문자열
    """
    return f"monthly_data:{employee_id}:{year}:{month.zfill(2)}"


def cache_monthly_data(employee_id: str, year: str, month: str, monthly_data: MonthlyData) -> None:
    """
    월별 데이터를 캐시에 저장합니다.
    
    Args:
        employee_id: 사원번호
        year: 년도
        month: 월
        monthly_data: 캐시할 월별 데이터
    """
    cache_key = generate_cache_key(employee_id, year, month)
    
    # MonthlyData 객체를 딕셔너리로 직렬화
    data_dict = {
        'employee_id': monthly_data.employee_id,
        'year': monthly_data.year,
        'month': monthly_data.month,
        'project_name': monthly_data.project_name,
        'base_calendar': monthly_data.base_calendar,
        'break_minutes': monthly_data.break_minutes,
        'standard_work_hours': monthly_data.standard_work_hours,
        'daily_list': []
    }
    
    # 일별 데이터도 직렬화
    for daily in monthly_data.daily_list:
        daily_dict = {
            'date': daily.date.isoformat(),
            'work_type': daily.work_type,
            'start_time': daily.start_time.isoformat() if daily.start_time else None,
            'end_time': daily.end_time.isoformat() if daily.end_time else None,
            'alternative_work_date': daily.alternative_work_date.isoformat() if daily.alternative_work_date else None,
            'notes': daily.notes,
            'is_confirmed': daily.is_confirmed,
            'break_minutes': daily.break_minutes,
            'standard_work_hours': daily.standard_work_hours,
            'regular_work_hours': daily.regular_work_hours,
            'deduction_hours': daily.deduction_hours,
            'overtime_hours': daily.overtime_hours,
            'late_night_overtime_hours': daily.late_night_overtime_hours,
            'total_hours': daily.total_hours
        }
        data_dict['daily_list'].append(daily_dict)
    
    # JSON으로 직렬화하여 캐시에 저장 (TTL: 1시간)
    cache.set(cache_key, json.dumps(data_dict), timeout=3600)


def get_cached_monthly_data(employee_id: str, year: str, month: str) -> Optional[MonthlyData]:
    """
    캐시에서 월별 데이터를 가져옵니다.
    
    Args:
        employee_id: 사원번호
        year: 년도
        month: 월
        
    Returns:
        캐시된 MonthlyData 객체 또는 None
    """
    cache_key = generate_cache_key(employee_id, year, month)
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        return None
    
    try:
        # JSON에서 딕셔너리로 역직렬화
        data_dict = json.loads(cached_data)
        
        # MonthlyData 객체 재구성
        from .structures import DailyData
        
        # 일별 데이터 재구성
        daily_list = []
        for daily_dict in data_dict['daily_list']:
            daily = DailyData(
                date=date.fromisoformat(daily_dict['date']),
                work_type=daily_dict['work_type'],
                start_time=datetime.fromisoformat(daily_dict['start_time']).time() if daily_dict['start_time'] else None,
                end_time=datetime.fromisoformat(daily_dict['end_time']).time() if daily_dict['end_time'] else None,
                alternative_work_date=date.fromisoformat(daily_dict['alternative_work_date']) if daily_dict['alternative_work_date'] else None,
                notes=daily_dict['notes'],
                is_confirmed=daily_dict['is_confirmed'],
                break_minutes=daily_dict['break_minutes'],
                standard_work_hours=daily_dict['standard_work_hours']
            )
            # 계산된 값들 복원
            daily.regular_work_hours = daily_dict['regular_work_hours']
            daily.deduction_hours = daily_dict['deduction_hours']
            daily.overtime_hours = daily_dict['overtime_hours']
            daily.late_night_overtime_hours = daily_dict['late_night_overtime_hours']
            daily.total_hours = daily_dict['total_hours']
            daily_list.append(daily)
        
        # MonthlyData 객체 생성
        monthly_data = MonthlyData(
            employee_id=data_dict['employee_id'],
            year=data_dict['year'],
            month=data_dict['month'],
            project_name=data_dict['project_name'],
            base_calendar=data_dict['base_calendar'],
            break_minutes=data_dict['break_minutes'],
            standard_work_hours=data_dict['standard_work_hours'],
            daily_list=daily_list
        )
        
        return monthly_data
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # 캐시 데이터가 손상된 경우 캐시 삭제
        cache.delete(cache_key)
        print(f"캐시 데이터 역직렬화 오류: {e}")
        return None


def invalidate_monthly_cache(employee_id: str, year: str, month: str) -> None:
    """
    특정 월의 캐시를 무효화합니다.
    
    Args:
        employee_id: 사원번호
        year: 년도
        month: 월
    """
    cache_key = generate_cache_key(employee_id, year, month)
    cache.delete(cache_key)


def invalidate_employee_cache(employee_id: str) -> None:
    """
    특정 사원의 모든 캐시를 무효화합니다.
    
    Args:
        employee_id: 사원번호
    """
    # Redis에서 패턴 매칭으로 해당 사원의 모든 캐시 삭제
    pattern = f"techave_kintai:monthly_data:{employee_id}:*"
    cache.delete_pattern(pattern)


def get_monthly_data_with_cache(employee: Employee, year: str, month: str) -> Optional[MonthlyData]:
    """
    캐시를 우선 확인하고, 없으면 DB에서 가져와서 캐시에 저장합니다.
    
    Args:
        employee: 사원 객체
        year: 년도
        month: 월
        
    Returns:
        MonthlyData 객체 또는 None
    """
    employee_id = employee.employee_no
    
    # 1. 캐시에서 먼저 확인
    cached_data = get_cached_monthly_data(employee_id, year, month)
    if cached_data:
        print(f"캐시에서 데이터 로드: {employee_id} - {year}/{month}")
        return cached_data
    
    # 2. 캐시에 없으면 DB에서 가져오기
    print(f"DB에서 데이터 로드: {employee_id} - {year}/{month}")
    monthly_data = get_or_create_monthly_structure(employee, year, month)
    
    # 3. DB에서 가져온 데이터를 캐시에 저장
    if monthly_data:
        cache_monthly_data(employee_id, year, month, monthly_data)
        print(f"캐시에 데이터 저장: {employee_id} - {year}/{month}")
    
    return monthly_data


def preload_adjacent_months(employee: Employee, current_year: int, current_month: int) -> Dict[str, Optional[MonthlyData]]:
    """
    현재 월과 인접한 월들의 데이터를 미리 로드합니다.
    
    Args:
        employee: 사원 객체
        current_year: 현재 년도
        current_month: 현재 월
        
    Returns:
        월별 데이터 딕셔너리 (키: "YYYY-MM" 형식)
    """
    preloaded_data = {}
    
    # 이전 월, 현재 월, 다음 월 (총 3개월)
    months_to_load = [
        (current_year, current_month - 1),
        (current_year, current_month),
        (current_year, current_month + 1)
    ]
    
    for year, month in months_to_load:
        # 월이 0이거나 13이 되는 경우 처리
        if month == 0:
            year -= 1
            month = 12
        elif month == 13:
            year += 1
            month = 1
        
        # 데이터 로드 (캐시 우선)
        monthly_data = get_monthly_data_with_cache(employee, str(year), str(month))
        key = f"{year:04d}-{month:02d}"
        preloaded_data[key] = monthly_data
    
    return preloaded_data


def get_monthly_attendance(employee_id, year, month):
    key = f"monthly_attendance:{employee_id}:{year}:{month}"
    data = cache.get(key)
    if data:
        return json.loads(data)
    return None


def set_monthly_attendance(employee_id, year, month, obj):
    key = f"monthly_attendance:{employee_id}:{year}:{month}"
    # obj는 AttendanceMonthly 인스턴스
    data = {
        'employee_id': obj.employee_id,
        'year': obj.year,
        'month': obj.month,
        'project_name': obj.project_name,
        'base_calendar': obj.base_calendar,
        'break_minutes': obj.break_minutes,
        'standard_work_hours': obj.standard_work_hours,
        'is_confirmed': obj.is_confirmed,
        'is_required': obj.is_required,
    }
    cache.set(key, json.dumps(data), timeout=60*60*24)  # 1일 캐시 등 