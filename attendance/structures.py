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
    
    # 월별 근태 정보 (계산에 필요)
    break_minutes: int = 60  # 점심시간 (기본값 60분)
    standard_work_hours: float = 8.0  # 기준 근무시간 (기본값 8시간)
    
    # 계산 필드 (초기값은 None으로 설정)
    regular_work_hours: Optional[float] = None  # 상근시간
    deduction_hours: Optional[float] = None     # 공제시간
    overtime_hours: Optional[float] = None      # 잔업시간
    late_night_overtime_hours: Optional[float] = None  # 심야시간
    total_hours: Optional[float] = None         # 소계시간
    
    def calculate_work_hours(self):
        """근무시간 계산 메서드"""
        self._calculate_regular_work_hours()
        self._calculate_deduction_hours()
        self._calculate_overtime_hours()
        self._calculate_total_hours()
    
    def _calculate_regular_work_hours(self):
        """상근시간 계산"""
        # start_time이 비어있으면 null
        if not self.start_time:
            self.regular_work_hours = None
            return
        
        # end_time이 비어있는 경우 처리
        if not self.end_time:
            # 휴일/공휴일/대체휴일인 경우 null
            holiday_types = ['休日(法)', '祝日', '振替(法)', '休日', '振替(休)']
            if self.work_type in holiday_types:
                self.regular_work_hours = None
            else:
                # 그 외에는 기준 근무시간
                self.regular_work_hours = self.standard_work_hours
            return
        
        # start_time과 end_time이 모두 있는 경우
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        
        # 다음날로 넘어가는 경우 처리
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        # 기본 근무시간 계산 (분 단위)
        work_minutes = (end_dt - start_dt).total_seconds() / 60
        
        # 오전 9시~12시 사이 시작인 경우 점심시간 공제
        if time(9, 0) <= self.start_time <= time(12, 0):
            work_minutes -= self.break_minutes
        
        # 기준 근무시간을 초과하는 경우 기준값으로 제한
        if work_minutes > self.standard_work_hours * 60:
            work_minutes = self.standard_work_hours * 60
        
        self.regular_work_hours = work_minutes / 60.0
    
    def _calculate_deduction_hours(self):
        """공제시간 계산"""
        # regular_work_hours가 비어있으면 null
        if self.regular_work_hours is None:
            self.deduction_hours = None
            return
        
        # 휴일/공휴일/대체휴일인 경우 null
        holiday_types = ['休日(法)', '祝日', '振替(法)', '休日', '振替(休)']
        if self.work_type in holiday_types:
            self.deduction_hours = None
            return
        
        # 기준 근무시간에서 실제 근무시간을 뺀 값
        standard_hours = self.standard_work_hours
        deduction = standard_hours - self.regular_work_hours
        
        # 반차인 경우 추가로 4시간 공제
        if self.work_type == '有給(半)':
            deduction += 4.0
        
        self.deduction_hours = max(0.0, deduction)
    
    def _calculate_overtime_hours(self):
        """잔업시간 및 심야시간 계산"""
        # start_time과 end_time 중 하나라도 없으면 null
        if not self.start_time or not self.end_time:
            self.overtime_hours = None
            self.late_night_overtime_hours = None
            return
        
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        
        # 다음날로 넘어가는 경우 처리
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        # 휴일/공휴일/대체휴일인 경우: 전체 근무시간이 잔업시간
        holiday_types = ['休日(法)', '祝日', '振替(法)', '休日', '振替(休)']
        if self.work_type in holiday_types:
            # 전체 근무시간 계산 (분 단위)
            total_work_minutes = (end_dt - start_dt).total_seconds() / 60
            
            # 점심시간 공제 (12:00~12:00+lunch_break_hours)
            lunch_start = datetime.combine(self.date, time(12, 0))
            lunch_end = datetime.combine(self.date, time(12, 0)) + timedelta(minutes=self.break_minutes)
            
            if lunch_start < end_dt and lunch_end > start_dt:
                overlap_start = max(lunch_start, start_dt)
                overlap_end = min(lunch_end, end_dt)
                total_work_minutes -= (overlap_end - overlap_start).total_seconds() / 60
            
            # 저녁 휴게시간 공제 (19:30~20:00, 22:00~22:30)
            dinner_break1_start = datetime.combine(self.date, time(19, 30))
            dinner_break1_end = datetime.combine(self.date, time(20, 0))
            dinner_break2_start = datetime.combine(self.date, time(22, 0))
            dinner_break2_end = datetime.combine(self.date, time(22, 30))
            
            # 첫 번째 저녁 휴게시간 공제
            if dinner_break1_start < end_dt and dinner_break1_end > start_dt:
                overlap_start = max(dinner_break1_start, start_dt)
                overlap_end = min(dinner_break1_end, end_dt)
                total_work_minutes -= (overlap_end - overlap_start).total_seconds() / 60
            
            # 두 번째 저녁 휴게시간 공제
            if dinner_break2_start < end_dt and dinner_break2_end > start_dt:
                overlap_start = max(dinner_break2_start, start_dt)
                overlap_end = min(dinner_break2_end, end_dt)
                total_work_minutes -= (overlap_end - overlap_start).total_seconds() / 60
            
            # 22:30 이후는 심야시간으로 분리
            late_night_start = datetime.combine(self.date, time(22, 30))
            if end_dt > late_night_start:
                # 22:30 이전까지는 잔업시간
                overtime_minutes = (late_night_start - start_dt).total_seconds() / 60
                
                # 점심시간 공제 (잔업시간 부분만)
                if lunch_start < late_night_start and lunch_end > start_dt:
                    overlap_start = max(lunch_start, start_dt)
                    overlap_end = min(lunch_end, late_night_start)
                    overtime_minutes -= (overlap_end - overlap_start).total_seconds() / 60
                
                # 저녁 휴게시간 공제 (잔업시간 부분만)
                if dinner_break1_start < late_night_start and dinner_break1_end > start_dt:
                    overlap_start = max(dinner_break1_start, start_dt)
                    overlap_end = min(dinner_break1_end, late_night_start)
                    overtime_minutes -= (overlap_end - overlap_start).total_seconds() / 60
                
                if dinner_break2_start < late_night_start and dinner_break2_end > start_dt:
                    overlap_start = max(dinner_break2_start, start_dt)
                    overlap_end = min(dinner_break2_end, late_night_start)
                    overtime_minutes -= (overlap_end - overlap_start).total_seconds() / 60
                
                self.overtime_hours = max(0.0, overtime_minutes / 60.0)
                
                # 22:30 이후는 심야시간 계산
                next_day = self.date + timedelta(days=1)
                late_night_end = datetime.combine(next_day, time(6, 0))
                
                if end_dt > late_night_end:
                    late_night_end = end_dt
                
                late_night_minutes = (late_night_end - late_night_start).total_seconds() / 60
                
                # 심야 휴게시간 공제 (00:30~01:00, 03:00~03:30)
                late_break1_start = datetime.combine(next_day, time(0, 30))
                late_break1_end = datetime.combine(next_day, time(1, 0))
                late_break2_start = datetime.combine(next_day, time(3, 0))
                late_break2_end = datetime.combine(next_day, time(3, 30))
                
                if late_break1_start < late_night_end and late_break1_end > late_night_start:
                    overlap_start = max(late_break1_start, late_night_start)
                    overlap_end = min(late_break1_end, late_night_end)
                    late_night_minutes -= (overlap_end - overlap_start).total_seconds() / 60
                
                if late_break2_start < late_night_end and late_break2_end > late_night_start:
                    overlap_start = max(late_break2_start, late_night_start)
                    overlap_end = min(late_break2_end, late_night_end)
                    late_night_minutes -= (overlap_end - overlap_start).total_seconds() / 60
                
                self.late_night_overtime_hours = max(0.0, late_night_minutes / 60.0)
            else:
                # 22:30 이전에 끝나는 경우 전체가 잔업시간
                self.overtime_hours = max(0.0, total_work_minutes / 60.0)
                self.late_night_overtime_hours = 0.0
            
            return
        
        # 일반 근무일의 경우: 기존 로직 유지
        # 18:00 이후 시간 계산
        overtime_start = datetime.combine(self.date, time(18, 0))
        if end_dt <= overtime_start:
            self.overtime_hours = 0.0
            self.late_night_overtime_hours = 0.0
            return
        
        # 잔업시간 계산 (18:00~22:30)
        late_night_start = datetime.combine(self.date, time(22, 30))
        if end_dt <= late_night_start:
            overtime_end = end_dt
        else:
            overtime_end = late_night_start
        
        overtime_minutes = (overtime_end - overtime_start).total_seconds() / 60
        
        # 휴게시간 공제 (19:30~20:00, 22:00~22:30)
        break1_start = datetime.combine(self.date, time(19, 30))
        break1_end = datetime.combine(self.date, time(20, 0))
        break2_start = datetime.combine(self.date, time(22, 0))
        break2_end = datetime.combine(self.date, time(22, 30))
        
        # 첫 번째 휴게시간 공제
        if break1_start < overtime_end and break1_end > overtime_start:
            overlap_start = max(break1_start, overtime_start)
            overlap_end = min(break1_end, overtime_end)
            overtime_minutes -= (overlap_end - overlap_start).total_seconds() / 60
        
        # 두 번째 휴게시간 공제
        if break2_start < overtime_end and break2_end > overtime_start:
            overlap_start = max(break2_start, overtime_start)
            overlap_end = min(break2_end, overtime_end)
            overtime_minutes -= (overlap_end - overlap_start).total_seconds() / 60
        
        self.overtime_hours = max(0.0, overtime_minutes / 60.0)
        
        # 심야시간 계산 (22:30~06:00)
        if end_dt > late_night_start:
            # 다음날 06:00까지
            next_day = self.date + timedelta(days=1)
            late_night_end = datetime.combine(next_day, time(6, 0))
            
            if end_dt > late_night_end:
                late_night_end = end_dt
            
            late_night_minutes = (late_night_end - late_night_start).total_seconds() / 60
            
            # 심야 휴게시간 공제 (00:30~01:00, 03:00~03:30)
            late_break1_start = datetime.combine(next_day, time(0, 30))
            late_break1_end = datetime.combine(next_day, time(1, 0))
            late_break2_start = datetime.combine(next_day, time(3, 0))
            late_break2_end = datetime.combine(next_day, time(3, 30))
            
            # 첫 번째 심야 휴게시간 공제
            if late_break1_start < late_night_end and late_break1_end > late_night_start:
                overlap_start = max(late_break1_start, late_night_start)
                overlap_end = min(late_break1_end, late_night_end)
                late_night_minutes -= (overlap_end - overlap_start).total_seconds() / 60
            
            # 두 번째 심야 휴게시간 공제
            if late_break2_start < late_night_end and late_break2_end > late_night_start:
                overlap_start = max(late_break2_start, late_night_start)
                overlap_end = min(late_break2_end, late_night_end)
                late_night_minutes -= (overlap_end - overlap_start).total_seconds() / 60
            
            self.late_night_overtime_hours = max(0.0, late_night_minutes / 60.0)
        else:
            self.late_night_overtime_hours = 0.0
    
    def _calculate_total_hours(self):
        """소계시간 계산"""
        # end_time과 start_time이 없으면 null
        if not self.end_time or not self.start_time:
            self.total_hours = None
            return
        
        total = 0.0
        
        if self.regular_work_hours is not None:
            total += self.regular_work_hours
        
        if self.overtime_hours is not None:
            total += self.overtime_hours
        
        if self.late_night_overtime_hours is not None:
            total += self.late_night_overtime_hours
        
        self.total_hours = total

