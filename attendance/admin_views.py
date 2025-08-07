from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Employee, AttendanceMonthly, AttendanceDaily, PaidLeave, PaySlip
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from calendar import monthrange
from datetime import date, timedelta
from django import forms
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from .paroll_pdf import generate_payslip_pdf
from django.contrib import messages
import calendar
from django.contrib.auth.models import Group, Permission
from .views.main_views import get_holidays_for_months
from .structures import DailyData, MonthlyData
from .permissions import (
    permission_required, group_permission_required, 
    can_access_employee_data, PERMISSIONS
)

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def profile_view(request):
    """
    내 프로필 페이지: 성명, 사번, 근무지, 소속 그룹 표시
    """
    user = request.user
    groups = user.groups.values_list('name', flat=True)
    context = {
        'employee': user,
        'groups': groups,
    }
    return render(request, 'admin/attendance/profile.html', context)

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def attendance_overview(request):
    """
    근태관리 메인 페이지: 전체/부서별 월별 근태정보 표
    (기본 틀만 구현)
    """
    # 실제 데이터/필터링은 추후 구현
    employees = Employee.objects.filter(is_active=True)
    context = {
        'employees': employees,
    }
    return render(request, 'admin/attendance/attendance_overview.html', context)

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def payroll_view(request):
    """
    給与明細書管理ページ: 月/年別一覧・PDF保存/印刷ボタン
    """
    user = request.user
    today = timezone.now().date()
    year = str(request.GET.get('year', today.year))
    month = str(request.GET.get('month', str(today.month).zfill(2)))
    # 권한별 직원 필터링
    if user.is_superuser or user.groups.filter(name__in=['社長', '人事', '経理']).exists():
        employees = Employee.objects.filter(is_active=True)
    elif user.groups.filter(name='部長').exists():
        # 부장님은 급여명세서 접근 불가
        from .permissions import get_accessible_work_places
        accessible_places = get_accessible_work_places(user)
        from django.db.models import Q
        place_filters = Q()
        for place in accessible_places:
            place_filters |= Q(place_work=place)
        employees = Employee.objects.filter(is_active=True).filter(place_filters)
    else:
        employees = Employee.objects.filter(is_active=True, employee_no=user.employee_no)
    # 급여명세서 데이터
    rows = []
    for emp in employees:
        try:
            payslip = PaySlip.objects.get(employee=emp, year=year, month=month)
        except PaySlip.DoesNotExist:
            payslip = None
        rows.append({
            'employee': emp,
            'payslip': payslip,
        })
    # 월 이동
    prev_month = int(month) - 1 if int(month) > 1 else 12
    prev_year = int(year) - 1 if int(month) == 1 else int(year)
    next_month = int(month) + 1 if int(month) < 12 else 1
    next_year = int(year) + 1 if int(month) == 12 else int(year)
    context = {
        'rows': rows,
        'year': year,
        'month': month,
        'prev_year': prev_year,
        'prev_month': str(prev_month).zfill(2),
        'next_year': next_year,
        'next_month': str(next_month).zfill(2),
    }
    return render(request, 'admin/attendance/payroll.html', context)

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def employee_detail_view(request, employee_no, year=None, month=None):
    try:
        user = request.user
        employee = get_object_or_404(Employee, employee_no=employee_no)
        
        # 권한 체크
        if not can_access_employee_data(user, employee):
            raise PermissionDenied('この機能は社長または部長のみ利用可能です。')
        
        today = timezone.now().date()
        if not year:
            year = today.year
        if not month:
            month = today.month
        year = int(year)
        month = int(month)
        
        # 해당 월의 AttendanceMonthly
        try:
            monthly = AttendanceMonthly.objects.get(employee=employee, year=str(year), month=str(month).zfill(2))
        except AttendanceMonthly.DoesNotExist:
            monthly = None
        
        # 해당 월의 AttendanceDaily 리스트
        if monthly:
            daily_list = AttendanceDaily.objects.filter(monthly_attendance=monthly).order_by('date')
        else:
            daily_list = []
        
        # API 공휴일 데이터 가져오기
        try:
            api_holidays = get_holidays_for_months(year, month)
            api_holiday_dates = set()
            for date_str in api_holidays.keys():
                try:
                    holiday_date = date.fromisoformat(date_str)
                    api_holiday_dates.add(holiday_date)
                except ValueError:
                    continue
        except Exception as e:
            print(f"공휴일 데이터 가져오기 오류: {e}")
            api_holiday_dates = set()
        
        # 월별 리스트 데이터 생성 (calendar_partial.html과 동일한 구조)
        month_days_list = []
        days_in_month = calendar.monthrange(year, month)[1]
        
        for day in range(1, days_in_month + 1):
            dt = date(year, month, day)
            
            # 해당 날짜의 기록 찾기
            daily_record = None
            for daily in daily_list:
                if daily.date == dt:
                    daily_record = daily
                    break
            
            # 공휴일, 토요일, 일요일 체크
            is_saturday = (dt.weekday() == 5)
            is_sunday = (dt.weekday() == 6)
            is_api_holiday = dt in api_holiday_dates
            
            # 기본 근무 구분 설정
            if is_api_holiday:
                default_work_type = '祝日'
            elif is_sunday:
                default_work_type = '休日(法)'
            elif is_saturday:
                default_work_type = '休日'
            else:
                default_work_type = '出勤'
            
            month_days_list.append({
                'date': dt,
                'weekday': dt.weekday(),
                'record': daily_record,
                'is_saturday': is_saturday,
                'is_sunday': is_sunday,
                'is_api_holiday': is_api_holiday,
                'default_work_type': default_work_type
            })
        
        # 캘린더 데이터 생성 (calendar_partial.html과 동일한 구조)
        calendar_date = date(year, month, 1)
        weekdays = ['日', '月', '火', '水', '木', '金', '土']
        
        # 월의 첫 번째 날과 마지막 날
        first_day = calendar_date.replace(day=1)
        last_day = (first_day.replace(month=first_day.month % 12 + 1, day=1) - timedelta(days=1)) if first_day.month < 12 else first_day.replace(year=first_day.year + 1, month=1, day=1) - timedelta(days=1)
        
        # 캘린더 그리드 생성
        calendar_weeks = []
        current_week = []
        
        # 이전 달의 마지막 날들
        first_weekday = first_day.weekday()
        if first_weekday == 6:  # 일요일
            first_weekday = 0
        else:
            first_weekday += 1
        
        prev_month_last = first_day - timedelta(days=first_weekday)
        for i in range(first_weekday):
            prev_day = prev_month_last - timedelta(days=first_weekday - i - 1)
            current_week.append({'date': prev_day, 'record': None})
        
        # 현재 달의 날들
        current_date = first_day
        while current_date <= last_day:
            if len(current_week) == 7:
                calendar_weeks.append(current_week)
                current_week = []
            
            # 해당 날짜의 기록 찾기
            daily_record = None
            for daily in daily_list:
                if daily.date == current_date:
                    daily_record = daily
                    break
            
            current_week.append({
                'date': current_date,
                'record': daily_record
            })
            current_date += timedelta(days=1)
        
        # 다음 달의 첫 번째 날들
        while len(current_week) < 7:
            next_day = last_day + timedelta(days=len(current_week) - 6)
            current_week.append({'date': next_day, 'record': None})
        
        if current_week:
            calendar_weeks.append(current_week)
        
        # 잔업시간, 유급휴가(임시: 0)
        overtime_total = sum([(d.end_time.hour - d.start_time.hour) if d.start_time and d.end_time else 0 for d in daily_list])
        paid_leave_used = sum([1 for d in daily_list if d.work_type and '有給' in d.work_type])
        
        # 월별 정보 (monthly가 있을 때만)
        monthly_info = None
        if monthly:
            # structures.py를 사용한 정확한 계산
            # DailyData 객체들 생성
            daily_data_list = []
            for daily in daily_list:
                daily_data = DailyData(
                    date=daily.date,
                    work_type=daily.work_type,
                    start_time=daily.start_time,
                    end_time=daily.end_time,
                    alternative_work_date=daily.alternative_work_date,
                    notes=daily.notes,
                    is_required=daily.is_required,
                    is_confirmed=daily.is_confirmed,
                    break_minutes=monthly.break_minutes,
                    standard_work_hours=monthly.standard_work_hours
                )
                daily_data_list.append(daily_data)
            
            # MonthlyData 객체 생성 및 계산
            monthly_data = MonthlyData(
                employee_id=employee.employee_no,
                year=str(year),
                month=str(month).zfill(2),
                project_name=monthly.project_name,
                base_calendar=monthly.base_calendar,
                break_minutes=monthly.break_minutes,
                standard_work_hours=monthly.standard_work_hours,
                daily_list=daily_data_list
            )
            
            # 모든 일별 근무시간 계산
            monthly_data.calculate_all_daily_hours()
            
            monthly_info = {
                'project_name': monthly.project_name or '未設定',
                'standard_work_hours': monthly.standard_work_hours or 0,
                'break_minutes': monthly.break_minutes or 0,
                'work_days': monthly_data.work_days,
                'paid_leave_days': monthly_data.paid_leave_days,
                'overtime_hours': monthly_data.total_overtime_hours,
                'status': 'approved' if monthly.is_confirmed else 'pending' if monthly.is_required else 'waiting'
            }
        
        # 월 이동용
        prev_month = (date(year, month, 1).replace(day=1) - timedelta(days=1))
        next_month = (date(year, month, monthrange(year, month)[1]) + timedelta(days=1))
        
        context = {
            'employee': employee,
            'year': year,
            'month': month,
            'monthly': monthly,
            'monthly_info': monthly_info,
            'daily_list': daily_list,
            'month_days_list': month_days_list,
            'calendar_weeks': calendar_weeks,
            'weekdays': weekdays,
            'calendar_date': calendar_date,
            'overtime_total': overtime_total,
            'paid_leave_used': paid_leave_used,
            'prev_year': prev_month.year,
            'prev_month': prev_month.month,
            'next_year': next_month.year,
            'next_month': next_month.month,
        }
        
        return render(request, 'admin/attendance/employee_detail.html', context)
        
    except Exception as e:
        print(f"employee_detail_view 오류: {e}")
        import traceback
        traceback.print_exc()
        raise


