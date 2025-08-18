from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Group
from django.urls import path
from .models import Employee, AttendanceMonthly, AttendanceDaily, HolidayCalendar, Calendar
from .admin_views import profile_view, attendance_overview, payroll_view, employee_detail_view, payroll_detail_view, payroll_pdf_download_view, monthly_approval_action, daily_calendar_view, employee_monthly_data_check_view
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

# パスワード変更のためのカスタムフォーム
class EmployeeChangeForm(forms.ModelForm):
    """従業員情報変更のためのカスタムフォーム"""
    password = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput,
        required=False,
        help_text='パスワードを変更する場合は新しいパスワードを入力してください。変更しない場合は空欄のままにしてください。'
    )
    
    class Meta:
        model = Employee
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # 既存のユーザーの場合はパスワードフィールドを空欄にする
            self.fields['password'].help_text = 'パスワードを変更する場合は新しいパスワードを入力してください。変更しない場合は空欄のままにしてください。'
            # 既存のパスワードフィールドの初期値を削除
            self.fields['password'].initial = ''
    
    def save(self, commit=True):
        employee = super().save(commit=False)
        
        # パスワードが入力された場合にのみ暗号化して保存
        if self.cleaned_data.get('password'):
            employee.set_password(self.cleaned_data['password'])
            # パスワード変更のログを追加
            print(f"[DEBUG] パスワード変更: {employee.employee_no}")
        else:
            # パスワードが入力されない場合は既存のパスワードを維持
            print(f"[DEBUG] パスワード変更なし: {employee.employee_no}")
        
        if commit:
            employee.save()
        return employee

