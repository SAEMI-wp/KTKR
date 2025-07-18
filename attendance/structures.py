from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, time, datetime, timedelta

@dataclass
class DailyData:
    date: date
    work_type: Optional[str]
    start_time: Optional[time]
    end_time: Optional[time]
    alternative_work_date: Optional[date] = None
    notes: Optional[str] = None
    is_required: bool = False
    is_confirmed: bool = False
    
    break_minutes: int = 0  
    standard_work_hours: float = 0.0
    
    regular_work_hours: Optional[float] = None
    deduction_hours: Optional[float] = None
    overtime_hours: Optional[float] = None
    late_night_overtime_hours: Optional[float] = None
    total_hours: Optional[float] = None
    
    def calculate_work_hours(self):
        """모든 근무시간 계산 메서드"""
        self._calculate_regular_work_hours()
        self._calculate_deduction_hours()
        self._calculate_overtime_hours()
        self._calculate_late_night_hours()
        self._calculate_total_hours()

    def _get_overlap_minutes(self, period_start, period_end, check_start, check_end):
        """두 시간대의 겹치는 시간을 분으로 반환"""
        overlap_start = max(period_start, check_start)
        overlap_end = min(period_end, check_end)
        if overlap_start < overlap_end:
            return (overlap_end - overlap_start).total_seconds() / 60.0
        return 0.0

    def _calculate_regular_work_hours(self):
        """정규시간 계산. <<< 최종 규칙: 휴일에는 무조건 null"""
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.regular_work_hours = None
            return
        
        # <<< 사용자의 최종 규칙에 따라, 휴일일 경우 이 필드는 null이 되어야 함
        if self.work_type in ['休日', '休日(法)', '祝日', '振替']:
            self.regular_work_hours = None
            return

        work_start = datetime.combine(self.date, time(9, 0))
        work_lunch_start = datetime.combine(self.date, time(12, 0))
        work_lunch_end = work_lunch_start + timedelta(minutes=self.break_minutes)
        work_end = datetime.combine(self.date, time(18, 0))

        actual_start = datetime.combine(self.date, self.start_time)
        actual_end = datetime.combine(self.date, self.end_time)
        if actual_end < actual_start:
            actual_end += timedelta(days=1)

        morning_minutes = self._get_overlap_minutes(actual_start, actual_end, work_start, work_lunch_start)
        afternoon_minutes = self._get_overlap_minutes(actual_start, actual_end, work_lunch_end, work_end)
        
        total_minutes = morning_minutes + afternoon_minutes
        self.regular_work_hours = round(total_minutes / 60.0, 2)

    def _calculate_deduction_hours(self):
        """공제 시간 계산. 휴일에는 항상 null"""
        if self.work_type in ['休日', '休日(法)', '祝日', '振替']:
            self.deduction_hours = None
            return
        if self.regular_work_hours is None:
            self.deduction_hours = None
            return
        if self.start_time is not None and self.end_time is not None and self.start_time == self.end_time:
            self.deduction_hours = None
            return

        standard_hours = 8.0
        deduction = standard_hours - self.regular_work_hours
        self.deduction_hours = round(max(0.0, deduction), 2)

    def _calculate_overtime_hours(self):
        """잔업시간 계산. <<< 최종 규칙: 휴일에는 주간 근무를 잔업에 합산"""
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.overtime_hours = None
            return

        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
            
        next_day = self.date + timedelta(days=1)
        total_overtime_minutes = 0

        # 1. 표준 잔업 시간대 계산 (모든 근무일에 공통)
        evening_slot1_start = datetime.combine(self.date, time(18, 0))
        evening_slot1_end = datetime.combine(self.date, time(19, 30))
        evening_slot2_start = datetime.combine(self.date, time(20, 0))
        evening_slot2_end = datetime.combine(self.date, time(22, 0))
        morning_slot_start = datetime.combine(next_day, time(7, 0))
        morning_slot_end = datetime.combine(next_day, time(9, 0))
        
        total_overtime_minutes += self._get_overlap_minutes(start_dt, end_dt, evening_slot1_start, evening_slot1_end)
        total_overtime_minutes += self._get_overlap_minutes(start_dt, end_dt, evening_slot2_start, evening_slot2_end)
        total_overtime_minutes += self._get_overlap_minutes(start_dt, end_dt, morning_slot_start, morning_slot_end)
        
        # 2. <<< 휴일인 경우, 주간 근무(09:00-18:00)를 계산하여 잔업에 추가
        if self.work_type in ['休日', '休日(法)', '祝日', '振替']:
            work_start = datetime.combine(self.date, time(9, 0))
            work_lunch_start = datetime.combine(self.date, time(12, 0))
            work_lunch_end = work_lunch_start + timedelta(minutes=self.break_minutes)
            work_end = datetime.combine(self.date, time(18, 0))
            
            holiday_day_morning = self._get_overlap_minutes(start_dt, end_dt, work_start, work_lunch_start)
            holiday_day_afternoon = self._get_overlap_minutes(start_dt, end_dt, work_lunch_end, work_end)
            total_overtime_minutes += holiday_day_morning + holiday_day_afternoon
        
        self.overtime_hours = round(total_overtime_minutes / 60.0, 2)
        
    def _calculate_late_night_hours(self):
        """심야시간 계산 (수정 없음, 완성된 로직)"""
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.late_night_overtime_hours = None
            return

        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        next_day = self.date + timedelta(days=1)
        late_night_hours = 0.0
        bonus_start = datetime.combine(next_day, time(4, 0))
        bonus_end = datetime.combine(next_day, time(4, 30))
        if self._get_overlap_minutes(start_dt, end_dt, bonus_start, bonus_end) > 0:
            late_night_hours += 1.0

        current_time = datetime.combine(self.date, time(22, 0))
        late_night_end_time = datetime.combine(next_day, time(6, 30))
        late_night_breaks = [
            (datetime.combine(self.date, time(22, 0)), datetime.combine(self.date, time(22, 30))),
            (datetime.combine(next_day, time(0, 30)), datetime.combine(next_day, time(1, 0))),
            (datetime.combine(next_day, time(3, 0)), datetime.combine(next_day, time(4, 0))),
        ]
        while current_time < late_night_end_time:
            slot_end_time = current_time + timedelta(minutes=30)
            if current_time >= bonus_start and current_time < bonus_end:
                current_time = slot_end_time
                continue
            if self._get_overlap_minutes(start_dt, end_dt, current_time, slot_end_time) > 0:
                is_break_slot = any(self._get_overlap_minutes(current_time, slot_end_time, br_start, br_end) > 0 for br_start, br_end in late_night_breaks)
                if not is_break_slot:
                    late_night_hours += 0.5
            current_time = slot_end_time
        self.late_night_overtime_hours = round(late_night_hours, 2)

    def _calculate_total_hours(self):
        """소계 계산 (수정 없음)"""
        if not self.end_time or not self.start_time:
            self.total_hours = None
            return
        total = sum(filter(None, [self.regular_work_hours, self.overtime_hours, self.late_night_overtime_hours]))
        self.total_hours = round(total, 2)

