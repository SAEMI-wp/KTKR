# 유틸리티 기능 관련 뷰들
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import models

from ..models import AttendanceMonthly
from ..models import Employee


# 전월 복사 기능 (새로운 버전)
@csrf_exempt
@require_POST
@login_required
def copy_prev_month(request):
    import json
    
    employee_no = request.user.employee_no  # 로그인한 사원번호
    
    # JSON 요청 처리
    if request.headers.get('Content-Type') == 'application/json':
        data = json.loads(request.body)
        year = int(data.get('year'))
        month = int(data.get('month'))
    else:
        # 기존 POST 요청 처리 (호환성 유지)
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))

    # 전월 계산
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    # 모두 문자열로 변환
    year = str(year)
    month = f"{int(month):02d}"
    prev_year = str(prev_year)
    prev_month = f"{int(prev_month):02d}"

    print(f"[COPY] 복사 요청: {employee_no} - {prev_year}/{prev_month} → {year}/{month}")

    try:
        # 이전 월 데이터 가져오기
        prev_obj = AttendanceMonthly.objects.get(
            employee__employee_no=employee_no, year=prev_year, month=prev_month
        )
    except AttendanceMonthly.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '前月の情報がありません。'
        }, status=400)

    # 현재 월에 이미 데이터가 있는지 확인
    if AttendanceMonthly.objects.filter(employee__employee_no=employee_no, year=year, month=month).exists():
        return JsonResponse({
            'status': 'error',
            'message': '今月の情報は既に存在します。'
        }, status=400)

    # Employee 객체 가져오기
    employee = request.user

    # 새로운 월정보 생성 (이전 월 데이터 복사)
    new_obj = AttendanceMonthly(
        employee=employee,
        year=year,
        month=month,
        project_name=prev_obj.project_name,
        base_calendar=prev_obj.base_calendar,  # Calendar 객체 참조
        is_confirmed=False,
        is_required=False,
    )
    new_obj.save()

    # 캐시 무효화 (새로 생성된 월의 캐시 삭제)
    from ..cache_utils import invalidate_monthly_cache
    invalidate_monthly_cache(
        employee_id=employee_no,
        year=year,
        month=month
    )

    print(f"[COPY] 복사 완료: {employee_no} - {year}/{month}")

    return JsonResponse({
        'status': 'success',
        'message': '前月の情報が正常にコピーされました。'
    })

# 推奨メール受信者リストAPI
@require_GET
@login_required
def email_candidates(request):
    user = request.user
    # place_workが同じ、または特定の社員番号
    candidates = Employee.objects.filter(
        models.Q(place_work=user.place_work) |
        models.Q(employee_no__in=["100001", "500195"])
    ).exclude(email="").distinct()
    data = [
        {
            "employee_no": c.employee_no,
            "display_name": c.display_name,
            "email": c.email
        }
        for c in candidates
    ]
    return JsonResponse({"candidates": data})