class CustomAdminSite(admin.AdminSite):
    site_header = '勤怠・給与管理システム管理者'
    site_title = '勤怠・給与管理システム'
    index_title = '管理者ダッシュボード'

    def has_permission(self, request):
        # is_active이고, 'attendance.can_access_admin' 권한이 있을 때만 접근 허용
        return request.user.is_active and request.user.has_perm('attendance.can_access_admin')

    def get_app_list(self, request):
        """
        커스텀 사이드바 메뉴 구성
        """
        app_list = super().get_app_list(request)
        
        # 기존 "認証と認可" 섹션을 "管理メニュー"로 변경
        for app in app_list:
            if app['app_label'] == 'auth':
                app['name'] = '管理メニュー'
                app['has_module_perms'] = False  # 클릭 불가능하게 설정
                # app_url을 완전히 제거하여 링크 자체를 없앰
                if 'app_url' in app:
                    del app['app_url']
                
                # 그룹 모델은 "職級管理"로 변경하되 클릭 가능하게 유지
                for model in app['models']:
                    if model['object_name'] == 'group':
                        model['name'] = '職級管理'
                        model['verbose_name'] = '職級管理'
                        model['verbose_name_plural'] = '職級管理'
                        # admin_url은 유지하여 클릭 가능하게 함
                        # model['admin_url'] = '/admin/auth/group/'  # 기본 URL 유지
                        model['add_url'] = None  # 추가 버튼만 비활성화
                        model['view_only'] = False  # 읽기 전용 해제
                        # 모델 메타데이터도 변경
                        model['object_name'] = 'group'  # 원래 object_name 유지
                        model['perms'] = {'add': False, 'change': True, 'delete': False, 'view': True}
            
            # Attendance 앱 섹션만 클릭 불가능하게 설정 (모델은 그대로 유지)
            elif app['app_label'] == 'attendance':
                app['has_module_perms'] = False  # 앱 섹션만 클릭 불가능
                # app_url을 완전히 제거하여 앱 링크 자체를 없앰
                if 'app_url' in app:
                    del app['app_url']
                
                # Calendar와 HolidayCalendar 모델은 숨기기 (통합 관리에서 처리)
                app['models'] = [
                    model for model in app['models'] 
                    if model['object_name'] not in ['calendar', 'holidaycalendar']
                ]
        
        # 現場・カレンダ管理 메뉴 추가
        calendar_management_app = {
            'name': '現場・カレンダ管理',
            'app_label': 'calendar_management',
            'app_url': '/admin/calendar-management/',
            'has_module_perms': True,
            'models': [
                {
                    'name': '現場・カレンダー統合管理',
                    'object_name': 'calendar_management',
                    'admin_url': '/admin/calendar-management/',
                    'add_url': None,
                    'view_only': False,
                    'perms': {'add': False, 'change': True, 'delete': False, 'view': True}
                }
            ]
        }
        app_list.append(calendar_management_app)
        
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('profile/', self.admin_view(profile_view), name='profile'),
            path('attendance-overview/', self.admin_view(attendance_overview), name='attendance_overview'),
            path('payroll/', self.admin_view(payroll_view), name='payroll'),
            path('employee/<str:employee_no>/detail/<int:year>/<int:month>/', self.admin_view(employee_detail_view), name='employee_detail'),
            path('employee/<str:employee_no>/detail/', self.admin_view(employee_detail_view), name='employee_detail_current'),
            path('employee/<str:employee_no>/monthly-check/', self.admin_view(employee_monthly_data_check_view), name='employee_monthly_check'),
            path('payroll/<str:employee_no>/<str:year>/<str:month>/', self.admin_view(payroll_detail_view), name='payroll_detail'),
            path('payroll/<str:employee_no>/<str:year>/<str:month>/pdf/', self.admin_view(payroll_pdf_download_view), name='payroll_pdf_download'),
            path('monthly/<int:monthly_id>/<str:action>/', self.admin_view(monthly_approval_action), name='monthly_approval_action'),
            path('daily-calendar/<int:year>/<int:month>/', self.admin_view(daily_calendar_view), name='daily_calendar'),
            path('csv_upload/', self.admin_view(self.csv_upload_view), name='employee_csv_upload'),
            path('position-management/', self.admin_view(self.position_management_view), name='position_management'),
            path('calendar-management/', self.admin_view(self.calendar_management_view), name='calendar_management'),
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
                            # 첫 번째 행은 헤더이므로 건너뛰기
                            if row_num == 1:
                                print(f"[DEBUG] 헤더 행 건너뛰기: {row}")
                                continue
                                
                            if len(row) < 5:
                                print(f"[DEBUG] 행 {row_num}: 컬럼 수 부족 ({len(row)}) - 최소 5개 필요")
                                continue
                                
                            employee_no = row[0].strip()
                            name = row[1].strip()
                            place_work = row[2].strip()
                            email = row[3].strip()
                            position_code = row[4].strip() if len(row) > 4 else ''
                            
                            print(f"[DEBUG] 행 {row_num}: {employee_no}, {name}, {place_work}, {email}, {position_code}")
                            
                            # 사원번호 유효성 체크 (6글자 문자열 허용)
                            if len(employee_no) != 6:
                                duplicated.append(f"{employee_no} (社員番号が6文字ではありません)")
                                continue
                        
                            # 이름 분리
                            if ' ' in name:
                                last_name, first_name = name.split(' ', 1)                        
                            else:
                                last_name, first_name = name, ''
                                
                            # 기존 직원이 있는지 확인
                            existing_employee = Employee.objects.filter(employee_no=employee_no).first()
                            
                            # 직위코드에 따른 그룹 설정
                            position_group = None
                            if position_code:
                                # 직급 코드를 특정 ID로 매핑
                                try:
                                    position_id = int(position_code)
                                    # 특정 ID 매핑
                                    position_mapping = {
                                        1: '社長',
                                        2: '役員', 
                                        100: '部長',
                                        101: '担当部長',
                                        102: '主幹技師',
                                        104: '技師',
                                        105: '企画員',
                                        106: '社員',
                                    }
                                    
                                    if position_id in position_mapping:
                                        group_name = position_mapping[position_id]
                                        # 먼저 ID로 그룹이 있는지 확인
                                        try:
                                            position_group = Group.objects.get(id=position_id)
                                            print(f"[DEBUG] 기존 그룹 발견: ID {position_id} ({position_group.name})")
                                        except Group.DoesNotExist:
                                            # ID가 없으면 raw SQL로 생성
                                                                                     # AUTO_INCREMENT가 제거되었으므로 직접 ID 설정 가능
                                         position_group = Group(id=position_id, name=group_name)
                                         position_group.save()
                                         print(f"[DEBUG] 직위코드 {position_code} -> 그룹 ID {position_id} ({position_group.name}) 생성됨")
                                    else:
                                        # ID가 없으면 이름으로 매핑 시도
                                        group_name = position_mapping.get(position_code)
                                        if group_name:
                                            position_group, created_group = Group.objects.get_or_create(name=group_name)
                                            print(f"[DEBUG] 직위코드 {position_code} -> 그룹명 {group_name} (ID: {position_group.id})")
                                        else:
                                            print(f"[WARNING] 직위코드 {position_code}에 해당하는 그룹을 찾을 수 없습니다.")
                                except ValueError:
                                    # 숫자가 아닌 경우 이름으로 매핑
                                    position_mapping = {
                                        '1': '社長',
                                        '2': '役員', 
                                        '100': '部長',
                                        '101': '担当部長',
                                        '102': '主幹技師',
                                        '104': '技師',
                                        '105': '企画員',
                                        '106': '社員',
                                    }
                                    group_name = position_mapping.get(position_code)
                                    if group_name:
                                        position_group, created_group = Group.objects.get_or_create(name=group_name)
                                        print(f"[DEBUG] 직위코드 {position_code} -> 그룹명 {group_name} (ID: {position_group.id})")
                                    else:
                                        print(f"[WARNING] 직위코드 {position_code}에 해당하는 그룹을 찾을 수 없습니다.")
                            
                            if existing_employee:
                                # 기존 직원 정보 업데이트 (변경된 필드만)
                                updated_fields = []
                                
                                if existing_employee.last_name != last_name:
                                    existing_employee.last_name = last_name
                                    updated_fields.append('姓')
                                
                                if existing_employee.first_name != first_name:
                                    existing_employee.first_name = first_name
                                    updated_fields.append('名')
                                
                                if existing_employee.place_work != place_work:
                                    existing_employee.place_work = place_work
                                    updated_fields.append('勤務先')
                                
                                if existing_employee.email != email:
                                    existing_employee.email = email
                                    updated_fields.append('メール')
                                
                                if not existing_employee.is_active:
                                    existing_employee.is_active = True
                                    updated_fields.append('ステータス')
                                
                                # 직위 그룹 업데이트 (변경된 경우만)
                                current_groups = set(existing_employee.groups.values_list('name', flat=True))
                                if position_group:
                                    target_group_name = position_group.name
                                    if target_group_name not in current_groups:
                                        # 기존 그룹 제거 후 새로운 그룹 설정
                                        existing_employee.groups.clear()
                                        existing_employee.groups.add(position_group)
                                        updated_fields.append('職級')
                                        print(f"[DEBUG] 직급 변경: {list(current_groups)} -> {target_group_name}")
                                else:
                                    # 직위코드가 없는데 현재 그룹이 있는 경우 제거
                                    if current_groups:
                                        existing_employee.groups.clear()
                                        updated_fields.append('職級削除')
                                        print(f"[DEBUG] 직급 제거: {list(current_groups)} -> なし")
                                
                                # 변경사항이 있는 경우에만 저장
                                if updated_fields:
                                    existing_employee.save()
                                    print(f"[DEBUG] 직원 정보 업데이트 완료: {employee_no} - 변경필드: {', '.join(updated_fields)}")
                                    duplicated.append(f"{employee_no} {last_name} {first_name} (更新: {', '.join(updated_fields)})")
                                else:
                                    print(f"[DEBUG] 직원 정보 변경 없음: {employee_no}")
                                    duplicated.append(f"{employee_no} {last_name} {first_name} (変更なし)")
                            else:
                                # 새 직원 생성
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
                                
                                # 직위 그룹 설정
                                if position_group:
                                    emp.groups.add(position_group)
                                
                                print(f"[DEBUG] 직원 생성 완료: {employee_no}")
                                created += 1
                            
                        except Exception as e:
                            print(f"[ERROR] 행 {row_num} 처리 중 오류: {e}")
                            duplicated.append(f"행 {row_num}: {str(e)}")
                            continue
                            
                    # 업데이트된 직원 수 계산 (변경된 경우만)
                    updated_count = len([d for d in duplicated if '(更新:' in d])
                    no_change_count = len([d for d in duplicated if '(変更なし)' in d])
                    duplicated_without_update = [d for d in duplicated if '(更新:' not in d and '(変更なし)' not in d]
                    
                    msg = f"{created}名の従業員を追加しました。"
                    if updated_count > 0:
                        msg += f" {updated_count}名の従業員情報を更新しました。"
                    if no_change_count > 0:
                        msg += f" {no_change_count}名の従業員は変更なしでした。"
                    if used_encoding:
                        msg += f" (使用エンコード: {used_encoding})"
                    
                    if duplicated_without_update:
                        msg += f"\n以下の社員番号は処理できませんでした:\n" + '\n'.join(duplicated_without_update)
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
                    try:
                        position_id = int(position_code)
                        
                        # ID 중복 체크
                        if Group.objects.filter(id=position_id).exists():
                            messages.warning(request, f'職級コード "{position_code}" (ID: {position_id}) 天下之既に存在します。')
                        # 이름 중복 체크
                        elif Group.objects.filter(name=position_name).exists():
                            messages.warning(request, f'職級名 "{position_name}" 天下之既に存在します。')
                        else:
                            # AUTO_INCREMENT가 제거되었으므로 직접 ID 설정 가능
                            group = Group(id=position_id, name=position_name)
                            group.save()
                            messages.success(request, f'職級 "{position_name}" (コード: {position_code}, ID: {position_id}) 天下之追加しました。')
                            print(f"[DEBUG] 직급 생성: ID {position_id} -> {position_name}")
                    except ValueError:
                        messages.error(request, '職級コードは数字でなければなりません。')
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
                # 기본 직급 일괄 등록 (AUTO_INCREMENT 제거 후 간단한 방식)
                default_positions = {
                    1: '社長',
                    2: '役員', 
                    100: '部長',
                    101: '担当部長',
                    102: '主幹技師',
                    104: '技師',
                    105: '企画員',
                    106: '社員',
                }
                
                # 기존 그룹들을 모두 삭제 (직원이 없는 경우만)
                existing_groups = Group.objects.all()
                deleted_count = 0
                for group in existing_groups:
                    if group.user_set.count() == 0:  # 직원이 없는 그룹만 삭제
                        group.delete()
                        deleted_count += 1
                        print(f"[DEBUG] 기존 그룹 삭제: ID {group.id} -> {group.name}")
                
                if deleted_count > 0:
                    print(f"[DEBUG] {deleted_count}개 기존 그룹 삭제됨")
                
                # 특정 ID로 그룹 생성 (AUTO_INCREMENT 제거 후 간단한 방식)
                added_count = 0
                for position_id, name in default_positions.items():
                    try:
                        # AUTO_INCREMENT가 제거되었으므로 직접 ID 설정 가능
                        group = Group(id=position_id, name=name)
                        group.save()
                        added_count += 1
                        print(f"[DEBUG] 직급 생성: ID {position_id} -> {name}")
                    except Exception as e:
                        print(f"[ERROR] 직급 생성 실패: ID {position_id} -> {name}, 오류: {e}")
                
                if added_count > 0:
                    messages.success(request, f'{added_count}個の基本職級を追加しました。')
                    if deleted_count > 0:
                        messages.info(request, f'{deleted_count}個の既存職級を削除しました。')
        
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
            # 특정 ID 매핑 표시
            position_mapping = {
                1: '1',
                2: '2', 
                100: '100',
                101: '101',
                102: '102',
                104: '104',
                105: '105',
                106: '106',
            }
            position_code = position_mapping.get(group.id, str(group.id))
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

    def calendar_management_view(self, request):
        """現場・カレンダー統合管理ページ"""
        if request.method == 'POST':
            form = CalendarManagementForm(request.POST)
            if form.is_valid():
                # Calendar 생성/수정 처리
                calendar_name = form.cleaned_data['calendar_name']
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']
                work_hours = form.cleaned_data['work_hours']
                lunch_time = form.cleaned_data['lunch_time']
                etc = form.cleaned_data['etc']
                
                # Calendar 생성/수정 처리
                if calendar_name and start_time and end_time and work_hours is not None and lunch_time is not None:
                    # Calendar ID가 전달되었는지 확인 (수정 모드)
                    calendar_id = request.POST.get('edit_calendar_id')
                    
                    if calendar_id:
                        # 기존 Calendar 수정
                        try:
                            existing_calendar = Calendar.objects.get(id=calendar_id)
                            existing_calendar.calendar_name = calendar_name
                            existing_calendar.start_time = start_time
                            existing_calendar.end_time = end_time
                            existing_calendar.work_hours = work_hours
                            existing_calendar.lunch_time = lunch_time
                            existing_calendar.etc = etc or ''
                            existing_calendar.save()
                            messages.success(request, f'カレンダー「{calendar_name}」を更新しました。')
                        except Calendar.DoesNotExist:
                            messages.error(request, '指定されたカレンダーが見つかりません。')
                            return HttpResponseRedirect(reverse('admin:calendar_management'))
                    else:
                        # 새로운 Calendar 생성
                        # 이름 중복 체크
                        if Calendar.objects.filter(calendar_name=calendar_name).exists():
                            messages.error(request, f'カレンダー名「{calendar_name}」は既に存在します。')
                            return HttpResponseRedirect(reverse('admin:calendar_management'))
                        
                        calendar = Calendar(
                            calendar_name=calendar_name,
                            start_time=start_time,
                            end_time=end_time,
                            work_hours=work_hours,
                            lunch_time=lunch_time,
                            etc=etc or ''
                        )
                        calendar.save()
                        messages.success(request, f'カレンダー「{calendar_name}」を作成しました。')
                    
                    return HttpResponseRedirect(reverse('admin:calendar_management'))
                
                # Calendar 삭제 처리
                delete_calendar_id = request.POST.get('delete_calendar_id')
                if delete_calendar_id:
                    try:
                        calendar_to_delete = Calendar.objects.get(id=delete_calendar_id)
                        calendar_name = calendar_to_delete.calendar_name
                        
                        # 해당 Calendar를 사용하는 직원이 있는지 확인
                        if calendar_to_delete.attendancemonthly_set.exists():
                            messages.error(request, f'カレンダー「{calendar_name}」は使用中のため削除できません。')
                        else:
                            # 관련된 HolidayCalendar도 삭제
                            calendar_to_delete.holidaycalendar_set.all().delete()
                            calendar_to_delete.delete()
                            messages.success(request, f'カレンダー「{calendar_name}」を削除しました。')
                        
                        return HttpResponseRedirect(reverse('admin:calendar_management'))
                    except Calendar.DoesNotExist:
                        messages.error(request, '指定されたカレンダーが見つかりません。')
                        return HttpResponseRedirect(reverse('admin:calendar_management'))
                
                # 기존 Calendar 선택하여 HolidayCalendar 생성
                calendar = form.cleaned_data['calendar']
                if calendar:
                    start_date = form.cleaned_data['start_date']
                    end_date = form.cleaned_data['end_date']
                    category = form.cleaned_data['category']
                    
                    # 日付範囲で休日を一括登録
                    from datetime import date, timedelta
                    current_date = start_date
                    created_count = 0
                    
                    while current_date <= end_date:
                        # 既存の休日があるかチェック
                        existing_holiday = HolidayCalendar.objects.filter(
                            calendar_code=calendar,
                            date=current_date,
                            category=category
                        ).first()
                        
                        if not existing_holiday:
                            # 新しい休日を作成
                            holiday = HolidayCalendar(
                                calendar_code=calendar,
                                date=current_date,
                                category=category
                            )
                            holiday.save()
                            created_count += 1
                        
                        current_date += timedelta(days=1)
                    
                    if created_count > 0:
                        messages.success(request, f'{calendar.calendar_name}に{created_count}件の休日を登録しました。')
                    else:
                        messages.info(request, '指定された期間の休日は既に登録されています。')
                    
                    return HttpResponseRedirect(reverse('admin:calendar_management'))
                
                # HolidayCalendar 개별 삭제 처리
                delete_holiday_id = request.POST.get('delete_holiday_id')
                if delete_holiday_id:
                    try:
                        holiday_to_delete = HolidayCalendar.objects.get(id=delete_holiday_id)
                        holiday_to_delete.delete()
                        messages.success(request, '休日を削除しました。')
                        return HttpResponseRedirect(reverse('admin:calendar_management'))
                    except HolidayCalendar.DoesNotExist:
                        messages.error(request, '指定された休日が見つかりません。')
                        return HttpResponseRedirect(reverse('admin:calendar_management'))
                
                # HolidayCalendar 개별 수정 처리
                edit_holiday_id = request.POST.get('edit_holiday_id')
                if edit_holiday_id:
                    try:
                        holiday_to_edit = HolidayCalendar.objects.get(id=edit_holiday_id)
                        new_date = request.POST.get('edit_holiday_date')
                        new_category = request.POST.get('edit_holiday_category')
                        
                        if new_date and new_category:
                            holiday_to_edit.date = new_date
                            holiday_to_edit.category = new_category
                            holiday_to_edit.save()
                            messages.success(request, '休日を更新しました。')
                        else:
                            messages.error(request, '日付と区分を入力してください。')
                        
                        return HttpResponseRedirect(reverse('admin:calendar_management'))
                    except HolidayCalendar.DoesNotExist:
                        messages.error(request, '指定された休日が見つかりません。')
                        return HttpResponseRedirect(reverse('admin:calendar_management'))
                
                else:
                    messages.error(request, 'カレンダーを選択するか、新しいカレンダーを作成してください。')
        else:
            form = CalendarManagementForm()
        
        # カレンダー一覧と休日統計を取得
        calendars = Calendar.objects.all().order_by('calendar_name')
        calendar_stats = []
        
        for cal in calendars:
            holiday_count = cal.holidaycalendar_set.count()
            employee_count = cal.attendancemonthly_set.count()
            
            # 각 Calendar의 HolidayCalendar 목록도 가져오기
            holidays = cal.holidaycalendar_set.all().order_by('date')
            
            calendar_stats.append({
                'calendar': cal,
                'holiday_count': holiday_count,
                'employee_count': employee_count,
                'holidays': holidays
            })
        
        context = dict(
            self.each_context(request),
            form=form,
            calendar_stats=calendar_stats,
        )
        return render(request, "admin/attendance/calendar_management.html", context)

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
        from .permissions import get_accessible_work_places
        accessible_places = get_accessible_work_places(user)
        print(f"[DEBUG] 部長 접근 가능 근무지: {accessible_places}")
        
        # 접근 가능한 근무지의 직원들만 필터링
        from django.db.models import Q
        place_filters = Q()
        for place in accessible_places:
            place_filters |= Q(place_work=place)
        
        filtered = queryset.filter(place_filters)
        print(f"[DEBUG] 部長 필터 결과: {filtered.count()}명, {[e.employee_no for e in filtered]}")
        return filtered
    return queryset.filter(employee_no=user.employee_no)

