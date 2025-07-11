from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_permission_codename
from django.urls import path
from .models import Employee, AttendanceMonthly, AttendanceDaily, HolidayCalendar
from .admin_views import profile_view, attendance_overview, payroll_view, employee_detail_view, payroll_detail_view, payroll_pdf_download_view, monthly_approval_action, daily_calendar_view
from django.utils.html import format_html
from django.utils import timezone
from django import forms
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
import csv
from io import TextIOWrapper
from django.shortcuts import render

class CustomAdminSite(admin.AdminSite):
    site_header = '勤怠・給与管理システム管理者'
    site_title = '勤怠・給与管理システム'
    index_title = '管理者ダッシュボード'

    def has_permission(self, request):
        # is_active이고, 'attendance.can_access_admin' 권한이 있을 때만 접근 허용
        return request.user.is_active and request.user.has_perm('attendance.can_access_admin')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('profile/', self.admin_view(profile_view), name='profile'),
            path('attendance-overview/', self.admin_view(attendance_overview), name='attendance_overview'),
            path('payroll/', self.admin_view(payroll_view), name='payroll'),
            path('employee/<str:employee_no>/detail/<int:year>/<int:month>/', self.admin_view(employee_detail_view), name='employee_detail'),
            path('employee/<str:employee_no>/detail/', self.admin_view(employee_detail_view), name='employee_detail_current'),
            path('payroll/<str:employee_no>/<str:year>/<str:month>/', self.admin_view(payroll_detail_view), name='payroll_detail'),
            path('payroll/<str:employee_no>/<str:year>/<str:month>/pdf/', self.admin_view(payroll_pdf_download_view), name='payroll_pdf_download'),
            path('monthly/<int:monthly_id>/<str:action>/', self.admin_view(monthly_approval_action), name='monthly_approval_action'),
            path('daily-calendar/<int:year>/<int:month>/', self.admin_view(daily_calendar_view), name='daily_calendar'),
            path('csv_upload/', self.admin_view(self.csv_upload_view), name='employee_csv_upload'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['custom_links'] = [
            {'url': '/admin/payroll/', 'label': '給与明細書管理'},
            {'url': '/admin/attendance-overview/', 'label': '勤怠管理'},
        ]
        return super().index(request, extra_context=extra_context)

    def csv_upload_view(self, request):
        if request.method == 'POST':
            form = EmployeeCSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data['csv_file']
                decoded_file = TextIOWrapper(csv_file, encoding='utf-8')
                reader = csv.reader(decoded_file, delimiter=',')
                duplicated = []
                created = 0
                for row in reader:
                    if len(row) < 4:
                        continue
                    employee_no = row[0].strip()
                    name = row[1].strip()
                    place_work = row[2].strip()
                    email = row[3].strip()
                    # 사원번호 유효성 체크 (6글자 문자열 허용)
                    if len(employee_no) != 6:
                        duplicated.append(f"{employee_no} (社員番号が6文字ではありません)")
                        continue
                    # 이름 분리
                    if ' ' in name:
                        last_name, first_name = name.split(' ', 1)
                    else:
                        last_name, first_name = name, ''
                    if Employee.objects.filter(employee_no=employee_no).exists():
                        duplicated.append(f"{employee_no} {last_name} {first_name}")
                        continue
                    emp = Employee(
                        employee_no=employee_no,
                        last_name=last_name,
                        first_name=first_name,
                        place_work=place_work,
                        email=email,
                        is_active=True,
                        is_superuser=False,
                    )
                    emp.set_password('0000')
                    emp.save()
                    created += 1
                msg = f"{created}名の従業員を追加しました。"
                if duplicated:
                    msg += f"\n以下の社員番号は既に存在するため追加されませんでした:\n" + '\n'.join(duplicated)
                    messages.warning(request, msg.replace('\n', '<br>'))
                else:
                    messages.success(request, msg)
                return HttpResponseRedirect(reverse('admin:attendance_employee_changelist'))
        else:
            form = EmployeeCSVUploadForm()
        context = dict(
            self.each_context(request),
            form=form,
        )
        return render(request, "admin/attendance/employee_csv_upload.html", context)

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['csv_upload_url'] = reverse('admin:employee_csv_upload')
        return super().changelist_view(request, extra_context=extra_context)

custom_admin_site = CustomAdminSite(name='custom_admin')

# 권한별 사원 필터링 유틸 (추후 admin_utils.py로 분리 가능)
def get_employee_queryset_by_role(request, queryset):
    user = request.user
    # superuser, 사장, 인사팀, 관리부장: 전체
    if user.is_superuser or user.groups.filter(name__in=['사장', '인사팀', '관리부장']).exists():
        return queryset
    # 부장: 본인 팀(근무지)만
    elif user.groups.filter(name='부장').exists():
        return queryset.filter(place_work=user.place_work)
    # 그 외: 본인만
    else:
        return queryset.filter(employee_no=user.employee_no)

@admin.register(Employee, site=custom_admin_site)
class EmployeeAdmin(admin.ModelAdmin):
    """社員管理用のカスタムAdmin"""
    list_display = (
        'employee_no', 'last_name', 'first_name', 'place_work', 'email', 'is_active', 'retire_action_button', 'detail_button',
    )
    list_filter = ('is_active', 'place_work', 'groups')
    search_fields = ('employee_no', 'last_name', 'first_name', 'place_work', 'email')
    ordering = ('employee_no',)
    
    # フィールドセットのカスタマイズ
    fieldsets = (
        ('社員情報', {'fields': ('employee_no', 'password')}),
        ('個人情報', {'fields': ('first_name', 'last_name', 'email')}),
        ('勤務情報', {'fields': ('place_work',)}),
        ('権限', {'fields': ('is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日付', {'fields': ('last_login',)}),
    )
    
    add_fieldsets = (
        ('社員情報', {
            'classes': ('wide',),
            'fields': ('employee_no', 'place_work', 'email', 'password1', 'password2'),
        }),
    )
    
    actions = ['retire_selected']

    change_list_template = "admin/attendance/employee_changelist.html"

    def get_queryset(self, request):
        """社員番号でソート"""
        qs = super().get_queryset(request).order_by('employee_no')
        return get_employee_queryset_by_role(request, qs)
    
    def retire_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated}명 퇴사 처리 완료.")
    retire_selected.short_description = "선택 사원 퇴사 처리"

    def retire_action_button(self, obj):
        if obj.is_active:
            return format_html('<a class="button" href="/admin/employee/{}/retire/">퇴사처리</a>', obj.employee_no)
        else:
            return '퇴사자'
    retire_action_button.short_description = '퇴사처리'
    retire_action_button.allow_tags = True

    def formfield_for_dbfield(self, db_field, **kwargs):
        """employee_no 필드에 도움말 추가"""
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'employee_no':
            formfield.help_text = '6桁の社員番号を入力してください (例: 123456)'
        return formfield

    def detail_button(self, obj):
        today = timezone.now().date()
        return format_html('<a class="button" href="/admin/employee/{}/detail/{}/{}/">勤怠詳細</a>', obj.employee_no, today.year, str(today.month).zfill(2))
    detail_button.short_description = '勤怠詳細'

    def get_readonly_fields(self, request, obj=None):
        # superuser는 모든 필드 수정 가능, 그 외는 employee_no만 readonly
        if request.user.is_superuser:
            return []
        return ['employee_no']

    def get_fieldsets(self, request, obj=None):
        # superuser는 모든 필드 표시, 그 외는 제한
        if request.user.is_superuser:
            return self.fieldsets
        # 일반 사용자는 최소 필드만 표시
        return (
            ('社員情報', {'fields': ('employee_no', 'password')}),
            ('個人情報', {'fields': ('first_name', 'last_name', 'email')}),
            ('勤務情報', {'fields': ('place_work',)}),
        )

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['csv_upload_url'] = reverse('admin:employee_csv_upload')
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(AttendanceMonthly, site=custom_admin_site)
class AttendanceMonthlyAdmin(admin.ModelAdmin):
    """月別勤怠管理用のAdmin"""
    list_display = ('monthly_id', 'employee', 'year', 'month', 'project_name', 'base_calendar')
    list_filter = ('year', 'month', 'base_calendar', 'employee__place_work')
    search_fields = ('employee__employee_no', 'project_name')
    ordering = ('-year', '-month', 'employee__employee_no')
    
    def employee(self, obj):
        return f"{obj.employee.employee_no:06d} - {obj.employee.last_name}{obj.employee.first_name}"
    employee.short_description = '社員'

@admin.register(AttendanceDaily, site=custom_admin_site)
class AttendanceDailyAdmin(admin.ModelAdmin):
    """日別勤怠管理用のAdmin"""
    list_display = ('daily_id', 'employee', 'date', 'work_type', 'start_time', 'end_time', 'is_confirmed')
    list_filter = ('work_type', 'is_confirmed', 'date', 'monthly_attendance__employee__place_work')
    search_fields = ('monthly_attendance__employee__employee_no',)
    ordering = ('-date', 'monthly_attendance__employee__employee_no')
    
    def employee(self, obj):
        return f"{obj.monthly_attendance.employee.employee_no:06d} - {obj.monthly_attendance.employee.last_name}{obj.monthly_attendance.employee.first_name}"
    employee.short_description = '社員'

    def get_fieldsets(self, request, obj=None):
        return (
            ('日別勤怠', {'fields': ('monthly_attendance', 'date', 'work_type', 'start_time', 'end_time', 'notes', 'is_confirmed', 'is_required')}),
        )

    def get_readonly_fields(self, request, obj=None):
        return []

@admin.register(HolidayCalendar)
class HolidayCalendarAdmin(admin.ModelAdmin):
    list_display = ('calendar_name', 'date', 'category')
    list_filter = ('calendar_name', 'category')
    search_fields = ('calendar_name', 'category')
    ordering = ('calendar_name', 'date')

class EmployeeCSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='CSVファイルを選択')