@dataclass
class MonthlyData:
    employee_id: int                                                 # 社員番号
    year: str
    month: str
    project_name: str
    base_calendar: str
    break_minutes: int
    standard_work_hours: float
    daily_list: List[DailyData] = field(default_factory=list)
    # 計算 (基本値 = 0)
    total_work_days: int = 0                                         # 出勤日
    total_overtime: float = 0.0

    def calculate_all_daily_hours(self):
        """모든 일별 근무시간 계산"""
        for daily in self.daily_list:
            # 월별 정보를 일별 데이터에 전달
            daily.break_minutes = self.break_minutes
            daily.standard_work_hours = self.standard_work_hours
            daily.calculate_work_hours()

    @property
    def total_regular_work_hours(self) -> float:
    #    """상근시간 합계: 휴일(법), 공휴일, 대체(법) 제외한 나머지 날들의 상근시간 합"""
        total = 0.0
    #    exclude_types = ['休日(法)', '祝日', '振替'] daily.work_type not in exclude_types and 
        
        for daily in self.daily_list:
            if (
                daily.regular_work_hours is not None):
                total += daily.regular_work_hours
        
        return round(total, 2)

    @property
    def total_deduction_hours(self) -> float:
        """공제시간 합계: 모든 일별 공제시간의 합"""
        total = 0.0
        
        for daily in self.daily_list:
            if daily.deduction_hours is not None:
                total += daily.deduction_hours
        
        return round(total, 2)

    @property
    def total_overtime_hours(self) -> float:
        """残業時間合計: 休日(法)、祝日を除く全ての日の残業時間を合算"""
        total = 0.0
        # 休日(法)、祝日は除外
        for daily in self.daily_list:
            if daily.overtime_hours is not None and daily.work_type not in ['休日(法)', '祝日']:
                total += daily.overtime_hours
        return round(total, 2)

    @property
    def total_late_night_overtime_hours(self) -> float:
        """深夜時間合計: 休日(法)、祝日を除く全ての日の深夜時間を合算"""
        total = 0.0
        # 休日(法)、祝日は除外
        for daily in self.daily_list:
            if daily.late_night_overtime_hours is not None and daily.work_type not in ['休日(法)', '祝日']:
                total += daily.late_night_overtime_hours
        return round(total, 2)

    @property
    def total_holiday_work_hours(self) -> float:
        """휴일 근무시간 합계: 법정 휴일(休日(法)、祝日)에 일한 잔업시간의 합"""
        total = 0.0
        legal_holiday_types = ['休日(法)', '祝日']
        
        for daily in self.daily_list:
            if (daily.work_type in legal_holiday_types and 
                daily.overtime_hours is not None):
                total += daily.overtime_hours
        
        return round(total, 2)

    @property
    def holiday_work_hours_night(self) -> float:
        """휴일 심야근무시간 합계: 법정 휴일에 심야근무한 시간의 합"""
        total = 0.0
        legal_holiday_types = ['休日(法)', '祝日']
        
        for daily in self.daily_list:
            if (daily.work_type in legal_holiday_types and 
                daily.late_night_overtime_hours is not None):
                total += daily.late_night_overtime_hours
        
        return round(total, 2)

    @property
    def holiday_work_hours_overtime(self) -> float:
        """잔업시간 환산: 모든 잔업시간을 1.25배율 기준으로 환산한 시간"""
        # 계산식: total_overtime_hours + total_late_night_overtime_hours * 1.5 / 1.25 + 
        #         total_holiday_work_hours * 1.35 / 1.25 + holiday_work_hours_night * 1.6 / 1.25 - 
        #         total_deduction_hours * 1 / 1.25
        
        overtime = self.total_overtime_hours
        late_night = self.total_late_night_overtime_hours * 1.5 / 1.25
        holiday = self.total_holiday_work_hours * 1.35 / 1.25
        holiday_night = self.holiday_work_hours_night * 1.6 / 1.25
        deduction = self.total_deduction_hours * 1.0 / 1.25
        
        total = overtime + late_night + holiday + holiday_night - deduction
        
        return round(max(0.0, total), 2)

    @property
    def work_days(self) -> float:
        """出勤日: start_timeとend_timeが両方あり、かつ値が異なる場合のみカウント"""
        count = 0
        for d in self.daily_list:
            if d.start_time is not None and d.end_time is not None:
                if d.end_time != d.start_time:
                    count += 1
        return round(float(count), 1)

    @property
    def paid_leave_days(self) -> float:
        """年次有給: 有給(半)=0.5, 有給=1"""
        total = 0.0
        for d in self.daily_list:
            if d.work_type == "有給(半)":
                total += 0.5
            elif d.work_type == "有給":
                total += 1.0
        return(total)

    @property
    def special_paid_leave_days(self) -> float:
        """特別休暇 計算"""
        count = sum(1 for d in self.daily_list if d.work_type == "特別休暇")
        return round(float(count), 1)

    @property
    def unpaid_leave_days(self) -> float:
        """無給日: 代休(動)で、alternative_work_dateの年または月がdateと異なる場合のみカウント"""
        count = 0
        for d in self.daily_list:
            if d.work_type == "代休(動)":
                if d.alternative_work_date:
                    if (d.date.year != d.alternative_work_date.year) or (d.date.month != d.alternative_work_date.month):
                        count += 1
                else:
                    # alternative_work_dateがない時もカウント
                    count += 1
        return round(float(count), 1)
