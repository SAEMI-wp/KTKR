from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Employee, AttendanceMonthly, AttendanceDaily, PaidLeave, PaySlip
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from calendar import monthrange
from datetime import date
from django import forms
from django.http import HttpResponseRedirect, HttpResponse
from django.template.loader import render_to_string
from .pdf_generator import generate_payslip_pdf
from django.contrib import messages
import calendar

def admin_permission_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_active and user.has_perm('attendance.can_access_admin')):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@admin_permission_required
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
@admin_permission_required
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
@admin_permission_required
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

def employee_detail_view(request, employee_no, year=None, month=None):
    user = request.user
    employee = get_object_or_404(Employee, employee_no=employee_no)
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
    # 잔업시간, 유급휴가(임시: 0)
    overtime_total = sum([(d.end_time.hour - d.start_time.hour) if d.start_time and d.end_time else 0 for d in daily_list])
    paid_leave_used = sum([1 for d in daily_list if d.work_type and '有給' in d.work_type])
    # 월 이동용
    prev_month = (date(year, month, 1).replace(day=1) - timezone.timedelta(days=1))
    next_month = (date(year, month, monthrange(year, month)[1]) + timezone.timedelta(days=1))
    context = {
        'employee': employee,
        'year': year,
        'month': month,
        'daily_list': daily_list,
        'overtime_total': overtime_total,
        'paid_leave_used': paid_leave_used,
        'prev_year': prev_month.year,
        'prev_month': prev_month.month,
        'next_year': next_month.year,
        'next_month': next_month.month,
    }
    return render(request, 'admin/attendance/employee_detail.html', context)

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

@admin_permission_required
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

@admin_permission_required
def payroll_pdf_download_view(request, employee_no, year, month):
    employee = get_object_or_404(Employee, employee_no=employee_no)
    payslip = get_object_or_404(PaySlip, employee=employee, year=year, month=month)
    pdf_buffer = generate_payslip_pdf(employee, payslip, year, month)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"給与明細書_{employee.employee_no}_{year}{month}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@admin_permission_required
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

@admin_permission_required
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

# WeasyPrint 관련 import 및 payroll_pdf_view 함수 삭제
# 이후 pdf_generator.py의 generate_payslip_pdf 함수 등을 활용할 예정 