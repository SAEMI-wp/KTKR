# メイン画面ビュー
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import datetime, date
import calendar
import json
import collections
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.views import View
from django.http import HttpResponse
from django.template.loader import render_to_string

from ..models import AttendanceMonthly, HolidayCalendar, AttendanceDaily
from ..forms import MonthlyAttendanceForm, DailyAttendanceForm
from ..cache_utils import get_monthly_data_with_cache, invalidate_monthly_cache, preload_adjacent_months
from ..structures import DailyData
import requests

# カレンダーの最初の曜日を日曜日に設定
calendar.setfirstweekday(calendar.SUNDAY)


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


def fetch_japanese_holidays(year):
    """
    日本の祝日APIから、指定年の祝日情報を取得します。
    """
    try:
        # 日本の祝日API (https://holidays-jp.github.io/api/v1/)
        url = f"https://holidays-jp.github.io/api/v1/{year}/date.json"
        print(f"[HOLIDAY API] API 호출 시작: {url}")  # デバッグ用ログ
        
        response = requests.get(url, timeout=10)
        print(f"[HOLIDAY API] 응답 상태 코드: {response.status_code}")  # デバッグ用ログ
        
        response.raise_for_status()
        
        holidays_data = response.json()
        print(f"[HOLIDAY API] 원본 데이터 샘플: {dict(list(holidays_data.items())[:3])}")  # デバッグ用ログ
        
        holidays_dict = {}
        
        for date_str, holiday_info in holidays_data.items():
            # 実際のAPI応答形式: "2025-01-01": "元日"
            if isinstance(holiday_info, dict):
                # 辞書形式の場合 (想定した形式)
                holidays_dict[date_str] = holiday_info.get('name', '祝日')
            else:
                # 文字列形式の場合 (実際のAPI応答)
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
class MainView(AjaxLoginRequiredMixin, TemplateView):
    template_name = 'attendance/main.html'
    login_url = 'attendance:login'
    
    # メインビューのgetメソッド
    def get(self, request, *args, **kwargs):
        # AJAXリクエストの場合はカレンダー部分だけ返す
        if request.GET.get('ajax') == '1' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            context = self.get_context_data(**kwargs)
            html = render_to_string('attendance/calendar_partial.html', context, request=request)
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)
    
    # メインビューのget_context_dataメソッド
    def get_context_data(self, **kwargs):
        # カレンダーのコンテキストデータを生成
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
        
        # default_day 計算
        today = date.today()
        if calendar_date.year == today.year and calendar_date.month == today.month:
            default_day = today.day
        elif calendar_date < today.replace(day=1):
            # 過去月: 最終日
            last_day = calendar.monthrange(calendar_date.year, calendar_date.month)[1]
            default_day = last_day
        else:
            # 未来月: 1日
            default_day = 1
        context['default_day'] = default_day
        
        # 初期選択された日付は常に今日の日付 (要件)
        context['selected_date'] = today
        
        # Calendar 데이터 추가
        from ..models import Calendar
        context['calendars'] = Calendar.objects.all().order_by('id')
        
        # タブ状態管理: 0=カレンダー, 1=リスト (デフォルト: 0)
        show_list_view = self.request.GET.get('show_list', '0') == '1'
        context['show_list_view'] = show_list_view
        
        # タブ状態に応じたコンテキスト設定
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
        
        monthly_data = get_monthly_data_with_cache(
            employee=self.request.user,
            year=str(calendar_date.year),
            month=str(calendar_date.month)
        )
        context['monthly_data'] = monthly_data
        
        # トグル状態の処理 - 月情報 유무에 따라 동적 설정
        toggle_state = self.request.GET.get('toggle_state')
        if toggle_state is None:
            # URL 파라미터가 없으면 월정보 유무에 따라 기본값 설정
            toggle_state = '1' if monthly_data is None else '0'
        context['toggle_state'] = toggle_state
        
        # タブスイッチャーの位置決定: 月情報が開いている場合は月情報の下に、そうでない場合はトグルボタンの下に
        context['tab_switcher_position'] = 'after_monthly' if (monthly_data is not None and toggle_state == '1') else 'after_toggle'
        context['form'] = MonthlyAttendanceForm()
        # monthly_dataがなくてもdaily_formは常に提供
        # monthly_dataがなくてもdisabledフォームを作成
        context['daily_form'] = DailyAttendanceForm(disabled=monthly_data is None)
        
        # 今日の日付の日次データを取得 (form_partial.htmlで使用)
        today = date.today()
        selected_daily_data = None
        if monthly_data and monthly_data.daily_list:
            for daily in monthly_data.daily_list:
                if daily.date == today:
                    selected_daily_data = daily
                    break
        
        context['selected_daily_data'] = selected_daily_data
        
        # 基本勤務区分の設定 (日次データがない場合)
        if not selected_daily_data:
            # 曜日別の基本勤務区分の設定
            day_of_week = today.weekday()  # 0=月曜日, 6=日曜日
            print(f"DEBUG: Today is {today}, weekday: {day_of_week}")
            if day_of_week == 6:  # 日曜日
                context['default_work_type'] = '休日(法)'
                print("DEBUG: Set default_work_type to 休日(法)")
            elif day_of_week == 5:  # 土曜日
                context['default_work_type'] = '休日'
                print("DEBUG: Set default_work_type to 休日")
            else:  # 平日
                context['default_work_type'] = '出勤'
                print("DEBUG: Set default_work_type to 出勤")
        else:
            context['default_work_type'] = None
            print(f"DEBUG: Selected daily data exists: {selected_daily_data.work_type}")
        
        print(f"DEBUG: Context selected_date: {context.get('selected_date')}")
        print(f"DEBUG: Context default_work_type: {context.get('default_work_type')}")
        print(f"DEBUG: Context selected_daily_data: {context.get('selected_daily_data')}")
        
        # カレンダーとweekdaysは常に生成 (monthly_dataがなくても)
        calendar_data = self.generate_calendar_data(
            calendar_date,
            monthly_data.daily_list if monthly_data else [],
            monthly_data,
            set() # API 祝日はここでは処理せず、別途取得
        )
        context['calendar'] = calendar_data
        context['weekdays'] = ['日', '月', '火', '水', '木', '金', '土']
        
        # デバッグ: カレンダーデータの確認
        print(f"DEBUG: Generated calendar data length: {len(calendar_data)}")
        for week_idx, week in enumerate(calendar_data):
            print(f"DEBUG: Week {week_idx}: {len(week)} days")
            for day_idx, day in enumerate(week):
                if day and day.get('date'):
                    print(f"DEBUG: Week {week_idx}, Day {day_idx}: {day['date']} (data-date will be: {day['date'].strftime('%Y-%m-%d')})")

        # holidays_db: 3개월분(전월, 당월, 다음월) 휴일 정보를 DB에서 가져와서 context에 추가
        calendar_name = None
        if monthly_data and monthly_data.calendar_name:
            calendar_name = monthly_data.calendar_name
        holidays_db, api_holiday_set = self._get_holiday_data(calendar_date, calendar_name)
        
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
        context['holidays_db_json'] = json.dumps(holidays_db)
        
        # API 祝日情報 (JavaScriptで使用)
        api_holidays = get_holidays_for_months(calendar_date.year, calendar_date.month)
        context['api_holidays_json'] = json.dumps(api_holidays)
        
        # デバッグ用ログ
        print(f"[BACKEND] {calendar_date.year}년 {calendar_date.month}월 공휴일 데이터:")
        print(f"[BACKEND] api_holidays 개수: {len(api_holidays)}")
        print(f"[BACKEND] api_holidays 샘플: {dict(list(api_holidays.items())[:5])}")
        
        # 月別リストデータ (リストタブ用)
        # API 祝日データをdateオブジェクトに変換
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
        
        # 前月に月情報があるか確認 (コピーボタン表示用)
        prev_month = calendar_date.replace(day=1) - timezone.timedelta(days=1)
        from ..models import AttendanceMonthly
        prev_monthly_exists = AttendanceMonthly.objects.filter(
            employee=self.request.user,
            year=str(prev_month.year),
            month=str(prev_month.month).zfill(2)
        ).exists()
        
        context['prev_monthly_exists'] = prev_monthly_exists
        
        # 隣接月データを事前に読み込み (TTL ベースのキャッシュ使用)
        preload_adjacent_months(self.request.user, calendar_date.year, calendar_date.month)
        
        return context

    # 月別データの生成 (calendar_partial.htmlで使用)
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

    # カレンダーデータの生成 (calendar_partial.htmlで使用)
    def generate_calendar_data(self, calendar_date, daily_list, monthly_data, api_holiday_set):
        # 構造体ベースのカレンダーデータを生成
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

    def _get_holiday_data(self, calendar_date, calendar_name=None):
        """3か月分(前月, 当月, 翌月)の休日データをDBから取得します."""
        current_year = calendar_date.year
        current_month = calendar_date.month
        
        # 3か月分の範囲を計算
        months = []
        for diff in [-1, 0, 1]:
            y = current_year + ((current_month + diff - 1) // 12)
            m = (current_month + diff - 1) % 12 + 1
            months.append((y, m))
        
        # 月別の日付を生成
        month_dates = []
        for y, m in months:
            last_day = calendar.monthrange(y, m)[1]
            for d in range(1, last_day + 1):
                month_dates.append(date(y, m, d))
        
        # 基本カレンダー名を設定
        calendars = ['Techave']
        if calendar_name and calendar_name not in calendars:
            calendars.append(calendar_name)
        
        # DBから休日情報を取得
        # Calendar 테이블이存在しない場合は空のクエリセットを返す
        try:
            from ..models import Calendar
            calendar_ids = []
            for calendar_name in calendars:
                try:
                    # 더 안전한 쿼리 실행
                    calendar_obj = Calendar.objects.using('default').get(calendar_name=calendar_name)
                    calendar_ids.append(calendar_obj.id)
                except Calendar.DoesNotExist:
                    # Calendarがない場合はデフォルト値を使用
                    pass
                except Exception as e:
                    print(f"[WARNING] Calendar 조회 실패 ({calendar_name}): {e}")
                    continue
            
            if calendar_ids:
                # 더 안전한 쿼리 실행
                holidays = HolidayCalendar.objects.using('default').filter(
                    calendar_code__in=calendar_ids, 
                    date__in=month_dates
                )
            else:
                # Calendarがない場合は空のクエリセットを返す
                holidays = HolidayCalendar.objects.none()
        except Exception as e:
            # Calendar 테이블이 존재しない場合やその他のエラーの場合
            print(f"[WARNING] Calendar 테이블 접근 실패: {e}")
            holidays = HolidayCalendar.objects.none()
        holidays_db = collections.defaultdict(list)
        api_holiday_set = set()
        
        for h in holidays:
            holidays_db[h.date.strftime('%Y-%m-%d')].append(h.category)
            api_holiday_set.add(h.date)
        
        return holidays_db, api_holiday_set 


# ===================== AJAX用 Partial ビュー =====================

# カレンダー/リストセクション用 AJAX ビュー
class CalendarPartialView(MainView):
    template_name = 'attendance/calendar_partial.html'
    
    def get_context_data(self, **kwargs):
        # MainViewのget_context_dataを呼び出し、必要なcontextのみを返す
        context = super().get_context_data(**kwargs)
        
        # calendar_partial.htmlに必要なcontextのみを保持
        # (form関連のcontextは削除)
        context.pop('form', None)
        context.pop('daily_form', None)
        context.pop('default_day', None)
        
        # トグル状態の処理 - 月情報 유무에 따라 동적 설정
        toggle_state = self.request.GET.get('toggle_state')
        if toggle_state is None:
            # URL 파라미터가 없으면 월정보 유무에 따라 기본값 설정
            monthly_data = context.get('monthly_data')
            toggle_state = '1' if monthly_data is None else '0'
        context['toggle_state'] = toggle_state
        
        # calendar contextが正しくあるか確認
        if 'calendar' not in context or not context['calendar']:
            print(f"DEBUG: Calendar context missing or empty. Context keys: {list(context.keys())}")
            # calendarを再生成
            calendar_date = context.get('calendar_date')
            monthly_data = context.get('monthly_data')
            if calendar_date and monthly_data:
                # API 祝日データを取得
                api_holidays = get_holidays_for_months(calendar_date.year, calendar_date.month)
                api_holiday_set = set(api_holidays.keys())
                
                context['calendar'] = self.generate_calendar_data(
                    calendar_date,
                    monthly_data.daily_list if monthly_data else [],
                    monthly_data,
                    api_holiday_set
                )
        
        return context

    # MainViewのメソッドを継承して使用
    pass


# 勤怠登録フォームセクション用 AJAX ビュー
class FormPartialView(AjaxLoginRequiredMixin, TemplateView):
    template_name = 'attendance/form_partial.html'
    login_url = 'attendance:login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # URLパラメータから選択された日付を取得 (YYYY-MM-DD)
        selected_date_str = self.request.GET.get('date')
        today = datetime.today().date()
        
        if selected_date_str:
            try:
                # YYYY-MM-DD 形式のパース
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                calendar_date = date(selected_date.year, selected_date.month, 1)  # カレンダー年月
            except (ValueError, TypeError):
                # パースに失敗した場合は今日の日付を使用
                selected_date = today
                calendar_date = date(today.year, today.month, 1)
        else:
            # URLパラメータがない場合は今日の日付を使用
            selected_date = today
            calendar_date = date(today.year, today.month, 1)
        
        # 重要な変数を設定
        context['calendar_date'] = calendar_date  # カレンダー年月 (YYYY-MM-01)
        context['selected_date'] = selected_date  # dateオブジェクトをそのまま渡す
        context['default_day'] = today.day  # 今日の日付の日 (常に今日)
        
        # 選択された日付の年月に対応する月別データを取得
        monthly_data = get_monthly_data_with_cache(
            employee=self.request.user,
            year=str(selected_date.year),
            month=str(selected_date.month)
        )
        context['monthly_data'] = monthly_data
        
        # 選択された日付の日次データを取得
        selected_daily_data = None
        if monthly_data and monthly_data.daily_list:
            for daily in monthly_data.daily_list:
                if daily.date == selected_date:
                    selected_daily_data = daily
                    break
        
        context['selected_daily_data'] = selected_daily_data
        
        # 基本勤務区分の設定 (日次データがない場合)
        if not selected_daily_data:
            # API祝日情報確認
            api_holidays = get_holidays_for_months(selected_date.year, selected_date.month)
            selected_date_str = selected_date.strftime('%Y-%m-%d')
            is_api_holiday = selected_date_str in api_holidays
            
            # 祝日優先, 次に曜日別の基本勤務区分を設定
            if is_api_holiday:
                context['default_work_type'] = '祝日'
                print(f"DEBUG: FormPartialView - API 祝日発見: {selected_date_str} -> 祝日")
            else:
                # 曜日別の基本勤務区分の設定
                day_of_week = selected_date.weekday()  # 0=月曜日, 6=日曜日
                if day_of_week == 6:  # 日曜日
                    context['default_work_type'] = '休日(法)'
                elif day_of_week == 5:  # 土曜日
                    context['default_work_type'] = '休日'
                else:  # 平日
                    context['default_work_type'] = '出勤'
                print(f"DEBUG: FormPartialView - 曜日別基本区分: {selected_date_str} -> {context['default_work_type']}")
        else:
            context['default_work_type'] = None
        
        # daily_form 作成 (monthly_dataがない場合は無効化)
        context['daily_form'] = DailyAttendanceForm(disabled=monthly_data is None)
        
        # Calendar 객체를 별도로 전달 (HTML에서 start_time, end_time 접근용)
        if monthly_data and monthly_data.calendar_id:
            try:
                from ..models import Calendar
                calendar_obj = Calendar.objects.get(id=monthly_data.calendar_id)
                context['calendar_obj'] = calendar_obj
                print(f"DEBUG: FormPartialView - Calendar 객체 전달: {calendar_obj.calendar_name} ({calendar_obj.start_time} - {calendar_obj.end_time})")
            except Calendar.DoesNotExist:
                print(f"DEBUG: FormPartialView - Calendar를 찾을 수 없음: ID {monthly_data.calendar_id}")
            except Exception as e:
                print(f"DEBUG: FormPartialView - Calendar 조회 오류: {e}")
        
        return context


# ===================== データ API ビュー =====================

class MonthlyInfoSectionView(AjaxLoginRequiredMixin, TemplateView):
    """月情報セクションのみをレンダリングするAJAXビュー"""
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
            
            # キャッシュの整合性を確認して月別データを取得
            from ..utils import get_monthly_structure
            
            # キャッシュから先に確認
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


class DailyDataAPIView(AjaxLoginRequiredMixin, View):
    """日次データ取得API"""
    login_url = 'attendance:login'
    
    def get(self, request):
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'error': 'Date parameter required'}, status=400)
        
        try:
            # 日付のパース
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            employee = request.user
            
            # 1. セッションから確認 (キャッシュされたデータ)
            session_key = f"daily_data_{employee.employee_no}_{date_str}"
            if session_key in request.session:
                print(f"DEBUG: Daily data found in session for {date_str}")
                return JsonResponse(request.session[session_key])
            
            # 2. DBから取得
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
                    'alternative_work_date1': daily_record.alternative_work_date1.strftime('%Y-%m-%d') if daily_record.alternative_work_date1 else '',
                    'alternative_work_date2': daily_record.alternative_work_date2.strftime('%Y-%m-%d') if daily_record.alternative_work_date2 else '',
                    'alternative_work_date3': daily_record.alternative_work_date3.strftime('%Y-%m-%d') if daily_record.alternative_work_date3 else '',
                    'notes': daily_record.notes or '',
                    'date': date_str
                }
                
                # セッションにキャッシュ
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