@admin.register(Employee, site=custom_admin_site)
class EmployeeAdmin(admin.ModelAdmin):
    """社員管理用のカスタムAdmin"""
    form = EmployeeChangeForm  # カスタムフォームを適用
    
    list_display = (
        'employee_no', 'last_name', 'first_name', 'place_work', 'position_groups', 'email', 'detail_button',
    )
    list_filter = ('place_work', 'is_active', 'groups')
    search_fields = ('employee_no', 'last_name', 'first_name', 'place_work', 'email')
    ordering = ('employee_no',)
    
    # フィールドセットのカスタマイズ
    fieldsets = (
        ('社員情報', {
            'fields': ('employee_no', 'password'),
            'description': 'パスワードを変更する場合は新しいパスワードを入力してください。変更しない場合は空欄のままにしてください。'
        }),
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
        # MySQL 제약사항을 우회하기 위해 개별 업데이트
        updated = 0
        for employee in queryset:
            employee.is_active = False
            employee.save()
            updated += 1
        self.message_user(request, f"{updated}名退社処理完了.")
    retire_selected.short_description = "退社処理"

    def delete_selected(self, request, queryset):
        # MySQL 제약사항을 우회하기 위해 개별 삭제
        count = 0
        for employee in queryset:
            employee.delete()
            count += 1
        self.message_user(request, f"{count}名の従業員を削除しました.")
    delete_selected.short_description = "削除"

    def restore_selected(self, request, queryset):
        # MySQL 제약사항을 우회하기 위해 개별 업데이트
        updated = 0
        for employee in queryset:
            employee.is_active = True
            employee.save()
            updated += 1
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
            # 部長: 근무지 그룹별 접근 권한 확인
            if '部長' in user_groups:
                from .permissions import can_access_employee_data
                can_access = can_access_employee_data(user, obj)
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
        # 追加ボタン을非表示
        return False
    
    def add_view(self, request, form_url='', extra_context=None):
        """新しい従業員を追加するビュー - パスワードの暗号化処理"""
        if not self.has_add_permission(request):
            return self.response_post_save_add(request, None)
        
        if request.method == 'POST':
            form = self.get_form(request, request.POST)
            if form.is_valid():
                employee = form.save(commit=False)
                
                # パスワードが入力された場合にのみ暗号化
                if form.cleaned_data.get('password'):
                    employee.set_password(form.cleaned_data['password'])
                
                employee.save()
                form.save_m2m()  # Many-to-many 関係を保存
                
                self.log_addition(request, employee, [])
                return self.response_post_save_add(request, employee)
        else:
            form = self.get_form(request)
        
        context = {
            'title': '従業員追加',
            'form': form,
            'opts': self.model._meta,
            'has_add_permission': True,
        }
        if extra_context:
            context.update(extra_context)
        
        return render(request, 'admin/attendance/employee_add.html', context)

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


# Group 모델을 CustomAdminSite에 등록
from django.contrib.auth.admin import GroupAdmin

# Group 모델의 verbose_name 변경
Group._meta.verbose_name = '職級管理'
Group._meta.verbose_name_plural = '職級管理'

class CustomGroupAdmin(GroupAdmin):
    """커스텀 그룹 관리 - ID 컬럼 추가"""
    list_display = ('code', 'position')
    list_display_links = ('code', 'position')
    ordering = ('id',)
    
    # CSS 파일 참조 제거 (파일이 존재하지 않을 수 있음)
    # class Media:
    #     css = {
    #         'all': ('attendance/css/custom_group_admin.css',)
    #     }
    
    def code(self, obj):
        """코드 컬럼"""
        return obj.id
    code.short_description = 'コード'
    code.admin_order_field = 'id'
    
    def position(self, obj):
        """직급 컬럼"""
        return obj.name
    position.short_description = '職級'
    position.admin_order_field = 'name'
    
    # get_model_perms 메서드 단순화 (500 에러 방지)
    def get_model_perms(self, request):
        """모델 권한 설정"""
        return super().get_model_perms(request)

custom_admin_site.register(Group, CustomGroupAdmin)

class EmployeeCSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='CSVファイルを選択')