@dataclass
class MonthlyData:
    employee_id: int  # 6자리 숫자 사원번호
    year: str
    month: str
    project_name: str
    base_calendar: str
    break_minutes: int
    standard_work_hours: float
    daily_list: List[DailyData] = field(default_factory=list)
    # 계산 필드
    total_work_days: int = 0
    total_overtime: float = 0.0
    # ... 필요에 따라 추가

    def calculate_all_daily_hours(self):
        """모든 일별 근무시간 계산"""
        for daily in self.daily_list:
            # 월별 정보를 일별 데이터에 전달
            daily.break_minutes = self.break_minutes
            daily.standard_work_hours = self.standard_work_hours
            daily.calculate_work_hours()

    @property
    def total_regular_work_hours(self) -> float:
        """상근시간 합계: 휴일(법), 공휴일, 대체(법) 제외한 나머지 날들의 상근시간 합"""
        total = 0.0
        exclude_types = ['休日(法)', '祝日', '振替(法)']
        
        for daily in self.daily_list:
            if (daily.work_type not in exclude_types and 
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
        """잔업시간 합계: 모든 일별 잔업시간의 합"""
        total = 0.0
        
        for daily in self.daily_list:
            if daily.overtime_hours is not None:
                total += daily.overtime_hours
        
        return round(total, 2)

    @property
    def total_late_night_overtime_hours(self) -> float:
        """심야시간 합계: 모든 일별 심야시간의 합"""
        total = 0.0
        
        for daily in self.daily_list:
            if daily.late_night_overtime_hours is not None:
                total += daily.late_night_overtime_hours
        
        return round(total, 2)

    @property
    def total_holiday_work_hours(self) -> float:
        """휴일 근무시간 합계: 법정 휴일(休日(法)、祝日、振替(法))에 일한 잔업시간의 합"""
        total = 0.0
        legal_holiday_types = ['休日(法)', '祝日', '振替(法)']
        
        for daily in self.daily_list:
            if (daily.work_type in legal_holiday_types and 
                daily.overtime_hours is not None):
                total += daily.overtime_hours
        
        return round(total, 2)

    @property
    def holiday_work_hours_night(self) -> float:
        """휴일 심야근무시간 합계: 법정 휴일에 심야근무한 시간의 합"""
        total = 0.0
        legal_holiday_types = ['休日(法)', '祝日', '振替(法)']
        
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
        """출근일: start_time이 입력된 일수"""
        count = sum(1 for d in self.daily_list if d.start_time is not None)
        return round(float(count), 1)

    @property
    def paid_leave_days(self) -> float:
        """연차 유급: 有給(半)=+0.5, 有給=+1, 欠勤=-1, 합산 후 0 미만이면 0"""
        total = 0.0
        for d in self.daily_list:
            if d.work_type == "有給(半)":
                total += 0.5
            elif d.work_type == "有給":
                total += 1.0
            elif d.work_type == "欠勤":
                total -= 1.0
        return round(max(total, 0.0), 1)

    @property
    def special_paid_leave_days(self) -> float:
        """특별 유급: 特別休暇 카운트"""
        count = sum(1 for d in self.daily_list if d.work_type == "特別休暇")
        return round(float(count), 1)

    @property
    def unpaid_leave_days(self) -> float:
        """무급일: 代休이면서 date != alternative_work_date인 경우만 카운트"""
        count = 0
        for d in self.daily_list:
            if d.work_type == "代休":
                # alternative_work_date가 없거나, date와 다를 때만 +1
                if not d.alternative_work_date or d.date != d.alternative_work_date:
                    count += 1
        return round(float(count), 1)
