# 메인 뷰
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import datetime, date
import calendar
import json
import collections

from ..models import AttendanceMonthly, HolidayCalendar
from ..forms import MonthlyAttendanceForm, DailyAttendanceForm
from ..cache_utils import get_monthly_data_with_cache, preload_adjacent_months
from ..structures import DailyData

# カレンダーの最初の曜日を日曜日に設定
calendar.setfirstweekday(calendar.SUNDAY)


# メインビュー（ログイン必須）
class MainView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/main.html'
    login_url = 'attendance:login'
    
    def get_context_data(self, **kwargs):
        import calendar  # 함수 맨 위에서 항상 import
        context = super().get_context_data(**kwargs)
        
        # URLパラメータから年月を取得
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')
        
        if year is None or month is None:
            # 오늘 날짜로 기본값 설정
            today = datetime.today()
            year = today.year
            month = today.month
        else:
            year = int(year)
            month = int(month)
        
        current_date = date(year, month, 1)
        context['current_date'] = current_date
        context['today'] = date.today()
        
        # default_day 계산
        today = date.today()
        if current_date.year == today.year and current_date.month == today.month:
            default_day = today.day
        elif current_date < today.replace(day=1):
            # 과거달: 마지막일
            last_day = calendar.monthrange(current_date.year, current_date.month)[1]
            default_day = last_day
        else:
            # 미래달: 1일
            default_day = 1
        context['default_day'] = default_day
        
        # 캐싱을 사용하여 월별 데이터 가져오기 (캐시 우선, 없으면 DB에서 로드)
        monthly_data = get_monthly_data_with_cache(
            employee=self.request.user,
            year=str(current_date.year),
            month=str(current_date.month)
        )
        context['monthly_data'] = monthly_data
        context['form'] = MonthlyAttendanceForm()
        # monthly_data가 없어도 daily_form은 항상 제공
        # monthly_data가 없으면 disabled 폼 생성
        context['daily_form'] = DailyAttendanceForm(disabled=monthly_data is None)
        
        # 캘린더와 weekdays는 항상 생성 (monthly_data가 없어도)
        context['calendar'] = self.generate_calendar_data(
            current_date,
            monthly_data.daily_list if monthly_data else [],
            monthly_data,
            set() # API 공휴일은 여기서 처리하지 않고, 따로 가져옴
        )
        context['weekdays'] = ['日', '月', '火', '水', '木', '金', '土']

        # holidays_db: 3개월치(전월, 당월, 익월) 휴일 정보를 DB에서 가져와 context에 추가
        current_year = current_date.year
        current_month = current_date.month
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
        for h in holidays:
            holidays_db[h.date].append({'calendar_name': h.calendar_name, 'category': h.category})
        holidays_db_strkey = {d.strftime('%Y-%m-%d'): v for d, v in holidays_db.items()}
        context['holidays_db'] = dict(holidays_db_strkey)
        context['holidays_db_json'] = json.dumps(holidays_db_strkey, ensure_ascii=False)

        # 휴일 정보 준비 (DB holiday)
        holidays_set = set()
        for dstr in context['holidays_db'].keys():
            holidays_set.add(datetime.strptime(dstr, '%Y-%m-%d').date())

        # API 공휴일 받아오기 (requests)
        import requests
        api_holidays = {}
        try:
            res = requests.get('https://holidays-jp.github.io/api/v1/date.json')
            if res.status_code == 200:
                api_holidays = res.json()
        except Exception as e:
            api_holidays = {}
        context['api_holidays_json'] = json.dumps(api_holidays, ensure_ascii=False)
        # 이번 달 API 공휴일 set
        api_holiday_set = set()
        year_str = str(current_date.year)
        month_str = f"{current_date.month:02d}"
        for date_str, name in api_holidays.items():
            if date_str.startswith(f"{year_str}-{month_str}"):
                api_holiday_set.add(datetime.strptime(date_str, '%Y-%m-%d').date())

        # 리스트/캘린더용 한 달치 날짜/요일 데이터 always 제공
        month_days = []
        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        for dt in cal.itermonthdates(current_date.year, current_date.month):
            if dt.month == current_date.month:
                month_days.append(self.make_month_day(dt, monthly_data, monthly_data.daily_list if monthly_data else [], api_holiday_set))
        context['month_days_list'] = month_days

        # 인접 월 데이터 미리 로드
        preload_adjacent_months(self.request.user, current_date.year, current_date.month)

        # Employee 객체는 self.request.user
        employee = self.request.user

        # 전달 연/월 계산
        employee_no = self.request.user.employee_no
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        year = str(year)
        month = f"{int(month):02d}"
        prev_year = str(prev_year)
        prev_month = f"{int(prev_month):02d}"

        prev_monthly_data = AttendanceMonthly.objects.filter(
            employee__employee_no=employee_no, year=prev_year, month=prev_month
        ).first()

        context['prev_monthly_data'] = prev_monthly_data
        context['year'] = year
        context['month'] = month
    
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

    def generate_calendar_data(self, current_date, daily_list, monthly_data, api_holiday_set):
        import collections
        from django.utils.safestring import mark_safe
        # 구조체 기반 캘린더 데이터 생성
        cal = calendar.monthcalendar(current_date.year, current_date.month)
        calendar_data = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    week_data.append({'date': None, 'record': None, 'holiday_category': [], 'is_saturday': False, 'is_sunday': False, 'is_api_holiday': False, 'default_work_type': None})
                else:
                    day_date = date(current_date.year, current_date.month, day)
                    md = self.make_month_day(day_date, monthly_data, daily_list, api_holiday_set)
                    week_data.append(md)
            calendar_data.append(week_data)
        return calendar_data

    def get_holidays_db(self, current_date):
        import collections
        from ..models import HolidayCalendar
        current_year = current_date.year
        current_month = current_date.month
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