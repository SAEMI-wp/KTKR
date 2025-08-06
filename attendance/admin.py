from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Group
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
from io import StringIO, TextIOWrapper, BytesIO
from django.shortcuts import render
from .utils import get_group_name_by_code
import chardet

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
            path('position-management/', self.admin_view(self.position_management_view), name='position_management'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        # 従業員一覧へリダイレクト
        return HttpResponseRedirect(reverse('admin:attendance_employee_changelist'))

    def csv_upload_view(self, request):
        try:
            print(f"[DEBUG] CSV 업로드 시작 - 사용자: {request.user}")
            
            if request.method == 'POST':
                form = EmployeeCSVUploadForm(request.POST, request.FILES)
                if form.is_valid():
                    csv_file = form.cleaned_data['csv_file']
                    print(f"[DEBUG] CSV 파일명: {csv_file.name}")
                    
                    # 파일 내용을 바이트로 읽기
                    csv_file.seek(0)
                    file_content = csv_file.read()
                    
                    # 인코딩 자동 감지
                    detected_encoding = chardet.detect(file_content)
                    encoding = detected_encoding['encoding']
                    confidence = detected_encoding['confidence']
                    
                    print(f"[DEBUG] 감지된 인코딩: {encoding} (신뢰도: {confidence:.2f})")
                    
                    # 일반적인 일본어 인코딩들 시도
                    encodings_to_try = ['utf-8', 'shift_jis', 'cp932', 'euc-jp', 'iso-2022-jp']
                    
                    if encoding and confidence > 0.7:
                        encodings_to_try.insert(0, encoding)
                    
                    decoded_content = None
                    used_encoding = None
                    
                    for enc in encodings_to_try:
                        try:
                            decoded_content = file_content.decode(enc)
                            used_encoding = enc
                            print(f"[DEBUG] 성공적으로 디코딩됨: {enc}")
                            break
                        except UnicodeDecodeError as e:
                            print(f"[DEBUG] {enc} 디코딩 실패: {e}")
                            continue
                    
                    if decoded_content is None:
                        raise Exception(f"CSV 파일의 인코딩을 감지할 수 없습니다. 지원되는 인코딩: {', '.join(encodings_to_try)}")
                    
                    # StringIO로 변환하여 CSV 리더 사용
                    csv_string = StringIO(decoded_content)
                    reader = csv.reader(csv_string, delimiter=',')
                    duplicated = []
                    created = 0
                    
                    for row_num, row in enumerate(reader, 1):
                        try:
                            if len(row) < 4:
                                print(f"[DEBUG] 행 {row_num}: 컬럼 수 부족 ({len(row)})")
                                continue
                                
                            employee_no = row[0].strip()
                            name = row[1].strip()
                            place_work = row[2].strip()
                            email = row[3].strip()
                            
                            print(f"[DEBUG] 행 {row_num}: {employee_no}, {name}, {place_work}, {email}")
                            
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
                            print(f"[DEBUG] 직원 생성 완료: {employee_no}")
                            created += 1
                            
                        except Exception as e:
                            print(f"[ERROR] 행 {row_num} 처리 중 오류: {e}")
                            duplicated.append(f"행 {row_num}: {str(e)}")
                            continue
                            
                    msg = f"{created}名の従業員を追加しました。"
                    if used_encoding:
                        msg += f" (使用エンコード: {used_encoding})"
                    if duplicated:
                        msg += f"\n以下の社員番号は既に存在するため追加されませんでした:\n" + '\n'.join(duplicated)
                        messages.warning(request, msg.replace('\n', '<br>'))
                    else:
                        messages.success(request, msg)
                    return HttpResponseRedirect(reverse('admin:attendance_employee_changelist'))
                else:
                    print(f"[DEBUG] 폼 유효성 검사 실패: {form.errors}")
                    messages.error(request, f'CSV 파일 업로드 오류: {form.errors}')
            else:
                form = EmployeeCSVUploadForm()
                
            context = dict(
                self.each_context(request),
                form=form,
            )
            return render(request, "admin/attendance/employee_csv_upload.html", context)
            
        except Exception as e:
            print(f"[ERROR] CSV 업로드 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            
            # 인코딩 관련 오류인지 확인
            if 'codec' in str(e).lower() or 'decode' in str(e).lower():
                error_msg = f'CSV 파일의 인코딩을 감지할 수 없습니다. 파일이 UTF-8, Shift_JIS, CP932 중 하나로 저장되어 있는지 확인해주세요. (오류: {str(e)})'
            else:
                error_msg = f'CSV 업로드 중 오류가 발생했습니다: {str(e)}'
            
            messages.error(request, error_msg)
            return HttpResponseRedirect(reverse('admin:attendance_employee_changelist'))

    def position_management_view(self, request):
        """직급 관리 페이지 (superuser만 접근 가능)"""
        if not request.user.is_superuser:
            messages.error(request, 'この機能はスーパーユーザーのみ利用可能です。')
            return HttpResponseRedirect(reverse('admin:index'))
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'add':
                # 새 직급 추가
                position_code = request.POST.get('position_code', '').strip()
                position_name = request.POST.get('position_name', '').strip()
                
                if position_code and position_name:
                    # 코드 중복 체크
                    if Group.objects.filter(name=position_name).exists():
                        messages.warning(request, f'職級名 "{position_name}" は既に存在します。')
                    else:
                        group = Group.objects.create(name=position_name)
                        messages.success(request, f'職級 "{position_name}" (コード: {position_code}) を追加しました。')
                else:
                    messages.error(request, '職級コードと職級名を入力してください。')
            
            elif action == 'delete':
                # 직급 삭제
                group_id = request.POST.get('group_id')
                try:
                    group = Group.objects.get(id=group_id)
                    # 해당 그룹에 속한 직원 수 확인
                    employee_count = group.user_set.count()
                    if employee_count > 0:
                        messages.warning(request, f'職級 "{group.name}" には {employee_count}名の従業員が所属しているため削除できません。')
                    else:
                        group_name = group.name
                        group.delete()
                        messages.success(request, f'職級 "{group_name}" を削除しました。')
                except Group.DoesNotExist:
                    messages.error(request, '指定された職級が見つかりません。')
            
            elif action == 'edit':
                # 직급명 수정
                group_id = request.POST.get('group_id')
                new_name = request.POST.get('new_name', '').strip()
                try:
                    group = Group.objects.get(id=group_id)
                    if new_name:
                        if Group.objects.filter(name=new_name).exclude(id=group_id).exists():
                            messages.warning(request, f'職級名 "{new_name}" は既に存在します。')
                        else:
                            old_name = group.name
                            group.name = new_name
                            group.save()
                            messages.success(request, f'職級名を "{old_name}" から "{new_name}" に変更しました。')
                    else:
                        messages.error(request, '新しい職級名を入力してください。')
                except Group.DoesNotExist:
                    messages.error(request, '指定された職級が見つかりません。')
            
            elif action == 'add_defaults':
                # 기본 직급 일괄 등록
                default_positions = {
                    '1': '社長',
                    '2': '役員', 
                    '100': '部長',
                    '101': '担当部長',
                    '102': '主幹技師',
                    '104': '技師',
                    '105': '企画員',
                    '106': '社員',
                }
                
                added_count = 0
                skipped_positions = []
                
                for code, name in default_positions.items():
                    if not Group.objects.filter(name=name).exists():
                        Group.objects.create(name=name)
                        added_count += 1
                    else:
                        skipped_positions.append(name)
                
                if added_count > 0:
                    messages.success(request, f'{added_count}個の基本職級を追加しました。')
                if skipped_positions:
                    messages.info(request, f'既に存在する職級: {", ".join(skipped_positions)}')
        
        # 현재 등록된 직급 목록 (직급명으로 정렬)
        groups = Group.objects.all().order_by('name')
        group_info = []
        
        # 기본 직급 코드 매핑
        default_position_mapping = {
            '社長': '1',
            '役員': '2', 
            '部長': '100',
            '担当部長': '101',
            '主幹技師': '102',
            '技師': '104',
            '企画員': '105',
            '社員': '106',
        }
        
        for group in groups:
            employee_count = group.user_set.count()
            position_code = default_position_mapping.get(group.name, '未設定')
            group_info.append({
                'group': group,
                'employee_count': employee_count,
                'position_code': position_code
            })
        
        context = dict(
            self.each_context(request),
            group_info=group_info,
            default_positions=default_position_mapping,
        )
        return render(request, "admin/attendance/position_management.html", context)

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['csv_upload_url'] = reverse('admin:employee_csv_upload')
        return super().changelist_view(request, extra_context=extra_context)

custom_admin_site = CustomAdminSite(name='custom_admin')

# 권한별 사원 필터링 유틸 (새로운 직급 체계 적용)
def get_employee_queryset_by_role(request, queryset):
    user = request.user
    if user.is_superuser:
        return queryset
    
    # Django 기본 groups 사용
    user_groups = [g.name for g in user.groups.all()]
    print(f"[DEBUG] user.groups: {user_groups}")
    
    if '社長' in user_groups:
        return queryset
    elif '部長' in user_groups:
        user_place = (user.place_work or '').strip()
        # 모든 직원의 place_work를 split해서 포함 여부로 필터링
        filtered = queryset.filter(place_work__icontains=user_place)
        print(f"[DEBUG] 部長 필터 결과: {filtered.count()}명, {[e.employee_no for e in filtered]}")
        return filtered
    return queryset.filter(employee_no=user.employee_no)

@admin.register(Employee, site=custom_admin_site)
class EmployeeAdmin(admin.ModelAdmin):
    """社員管理用のカスタムAdmin"""
    list_display = (
        'employee_no', 'last_name', 'first_name', 'place_work', 'position_groups', 'email', 'detail_button',
    )
    list_filter = ('place_work', 'is_active', 'groups')
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
    
    actions = ['retire_selected', 'delete_selected', 'restore_selected']

    change_list_template = "admin/attendance/employee_changelist.html"

    def get_queryset(self, request):
        """社員番号でソート"""
        qs = super().get_queryset(request).order_by('employee_no')
        return get_employee_queryset_by_role(request, qs)
    
    def retire_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated}名退社処理完了.")
    retire_selected.short_description = "退社処理"

    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count}名の従業員を削除しました.")
    delete_selected.short_description = "削除"

    def restore_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated}名の従業員を復元しました.")
    restore_selected.short_description = "復元"

    def retire_action_button(self, obj):
        if obj.is_active:
            return format_html('<a class="button" href="/admin/employee/{}/retire/">퇴사처리</a>', obj.employee_no)
        else:
            return '退社者'
    retire_action_button.short_description = '退社処理'
    retire_action_button.allow_tags = True

    def formfield_for_dbfield(self, db_field, **kwargs):
        """employee_no 필드에 도움말 추가"""
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'employee_no':
            formfield.help_text = '6桁の社員番号を入力してください (例: 123456)'
        return formfield

    def detail_button(self, obj):
        """권한에 따라 勤怠詳細 버튼 표시"""
        request = self.request  # 현재 요청 객체 가져오기
        user = request.user
        can_access = False
        # superuser 또는 사장님(社長)은 무조건 허용
        if user.is_superuser or '社長' in user.groups.values_list('name', flat=True):
            can_access = True
        else:
            user_groups = user.groups.values_list('name', flat=True)
            # 部長: 같은 work_place 직원만 접근 가능  
            if '部長' in user_groups:
                if obj.place_work == user.place_work:
                    can_access = True
        if can_access:
            today = timezone.now().date()
            return format_html('<a class="button" href="/admin/employee/{}/detail/{}/{}/">勤怠詳細</a>', obj.employee_no, today.year, str(today.month).zfill(2))
        else:
            return format_html('<span style="color: #999;">権限なし</span>')
    
    detail_button.short_description = '勤怠詳細'

    def position_groups(self, obj):
        """직원이 속한 직급 그룹 표시"""
        groups = obj.groups.all()
        if groups:
            group_names = [group.name for group in groups]
            return ', '.join(group_names)
        return '未設定'
    position_groups.short_description = '職級'

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
        # request 객체를 인스턴스에 저장하여 다른 메서드에서 사용 가능하게 함
        self.request = request
        if extra_context is None:
            extra_context = {}
        extra_context['csv_upload_url'] = reverse('admin:employee_csv_upload')
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        # 追加ボタンを非表示
        return False

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

    def has_module_permission(self, request):
        # サイドバーから非表示
        return False

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

    def has_module_permission(self, request):
        # サイドバーから非表示
        return False

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
