# 유틸리티 기능 관련 뷰들
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest

from ..models import AttendanceMonthly


# 전월 복사 기능
@require_POST
@login_required
def copy_prev_month(request):
    employee_no = request.user.employee_no  # 로그인한 사원번호
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

    print("employee_no:", employee_no)
    print("prev_year:", prev_year)
    print("prev_month:", prev_month)
    print("DB rows:", AttendanceMonthly.objects.filter(employee__employee_no=employee_no).values('year', 'month'))

    try:
        prev_obj = AttendanceMonthly.objects.get(
            employee__employee_no=employee_no, year=prev_year, month=prev_month
        )
    except AttendanceMonthly.DoesNotExist:
        return HttpResponseBadRequest('前月の情報がありません。')

    if AttendanceMonthly.objects.filter(employee__employee_no=employee_no, year=year, month=month).exists():
        return HttpResponseBadRequest('今月の情報は既に存在します。')

    # Employee 객체 가져오기
    employee = request.user

    new_obj = AttendanceMonthly(
        employee=employee,
        year=year,
        month=month,
        project_name=prev_obj.project_name,
        base_calendar=prev_obj.base_calendar,
        break_minutes=prev_obj.break_minutes,
        standard_work_hours=prev_obj.standard_work_hours,
        is_confirmed=False,
        is_required=False,
    )
    new_obj.save()

    return JsonResponse({'result': 'ok'}) 