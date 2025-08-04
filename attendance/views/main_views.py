# 메인 뷰
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import datetime, date
import calendar
import json
import collections
from django.http import JsonResponse
from django.views import View
from django.http import HttpResponse
from django.template.loader import render_to_string

from ..models import AttendanceMonthly, HolidayCalendar, AttendanceDaily
from ..forms import MonthlyAttendanceForm, DailyAttendanceForm
from ..cache_utils import get_monthly_data_with_cache, invalidate_monthly_cache
from ..structures import DailyData
import requests

# カレンダーの最初の曜日を日曜日に設定
calendar.setfirstweekday(calendar.SUNDAY)


def fetch_japanese_holidays(year):
    """
    일본 공휴일 API에서 해당 연도의 공휴일 정보를 가져옵니다.
    """
    try:
        # 일본 공휴일 API (https://holidays-jp.github.io/api/v1/)
        url = f"https://holidays-jp.github.io/api/v1/{year}/date.json"
        print(f"[HOLIDAY API] API 호출 시작: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"[HOLIDAY API] 응답 상태 코드: {response.status_code}")
        
        response.raise_for_status()
        
        holidays_data = response.json()
        print(f"[HOLIDAY API] 원본 데이터 샘플: {dict(list(holidays_data.items())[:3])}")
        
        holidays_dict = {}
        
        for date_str, holiday_info in holidays_data.items():
            # 실제 API 응답 형식: "2025-01-01": "元日"
            if isinstance(holiday_info, dict):
                # 딕셔너리 형태인 경우 (예상했던 형식)
                holidays_dict[date_str] = holiday_info.get('name', '祝日')
            else:
                # 문자열 형태인 경우 (실제 API 응답)
                holidays_dict[date_str] = str(holiday_info)
        
        print(f"[HOLIDAY API] {year}년 공휴일 {len(holidays_dict)}개 로드 완료")
        print(f"[HOLIDAY API] 변환된 데이터 샘플: {dict(list(holidays_dict.items())[:3])}")
        return holidays_dict
        
    except requests.RequestException as e:
        print(f"[HOLIDAY API] {year}년 공휴일 로드 실패: {e}")
        return {}
    except Exception as e:
        print(f"[HOLIDAY API] {year}년 공휴일 파싱 실패: {e}")
        return {}


def get_holidays_for_months(year, month):
    """
    해당 월과 전후 월의 공휴일 정보를 가져옵니다.
    """
    print(f"[HOLIDAY MONTHS] {year}년 {month}월 공휴일 수집 시작")
    holidays = {}
    
    # 전년, 해당년, 익년의 공휴일 정보를 가져옴
    for y in [year - 1, year, year + 1]:
        print(f"[HOLIDAY MONTHS] {y}년 공휴일 가져오기 시작")
        year_holidays = fetch_japanese_holidays(y)
        print(f"[HOLIDAY MONTHS] {y}년 공휴일 {len(year_holidays)}개 가져옴")
        holidays.update(year_holidays)
    
    print(f"[HOLIDAY MONTHS] 총 {len(holidays)}개 공휴일 수집 완료")
    print(f"[HOLIDAY MONTHS] 샘플 데이터: {dict(list(holidays.items())[:5])}")
    return holidays


# メインビュー（ログ必須）
class MainView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/main.html'
    login_url = 'attendance:login'
    
    def get(self, request, *args, **kwargs):
        # AJAXリクエストの場合はカレンダー部分だけ返す
        if request.GET.get('ajax') == '1' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            context = self.get_context_data(**kwargs)
            html = render_to_string('attendance/calendar_partial.html', context, request=request)
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        import calendar  # 함수 맨 위에서 항상 import
        context = super().get_context_data(**kwargs)
        
        # URLパラメータから年月を取得
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        
        if year is None or month is None:
            # 本日を取得
            today = datetime.today()
            year = today.year
            month = today.month
        else:
            year = int(year)
            month = int(month)
        
        calendar_date = date(year, month, 1)
        context['calendar_date'] = calendar_date
        context['today'] = date.today()
        
        # default_day 계산
        today = date.today()
        if calendar_date.year == today.year and calendar_date.month == today.month:
            default_day = today.day
        elif calendar_date < today.replace(day=1):
            # 과거달: 마지막일
            last_day = calendar.monthrange(calendar_date.year, calendar_date.month)[1]
            default_day = last_day
        else:
            # 미래달: 1일
            default_day = 1
        context['default_day'] = default_day
        
        # 초기 선택된 날짜는 항상 오늘 날짜 (요구사항)
        context['selected_date'] = today
        
        # 탭 상태 관리: 0=캘린더, 1=리스트 (기본값: 0)
        show_list_view = self.request.GET.get('show_list', '0') == '1'
        context['show_list_view'] = show_list_view
        
        # 탭 상태에 따른 컨텍스트 설정
        if show_list_view:
            context['calendar_tab_display'] = 'none'
            context['list_tab_display'] = 'block'
            context['calendar_tab_active'] = False
            context['list_tab_active'] = True
        else:
            context['calendar_tab_display'] = 'block'
            context['list_tab_display'] = 'none'
            context['calendar_tab_active'] = True
            context['list_tab_active'] = False
        
        # TTL 기반 캐시에서 월별 데이터 가져오기 (5분 자동 만료)
        from ..cache_utils import get_monthly_data_with_cache
        
        monthly_data = get_monthly_data_with_cache(
            employee=self.request.user,
            year=str(calendar_date.year),
            month=str(calendar_date.month)
        )
        context['monthly_data'] = monthly_data
        
        # 토글 상태 처리
        toggle_state = self.request.GET.get('toggle_state', '0')  # 기본값: 0 (green)
        context['toggle_state'] = toggle_state
        
        # 탭 스위처 위치 결정: 월정보가 열려있으면 월정보 아래에, 아니면 토글 버튼 아래에
        context['tab_switcher_position'] = 'after_monthly' if (monthly_data is not None and toggle_state == '1') else 'after_toggle'
        context['form'] = MonthlyAttendanceForm()
        # monthly_data가 없어도 daily_form은 항상 제공
        # monthly_data가 없으면 disabled 폼 생성
        context['daily_form'] = DailyAttendanceForm(disabled=monthly_data is None)
        
        # 오늘 날짜의 일일 데이터 가져오기 (form_partial.html에서 사용)
        today = date.today()
        selected_daily_data = None
        if monthly_data and monthly_data.daily_list:
            for daily in monthly_data.daily_list:
                if daily.date == today:
                    selected_daily_data = daily
                    break
        
        context['selected_daily_data'] = selected_daily_data
        
        # 기본 근무구분 설정 (일일 데이터가 없는 경우)
        if not selected_daily_data:
            # 요일별 기본 근무구분 설정
            day_of_week = today.weekday()  # 0=월요일, 6=일요일
            print(f"DEBUG: Today is {today}, weekday: {day_of_week}")
            if day_of_week == 6:  # 일요일
                context['default_work_type'] = '休日(法)'
                print("DEBUG: Set default_work_type to 休日(法)")
            elif day_of_week == 5:  # 토요일
                context['default_work_type'] = '休日'
                print("DEBUG: Set default_work_type to 休日")
            else:  # 평일
                context['default_work_type'] = '出勤'
                print("DEBUG: Set default_work_type to 出勤")
        else:
            context['default_work_type'] = None
            print(f"DEBUG: Selected daily data exists: {selected_daily_data.work_type}")
        
        print(f"DEBUG: Context selected_date: {context.get('selected_date')}")
        print(f"DEBUG: Context default_work_type: {context.get('default_work_type')}")
        print(f"DEBUG: Context selected_daily_data: {context.get('selected_daily_data')}")
        
        # 캘린더와 weekdays는 항상 생성 (monthly_data가 없어도)
        calendar_data = self.generate_calendar_data(
            calendar_date,
            monthly_data.daily_list if monthly_data else [],
            monthly_data,
            set() # API 공휴일은 여기서 처리하지 않고, 따로 가져옴
        )
        context['calendar'] = calendar_data
        context['weekdays'] = ['日', '月', '火', '水', '木', '金', '土']
        
        # 디버그: 캘린더 데이터 확인
        print(f"DEBUG: Generated calendar data length: {len(calendar_data)}")
        for week_idx, week in enumerate(calendar_data):
            print(f"DEBUG: Week {week_idx}: {len(week)} days")
            for day_idx, day in enumerate(week):
                if day and day.get('date'):
                    print(f"DEBUG: Week {week_idx}, Day {day_idx}: {day['date']} (data-date will be: {day['date'].strftime('%Y-%m-%d')})")

        # holidays_db: 3개월치(전월, 당월, 익월) 휴일 정보를 DB에서 가져와 context에 추가
        current_year = calendar_date.year
        current_month = calendar_date.month
        months = []
        for diff in [-1, 0, 1]:
            y = current_year + ((current_month + diff - 1) // 12)
            m = (current_month + diff - 1) % 12 + 1
            months.append((y, m))
        month_dates = []
        for y, m in months:
            last_day = calendar.monthrange(y, m)[1]
            for d in range(1, last_day + 1):
                month_dates.append(date(y, m, d))
        base_calendar = None
        if monthly_data:
            base_calendar = monthly_data.base_calendar
        calendars = ['共通']
        if base_calendar and base_calendar not in calendars:
            calendars.append(base_calendar)
        holidays = HolidayCalendar.objects.filter(calendar_name__in=calendars, date__in=month_dates)
        holidays_db = collections.defaultdict(list)
        api_holiday_set = set()
        for h in holidays:
            holidays_db[h.date.strftime('%Y-%m-%d')].append(h.category)
            api_holiday_set.add(h.date)
        
        # API公休日情報をパースしてセット化
        import json as _json
        try:
            api_holidays = _json.loads(context.get('api_holidays_json', '{}'))
            for ymd, name in api_holidays.items():
                try:
                    dt = datetime.strptime(ymd, '%Y-%m-%d').date()
                    api_holiday_set.add(dt)
                except Exception:
                    pass
        except Exception:
            pass
        # DB休日も合成
        for h in holidays:
            api_holiday_set.add(h.date)
        context['holidays_db_json'] = json.dumps(holidays_db)
        
        # API 공휴일 정보 (JavaScript에서 사용)
        api_holidays = get_holidays_for_months(calendar_date.year, calendar_date.month)
        context['api_holidays_json'] = json.dumps(api_holidays)
        
        # 디버깅용 로그
        print(f"[BACKEND] {calendar_date.year}년 {calendar_date.month}월 공휴일 데이터:")
        print(f"[BACKEND] api_holidays 개수: {len(api_holidays)}")
        print(f"[BACKEND] api_holidays 샘플: {dict(list(api_holidays.items())[:5])}")
        
        # 월별 리스트 데이터 (리스트 탭용)
        # API 공휴일 데이터를 date 객체로 변환
        api_holiday_dates = set()
        for date_str in api_holidays.keys():
            try:
                holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                api_holiday_dates.add(holiday_date)
                print(f"[BACKEND] 공휴일 변환: {date_str} -> {holiday_date}")
            except ValueError:
                print(f"[BACKEND] 공휴일 변환 실패: {date_str}")
                continue
        
        print(f"[BACKEND] 리스트용 API 공휴일 날짜: {api_holiday_dates}")
        print(f"[BACKEND] 8월 11일 포함 여부: {date(2025, 8, 11) in api_holiday_dates}")
        
        context['month_days_list'] = build_month_days_list(
            self.request.user,
            calendar_date.year,
            calendar_date.month,
            api_holiday_dates
        )
        
        # 이전 월에 월정보가 있는지 확인 (복사 버튼 표시용)
        prev_month = calendar_date.replace(day=1) - timezone.timedelta(days=1)
        from ..models import AttendanceMonthly
        prev_monthly_exists = AttendanceMonthly.objects.filter(
            employee=self.request.user,
            year=str(prev_month.year),
            month=str(prev_month.month).zfill(2)
        ).exists()
        
        context['prev_monthly_exists'] = prev_monthly_exists
        
        # 인접 월 데이터 미리 로드 (TTL 기반 캐시 사용)
        from ..cache_utils import preload_adjacent_months
        preload_adjacent_months(self.request.user, calendar_date.year, calendar_date.month)
        
        return context

    def make_month_day(self, dt, monthly_data, daily_list, api_holiday_set):
        record = None
        if monthly_data and daily_list:
            for d in daily_list:
                if d.date == dt:
                    record = d
                    break
        is_saturday = (dt.weekday() == 5)
        is_sunday = (dt.weekday() == 6)
        is_api_holiday = dt in api_holiday_set
        default_work_type = None
        if is_api_holiday:
            default_work_type = '祝日'
        elif is_sunday:
            default_work_type = '休日(法)'
        elif is_saturday:
            default_work_type = '休日'
        return {
            'date': dt,
            'weekday': dt.weekday(),
            'record': record,
            'is_saturday': is_saturday,
            'is_sunday': is_sunday,
            'is_api_holiday': is_api_holiday,
            'default_work_type': default_work_type
        }

    def generate_calendar_data(self, calendar_date, daily_list, monthly_data, api_holiday_set):
        import collections
        from django.utils.safestring import mark_safe
        # 구조체 기반 캘린더 데이터 생성
        cal = calendar.monthcalendar(calendar_date.year, calendar_date.month)
        calendar_data = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append({'date': None, 'record': None, 'holiday_category': [], 'is_saturday': False, 'is_sunday': False, 'is_api_holiday': False, 'default_work_type': None})
                else:
                    day_date = date(calendar_date.year, calendar_date.month, day)
                    md = self.make_month_day(day_date, monthly_data, daily_list, api_holiday_set)
                    week_data.append(md)
            calendar_data.append(week_data)
        return calendar_data

    def get_holidays_db(self, calendar_date):
        import collections
        from ..models import HolidayCalendar
        current_year = calendar_date.year
        current_month = calendar_date.month
        months = []
        for diff in [-1, 0, 1]:
            y = current_year + ((current_month + diff - 1) // 12)
            m = (current_month + diff - 1) % 12 + 1
            months.append((y, m))
        month_dates = []
        for y, m in months:
            last_day = calendar.monthrange(y, m)[1]
            for d in range(1, last_day + 1):
                month_dates.append(date(y, m, d))
        calendars = ['共通']
        holidays = HolidayCalendar.objects.filter(calendar_name__in=calendars, date__in=month_dates)
        holidays_db = collections.defaultdict(list)
        for h in holidays:
            holidays_db[h.date].append({'calendar_name': h.calendar_name, 'category': h.category})
        return dict(holidays_db) 


# ===================== AJAX용 Partial 뷰들 =====================

# カレンダー/リストセクション용 AJAX 뷰
class CalendarPartialView(MainView):
    template_name = 'attendance/calendar_partial.html'
    
    def get_context_data(self, **kwargs):
        # MainView의 get_context_data를 호출하되, 필요한 context만 반환
        context = super().get_context_data(**kwargs)
        
        # calendar_partial.html에 필요한 context만 유지
        # (form 관련 context는 제거)
        context.pop('form', None)
        context.pop('daily_form', None)
        context.pop('default_day', None)
        
        # 토글 상태 처리
        toggle_state = self.request.GET.get('toggle_state', '0')  # 기본값: 0 (green)
        context['toggle_state'] = toggle_state
        
        # calendar context가 제대로 있는지 확인
        if 'calendar' not in context or not context['calendar']:
            print(f"DEBUG: Calendar context missing or empty. Context keys: {list(context.keys())}")
            # calendar를 다시 생성
            calendar_date = context.get('calendar_date')
            monthly_data = context.get('monthly_data')
            if calendar_date and monthly_data:
                # API 공휴일 데이터 가져오기
                api_holidays = get_holidays_for_months(calendar_date.year, calendar_date.month)
                api_holiday_set = set(api_holidays.keys())
                
                context['calendar'] = self.generate_calendar_data(
                    calendar_date,
                    monthly_data.daily_list if monthly_data else [],
                    monthly_data,
                    api_holiday_set
                )
        
        return context

    # MainView의 메서드들을 상속받아 사용
    pass


# 勤怠登録フォームセクション용 AJAX 뷰
class FormPartialView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/form_partial.html'
    login_url = 'attendance:login'
    
    def get_context_data(self, **kwargs):
        import calendar
        context = super().get_context_data(**kwargs)
        
        # URLパラメータ에서 선택된 날짜 가져오기 (YYYY-MM-DD)
        selected_date_str = self.request.GET.get('date')
        today = datetime.today().date()
        
        if selected_date_str:
            try:
                # YYYY-MM-DD 형식 파싱
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                calendar_date = date(selected_date.year, selected_date.month, 1)  # 캘린더 년월
            except (ValueError, TypeError):
                # 파싱 실패 시 오늘 날짜 사용
                selected_date = today
                calendar_date = date(today.year, today.month, 1)
        else:
            # URL 파라미터가 없으면 오늘 날짜 사용
            selected_date = today
            calendar_date = date(today.year, today.month, 1)
        
        # 핵심 변수들 설정
        context['calendar_date'] = calendar_date  # 캘린더 년월 (YYYY-MM-01)
        context['selected_date'] = selected_date  # date 객체 그대로 전달
        context['default_day'] = today.day  # 오늘 날짜의 일 (항상 오늘)
        
        # 선택된 날짜의 년월에 해당하는 월별 데이터 가져오기
        monthly_data = get_monthly_data_with_cache(
            employee=self.request.user,
            year=str(selected_date.year),
            month=str(selected_date.month)
        )
        context['monthly_data'] = monthly_data
        
        # 선택된 날짜의 일일 데이터 가져오기
        selected_daily_data = None
        if monthly_data and monthly_data.daily_list:
            for daily in monthly_data.daily_list:
                if daily.date == selected_date:
                    selected_daily_data = daily
                    break
        
        context['selected_daily_data'] = selected_daily_data
        
        # 기본 근무구분 설정 (일일 데이터가 없는 경우)
        if not selected_daily_data:
            # 요일별 기본 근무구분 설정
            day_of_week = selected_date.weekday()  # 0=월요일, 6=일요일
            if day_of_week == 6:  # 일요일
                context['default_work_type'] = '休日(法)'
            elif day_of_week == 5:  # 토요일
                context['default_work_type'] = '休日'
            else:  # 평일
                context['default_work_type'] = '出勤'
        else:
            context['default_work_type'] = None
        
        # daily_form 생성 (monthly_data가 없으면 disabled)
        context['daily_form'] = DailyAttendanceForm(disabled=monthly_data is None)
        
        return context


# ===================== 데이터 API Views =====================

class MonthlyInfoSectionView(LoginRequiredMixin, TemplateView):
    """월정보 섹션만 렌더링하는 AJAX 뷰"""
    template_name = 'attendance/monthly_info_section.html'
    login_url = 'attendance:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # URLパラメータから年月を取得
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        
        if not year or not month:
            return context
        
        try:
            year = int(year)
            month = int(month)
            calendar_date = date(year, month, 1)
            
            # 캐시 무결성 검증 후 월별 데이터 가져오기
            from ..utils import get_monthly_structure
            from ..cache_utils import get_monthly_data_with_cache, invalidate_monthly_cache
            
            # 캐시에서 먼저 확인
            monthly_data = get_monthly_data_with_cache(
                employee=self.request.user,
                year=str(calendar_date.year),
                month=str(calendar_date.month)
            )
            
            context['monthly_data'] = monthly_data
            context['calendar_date'] = calendar_date
            
        except (ValueError, TypeError):
            pass
        
        return context


class DailyDataAPIView(LoginRequiredMixin, View):
    """일일 데이터 가져오기 API"""
    login_url = 'attendance:login'
    
    def get(self, request):
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'error': 'Date parameter required'}, status=400)
        
        try:
            # 날짜 파싱
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            employee = request.user
            
            # 1. 세션에서 확인 (캐시된 데이터)
            session_key = f"daily_data_{employee.employee_no}_{date_str}"
            if session_key in request.session:
                print(f"DEBUG: Daily data found in session for {date_str}")
                return JsonResponse(request.session[session_key])
            
            # 2. DB에서 조회
            from ..models import AttendanceDaily
            try:
                daily_record = AttendanceDaily.objects.get(
                    employee=employee,
                    date=selected_date
                )
                
                data = {
                    'work_type': daily_record.work_type,
                    'start_time': daily_record.start_time.strftime('%H:%M') if daily_record.start_time else '',
                    'end_time': daily_record.end_time.strftime('%H:%M') if daily_record.end_time else '',
                    'alternative_work_date': daily_record.alternative_work_date.strftime('%Y-%m-%d') if daily_record.alternative_work_date else '',
                    'notes': daily_record.notes or '',
                    'date': date_str
                }
                
                # 세션에 캐시
                request.session[session_key] = data
                print(f"DEBUG: Daily data loaded from DB and cached for {date_str}")
                
                return JsonResponse(data)
                
            except AttendanceDaily.DoesNotExist:
                print(f"DEBUG: No daily data found for {date_str}")
                return JsonResponse({'error': 'No data found'}, status=404)
        
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
        except Exception as e:
            print(f"DEBUG: Error loading daily data: {e}")
            return JsonResponse({'error': str(e)}, status=500)


class MonthlyDataAPIView(LoginRequiredMixin, View):
    """월별 데이터 가져오기 API"""
    login_url = 'attendance:login'
    
    def get(self, request):
        year = request.GET.get('year')
        month = request.GET.get('month')
        
        if not year or not month:
            return JsonResponse({'error': 'Year and month parameters required'}, status=400)
        
        try:
            year = int(year)
            month = int(month)
            employee = request.user
            
            # 1. 세션에서 확인 (캐시된 데이터)
            session_key = f"monthly_data_{employee.employee_no}_{year}_{month}"
            if session_key in request.session:
                print(f"DEBUG: Monthly data found in session for {year}-{month}")
                return JsonResponse(request.session[session_key])
            
            # 2. DB에서 조회
            from ..models import AttendanceMonthly
            try:
                monthly_record = AttendanceMonthly.objects.get(
                    employee=employee,
                    year=str(year),
                    month=str(month)
                )
                
                data = {
                    'project_name': monthly_record.project_name,
                    'base_calendar': monthly_record.base_calendar,
                    'break_minutes': monthly_record.break_minutes,
                    'standard_work_hours': float(monthly_record.standard_work_hours),
                    'work_days': monthly_record.work_days,
                    'paid_leave_days': monthly_record.paid_leave_days,
                    'total_regular_work_hours': float(monthly_record.total_regular_work_hours),
                    'total_deduction_hours': float(monthly_record.total_deduction_hours),
                    'total_overtime_hours': float(monthly_record.total_overtime_hours),
                    'total_late_night_overtime_hours': float(monthly_record.total_late_night_overtime_hours),
                    'total_holiday_work_hours': float(monthly_record.total_holiday_work_hours),
                    'holiday_work_hours_night': float(monthly_record.holiday_work_hours_night),
                    'year': year,
                    'month': month,
                    'exists': True
                }
                
                # 세션에 캐시
                request.session[session_key] = data
                print(f"DEBUG: Monthly data loaded from DB and cached for {year}-{month}")
                
                return JsonResponse(data)
                
            except AttendanceMonthly.DoesNotExist:
                print(f"DEBUG: No monthly data found for {year}-{month}")
                return JsonResponse({'error': 'No monthly data found', 'exists': False}, status=404)
        
        except ValueError:
            return JsonResponse({'error': 'Invalid year or month'}, status=400)
        except Exception as e:
            print(f"DEBUG: Error loading monthly data: {e}")
            return JsonResponse({'error': str(e)}, status=500) 

# ===================== 月別リストデータ生成関数 =====================
def build_month_days_list(employee, year, month, api_holiday_set):
    """
    指定月の全日付について、DBから日別データを取得し、
    公休日・土日・基本勤務区分も含めてリストを生成する
    """
    import calendar
    from datetime import date
    days_in_month = calendar.monthrange(year, month)[1]
    month_days_list = []
    
    print(f"[BUILD LIST] {year}년 {month}월 리스트 생성 시작")
    print(f"[BUILD LIST] API 공휴일 세트: {api_holiday_set}")
    
    for day in range(1, days_in_month + 1):
        dt = date(year, month, day)
        # DBから日別データを取得（社員はmonthly_attendance経由で参照）
        try:
            record = AttendanceDaily.objects.get(monthly_attendance__employee=employee, date=dt)
        except AttendanceDaily.DoesNotExist:
            record = None
        is_saturday = (dt.weekday() == 5)
        is_sunday = (dt.weekday() == 6)
        is_api_holiday = dt in api_holiday_set
        
        if is_api_holiday:
            default_work_type = '祝日'
        elif is_sunday:
            default_work_type = '休日(法)'
        elif is_saturday:
            default_work_type = '休日'
        else:
            default_work_type = '出勤'
        
        # 디버깅 로그
        if is_api_holiday:
            print(f"[BUILD LIST] 공휴일 발견: {dt} -> {default_work_type}")
        elif dt == date(2025, 8, 11):
            print(f"[BUILD LIST] 8월 11일 체크: is_api_holiday={is_api_holiday}, api_holiday_set={api_holiday_set}")
        
        month_days_list.append({
            'date': dt,
            'weekday': dt.weekday(),
            'record': record,
            'is_saturday': is_saturday,
            'is_sunday': is_sunday,
            'is_api_holiday': is_api_holiday,
            'default_work_type': default_work_type
        })
    
    print(f"[BUILD LIST] 리스트 생성 완료: {len(month_days_list)}일")
    return month_days_list 