@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def employee_monthly_data_check_view(request, employee_no):
    """직원의 월별 데이터 존재 여부를 확인하는 API"""
    try:
        employee = get_object_or_404(Employee, employee_no=employee_no)
        year = request.GET.get('year')
        month = request.GET.get('month')
        
        if not year or not month:
            return JsonResponse({'error': 'Year and month parameters required'}, status=400)
        
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return JsonResponse({'error': 'Invalid year or month'}, status=400)
        
        # 해당 월의 AttendanceMonthly 확인
        try:
            monthly = AttendanceMonthly.objects.get(
                employee=employee, 
                year=str(year), 
                month=str(month).zfill(2)
            )
            has_data = True
        except AttendanceMonthly.DoesNotExist:
            has_data = False
        
        return JsonResponse({
            'employee_no': employee_no,
            'year': year,
            'month': month,
            'has_data': has_data
        })
        
    except Exception as e:
        print(f"employee_monthly_data_check_view 오류: {e}")
        return JsonResponse({'error': str(e)}, status=500)

class PaySlipForm(forms.ModelForm):
    class Meta:
        model = PaySlip
        fields = ['payment', 'deduction', 'net_payment', 'notes']
        labels = {
            'payment': '支給額',
            'deduction': '控除額',
            'net_payment': '差引支給額',
            'notes': '備考',
        }

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def payroll_detail_view(request, employee_no, year, month):
    employee = get_object_or_404(Employee, employee_no=employee_no)
    payslip, created = PaySlip.objects.get_or_create(employee=employee, year=year, month=month)
    if request.method == 'POST':
        form = PaySlipForm(request.POST, instance=payslip)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(f'/admin/payroll/?year={year}&month={month}')
    else:
        form = PaySlipForm(instance=payslip)
    context = {
        'employee': employee,
        'year': year,
        'month': month,
        'form': form,
    }
    return render(request, 'admin/attendance/payroll_detail.html', context)

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def payroll_pdf_download_view(request, employee_no, year, month):
    employee = get_object_or_404(Employee, employee_no=employee_no)
    payslip = get_object_or_404(PaySlip, employee=employee, year=year, month=month)
    pdf_buffer = generate_payslip_pdf(employee, payslip, year, month)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"給与明細書_{employee.employee_no}_{year}{month}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def monthly_approval_action(request, monthly_id, action):
    monthly = get_object_or_404(AttendanceMonthly, pk=monthly_id)
    if action == 'request':
        monthly.is_required = True
        monthly.is_confirmed = False
        monthly.save()
        messages.success(request, '承認申請を行いました。')
    elif action == 'approve':
        monthly.is_confirmed = True
        monthly.is_required = False
        monthly.save()
        messages.success(request, '承認が確定されました。')
    elif action == 'cancel':
        monthly.is_required = False
        monthly.is_confirmed = False
        monthly.save()
        messages.info(request, '承認申請をキャンセルしました。')
    elif action == 'revise':
        monthly.is_required = False
        monthly.is_confirmed = False
        monthly.save()
        messages.warning(request, '修正依頼を出しました。')
    else:
        messages.error(request, '不正な操作です。')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))

@login_required
@permission_required(PERMISSIONS['ADMIN_ACCESS'])
def daily_calendar_view(request, year=None, month=None):
    today = timezone.now().date()
    year = int(year) if year else today.year
    month = int(month) if month else today.month
    cal = calendar.Calendar()
    days = list(cal.itermonthdates(year, month))
    # 일별 근무자 정보
    selected_date = request.GET.get('date')
    employees = []
    if selected_date:
        d = selected_date
        daily_qs = AttendanceDaily.objects.filter(date=d)
        employees = [dd.monthly_attendance.employee for dd in daily_qs]
        daily_list = list(daily_qs)
    else:
        daily_list = []
    context = {
        'year': year,
        'month': month,
        'days': days,
        'selected_date': selected_date,
        'employees': employees,
        'daily_list': daily_list,
    }
    return render(request, 'admin/attendance/daily_calendar.html', context)