class MonthlyDataAPIView(AjaxLoginRequiredMixin, View):
    """月別データ取得API"""
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
            
            # 1. セッションから確認 (キャッシュされたデータ)
            session_key = f"monthly_data_{employee.employee_no}_{year}_{month}"
            if session_key in request.session:
                print(f"DEBUG: Monthly data found in session for {year}-{month}")
                return JsonResponse(request.session[session_key])
            
            # 2. DBから取得
            from ..models import AttendanceMonthly
            try:
                monthly_record = AttendanceMonthly.objects.get(
                    employee=employee,
                    year=str(year),
                    month=str(month)
                )
                
                data = {
                    'project_name': monthly_record.project_name,
                    'calendar_id': monthly_record.base_calendar.id if monthly_record.base_calendar else None,
                    'calendar_name': monthly_record.base_calendar.calendar_name if monthly_record.base_calendar and hasattr(monthly_record.base_calendar, 'calendar_name') else None,
                    'break_minutes': monthly_record.base_calendar.break_minutes if monthly_record.base_calendar and hasattr(monthly_record.base_calendar, 'break_minutes') else None,
                    'standard_work_hours': float(monthly_record.base_calendar.standard_work_hours) if monthly_record.base_calendar and hasattr(monthly_record.base_calendar, 'standard_work_hours') else None,
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
                
                # セッションにキャッシュ
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
        
        # デバッグログ
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