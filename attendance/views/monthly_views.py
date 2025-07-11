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
from ..cache_utils import invalidate_monthly_cache, preload_adjacent_months


# 月別勤怠作成ビュー（ログイン必須）
class MonthlyAttendanceCreateView(LoginRequiredMixin, CreateView):
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
        
        try:
            result = super().form_valid(form)
            print(f"Monthly attendance created successfully: {form.instance}")
            
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


# 月別勤怠修正ビュー（ロ그인必須）
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class MonthlyAttendanceUpdateView(View):
    def post(self, request, *args, **kwargs):
        print("=== MonthlyAttendanceUpdateView called ===")
        try:
            data = json.loads(request.body)
            year = data.get('year')
            month = data.get('month')
            
            print(f"Updating monthly attendance for year: {year}, month: {month}")
            print(f"Update data: {data}")
            
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
            
            # 구조체 데이터 업데이트
            monthly_data.project_name = data.get('project_name', monthly_data.project_name)
            monthly_data.base_calendar = data.get('base_calendar', monthly_data.base_calendar)
            monthly_data.break_minutes = int(data.get('break_minutes', monthly_data.break_minutes))
            monthly_data.standard_work_hours = float(data.get('standard_work_hours', monthly_data.standard_work_hours))
            
            # 일별 데이터의 설정값도 업데이트
            for daily in monthly_data.daily_list:
                daily.break_minutes = monthly_data.break_minutes
                daily.standard_work_hours = monthly_data.standard_work_hours
                # 시간 재계산
                daily.calculate_work_hours()
            
            # DB에 저장
            update_monthly_from_structure(monthly_data, request.user)
            
            # 캐시 무효화 (해당 월의 캐시 삭제)
            invalidate_monthly_cache(
                employee_id=request.user.employee_no,
                year=str(year),
                month=str(month)
            )
            
            print(f"Monthly data updated successfully")
            
            return JsonResponse({
                'status': 'success', 
                'message': f'{year}年{month}月の勤怠情報を修正しました。'
            })
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'JSONデータの解析に失敗しました'})
        except Exception as e:
            print(f"Unexpected error: {e}")
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
        # 3개월치 월별 데이터 preload
        preloaded = preload_adjacent_months(request.user, year, month)
        result = {}
        for key, monthly_data in preloaded.items():
            if monthly_data:
                # 필요한 최소 정보만 반환 (exist: true)
                result[key] = {
                    'exist': True,
                    'project_name': getattr(monthly_data, 'project_name', None),
                    'base_calendar': getattr(monthly_data, 'base_calendar', None),
                    'break_minutes': getattr(monthly_data, 'break_minutes', None),
                    'standard_work_hours': getattr(monthly_data, 'standard_work_hours', None),
                }
            else:
                result[key] = {'exist': False}
        return JsonResponse({'status': 'success', 'data': result}) 