# 월별 출근 관리 관련 뷰들
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.urls import reverse_lazy
from django.http import JsonResponse
import json

from ..models import AttendanceMonthly, AttendanceDaily
from ..forms import MonthlyAttendanceForm
from ..utils import get_or_create_monthly_structure, update_monthly_from_structure
from ..cache_utils import invalidate_monthly_cache


# AJAX 요청에 대해 적절한 HTTP 상태 코드를 반환하는 커스텀 LoginRequiredMixin
class AjaxLoginRequiredMixin(LoginRequiredMixin):
    """AJAX 요청 시 세션 만료 시 401 상태 코드를 반환하는 믹스인"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            # AJAX 요청인지 확인
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
                return JsonResponse({'error': 'Authentication required'}, status=401)
            # 일반 요청은 기본 LoginRequiredMixin 동작 (리다이렉트)
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


# 月別勤怠作成ビュー（ログイン必須）
class MonthlyAttendanceCreateView(AjaxLoginRequiredMixin, CreateView):
    model = AttendanceMonthly
    form_class = MonthlyAttendanceForm
    template_name = 'attendance/monthly_form.html'
    success_url = reverse_lazy('attendance:main')
    login_url = 'attendance:login'
    
    def form_valid(self, form):
        print("=== MonthlyAttendanceCreateView form_valid called ===")
        print(f"Request method: {self.request.method}")
        print(f"Request POST data: {self.request.POST}")
        
        form.instance.employee = self.request.user
        # URLパラメータから年月を取得
        year = self.request.POST.get('year')
        month = self.request.POST.get('month')
        print(f"Year: {year}, Month: {month}")
        
        if year and month:
            form.instance.year = str(year)
            form.instance.month = str(month).zfill(2)
            print(f"Set year: {form.instance.year}, month: {form.instance.month}")
        
        # Calendar ID 처리
        base_calendar_id = self.request.POST.get('base_calendar')
        if base_calendar_id:
            from ..models import Calendar
            try:
                calendar_obj = Calendar.objects.get(id=base_calendar_id)
                form.instance.base_calendar = calendar_obj
                print(f"Set base_calendar: {calendar_obj.calendar_name} (ID: {base_calendar_id})")
            except Calendar.DoesNotExist:
                print(f"Warning: Calendar with ID {base_calendar_id} not found")
                # 기본 Calendar 사용
                calendar_obj = Calendar.objects.first()
                if calendar_obj:
                    form.instance.base_calendar = calendar_obj
        
        try:
            result = super().form_valid(form)
            print(f"Monthly attendance created successfully: {form.instance}")
            
            # 캐시 무효화 (새로 생성된 월의 캐시 삭제)
            from ..cache_utils import invalidate_monthly_cache
            invalidate_monthly_cache(
                employee_id=self.request.user.employee_no,
                year=str(year),
                month=str(month)
            )
            
            # AJAX 요청인 경우 JSON 응답
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': '月別情報が正常に登録されました。'
                })
            
            return result
        except Exception as e:
            print(f"Error creating monthly attendance: {e}")
            import traceback
            traceback.print_exc()
            
            # AJAX 요청인 경우 JSON 응답
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'登録中にエラーが発生しました: {str(e)}'
                })
            
            raise
    
    def form_invalid(self, form):
        print("=== MonthlyAttendanceCreateView form_invalid called ===")
        print(f"Form errors: {form.errors}")
        
        # AJAX 요청인 경우 JSON 응답
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'フォームの入力に問題があります。',
                'errors': form.errors
            })
        
        return super().form_invalid(form)


# 月別勤怠削除ビュー（ログイン必須）
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class MonthlyAttendanceDeleteView(View):
    def post(self, request, *args, **kwargs):
        print("=== MonthlyAttendanceDeleteView called ===")
        try:
            data = json.loads(request.body)
            year = data.get('year')
            month = data.get('month')
            
            print(f"Deleting monthly attendance for year: {year}, month: {month}")
            
            if not year or not month:
                return JsonResponse({'status': 'error', 'message': '年月情報が不足しています'})
            
            # 구조체 기반으로 월별 데이터 가져오기
            monthly_data = get_or_create_monthly_structure(
                employee=request.user,
                year=str(year),
                month=str(month)
            )
            
            if not monthly_data:
                return JsonResponse({'status': 'error', 'message': '該当する月別勤怠情報が見つかりません'})
            
            # DB에서 삭제
            monthly_model = AttendanceMonthly.objects.filter(
                employee=request.user,
                year=str(year),
                month=str(month).zfill(2)
            ).first()
            
            if monthly_model:
                # 관련하는 일별 데이터도 삭제
                daily_count = AttendanceDaily.objects.filter(monthly_attendance=monthly_model).count()
                AttendanceDaily.objects.filter(monthly_attendance=monthly_model).delete()
                
                # 월별 데이터를 삭제
                monthly_model.delete()
                
                print(f"Deleted monthly attendance and {daily_count} daily records")
            
            # 캐시 무효화 (해당 월의 캐시 삭제)
            invalidate_monthly_cache(
                employee_id=request.user.employee_no,
                year=str(year),
                month=str(month)
            )
            
            return JsonResponse({
                'status': 'success', 
                'message': f'{year}年{month}月の勤怠情報を削除しました。'
            })
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'JSONデータの解析に失敗しました'})
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)})


# 月別勤怠修正ビュー
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class MonthlyAttendanceUpdateView(View):
    def post(self, request, *args, **kwargs):
        try:
            # FormDataで送信された場合はrequest.POST.getで取得
            year = request.POST.get('year')
            month = request.POST.get('month')
            project_name = request.POST.get('project_name')
            base_calendar_id = request.POST.get('base_calendar')
            # break_minutes와 standard_work_hours는 이제 Calendar 모델에서 가져옴
            
            # 디버깅용 로그
            print(f"[MONTHLY_UPDATE] 서버에서 받은 데이터:")
            print(f"  year: {year}")
            print(f"  month: {month}")
            print(f"  project_name: {project_name}")
            print(f"  base_calendar_id: {base_calendar_id}")
            # 必要に応じて他のフィールドも取得

            # 必須チェック
            if not year or not month:
                return JsonResponse({'status': 'error', 'message': '年月情報が不足しています'})

            # 既存の月別データ取得
            monthly_data = get_or_create_monthly_structure(
                employee=request.user,
                year=str(year),
                month=str(month)
            )
            if not monthly_data:
                return JsonResponse({'status': 'error', 'message': '該当する月別勤怠情報が見つかりません'})

            # 値を更新
            monthly_data.project_name = project_name or monthly_data.project_name
            if base_calendar_id:
                try:
                    from .models import Calendar
                    calendar_obj = Calendar.objects.get(id=base_calendar_id)
                    monthly_data.base_calendar = calendar_obj.calendar_name  # 문자열로 저장
                    print(f"[MONTHLY_UPDATE] Calendar 설정: {calendar_obj.calendar_name} (ID: {base_calendar_id})")
                except Calendar.DoesNotExist:
                    print(f"[MONTHLY_UPDATE] Calendar를 찾을 수 없음: ID {base_calendar_id}")
                    return JsonResponse({'status': 'error', 'message': '指定されたカレンダーが見つかりません'})

            # DB保存
            update_monthly_from_structure(monthly_data, request.user)

            # キャッシュ無効化（該当月のキャッシュを必ず削除）
            invalidate_monthly_cache(
                employee_id=request.user.employee_no,
                year=str(year),
                month=str(month)
            )

            return JsonResponse({'status': 'success', 'message': '修正しました。'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)})


# [추가] 3개월치 월별 정보를 한 번에 내려주는 bulk API
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class MonthlyBulkInfoView(View):
    """
    3개월치 월별 정보를 한 번에 내려주는 API
    GET 파라미터: year, month (기준)
    반환: { 'YYYY-MM': {exist: true, ...}, ... }
    월별 데이터가 없으면 exist: false만 반환
    """
    def get(self, request, *args, **kwargs):
        year = request.GET.get('year')
        month = request.GET.get('month')
        if not year or not month:
            return JsonResponse({'status': 'error', 'message': 'year, month 파라미터가 필요합니다.'})
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'year, month는 정수여야 합니다.'})
        # 3개월치 월별 데이터 preload (TTL 기반 캐시 사용)
        from ..cache_utils import preload_adjacent_months
        preloaded = preload_adjacent_months(request.user, year, month)
        result = {}
        for key, monthly_data in preloaded.items():
            if monthly_data:
                # 필요한 최소 정보만 반환 (exist: true)
                result[key] = {
                    'exist': True,
                    'project_name': getattr(monthly_data, 'project_name', None),
                    'base_calendar': monthly_data.base_calendar.id if monthly_data.base_calendar else None,
                    'base_calendar_name': monthly_data.base_calendar.calendar_name if monthly_data.base_calendar and hasattr(monthly_data.base_calendar, 'calendar_name') else (str(monthly_data.base_calendar) if monthly_data.base_calendar else None),
                    'break_minutes': monthly_data.base_calendar.break_minutes if monthly_data.base_calendar and hasattr(monthly_data.base_calendar, 'break_minutes') else None,
                    'standard_work_hours': float(monthly_data.base_calendar.standard_work_hours) if monthly_data.base_calendar and hasattr(monthly_data.base_calendar, 'standard_work_hours') else None,
                }
            else:
                result[key] = {'exist': False}
        return JsonResponse({'status': 'success', 'data': result}) 