class CalendarManagementForm(forms.Form):
    """現場・カレンダー統合管理フォーム"""
    # Calendar 선택 (기존 Calendar가 있는 경우)
    calendar = forms.ModelChoiceField(
        queryset=Calendar.objects.all(),
        label='カレンダー選択',
        empty_label='カレンダーを選択してください',
        required=False,
        help_text='既存のカレンダーを選択するか、下記で新規作成してください'
    )
    
    # Calendar 생성/수정을 위한 필드들
    calendar_name = forms.CharField(
        label='カレンダー名',
        max_length=20,
        required=False,
        help_text='新しいカレンダーを作成する場合は入力してください'
    )
    start_time = forms.TimeField(
        label='開始時刻',
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text='勤務開始時刻'
    )
    end_time = forms.TimeField(
        label='終了時刻',
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text='勤務終了時刻'
    )
    work_hours = forms.FloatField(
        label='稼働時間(時間)',
        required=False,
        min_value=0,
        max_value=24,
        help_text='1日の勤務時間（時間単位）'
    )
    lunch_time = forms.IntegerField(
        label='昼休み(分)',
        required=False,
        min_value=0,
        max_value=180,
        help_text='昼休み時間（分単位）'
    )
    etc = forms.CharField(
        label='備考',
        max_length=200,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='カレンダーに関する備考'
    )
    
    # HolidayCalendar 생성을 위한 필드들
    start_date = forms.DateField(
        label='開始日',
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='休日登録の開始日を選択してください'
    )
    end_date = forms.DateField(
        label='終了日',
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='休日登録の終了日を選択してください'
    )
    category = forms.ChoiceField(
        choices=[
            ('祝日', '祝日'),
            ('休日', '休日'),
            ('休日(法)', '休日(法)'),
            ('特別休暇', '特別休暇'),
            ('その他', 'その他'),
        ],
        label='区分',
        initial='祝日'
    )

