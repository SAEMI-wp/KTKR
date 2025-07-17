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
    
    # 月情報 (基本値 = 0)
    break_minutes: int = 0  
    standard_work_hours: float = 0.0
    
    # 計算 (基本値 = None)
    regular_work_hours: Optional[float] = None          # 常動
    deduction_hours: Optional[float] = None             # 控除
    overtime_hours: Optional[float] = None              # 残業
    late_night_overtime_hours: Optional[float] = None   # 深夜
    total_hours: Optional[float] = None                 # 小計
    
    def calculate_work_hours(self):
        """근무시간 계산 메서드"""
        self._calculate_regular_work_hours()
        self._calculate_deduction_hours()
        self._calculate_overtime_hours()
        self._calculate_total_hours()
    
    def _calculate_regular_work_hours(self):
        """常動時間を計算 (9:00~18:00, 점심 12:00~13:00 제외)"""
        # 출근/퇴근시간이 없거나 같으면 null
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.regular_work_hours = None
            return
        # 休日, 休日(法), 祝日인 경우 null
        if self.work_type in ['休日', '休日(法)', '祝日']:
            self.regular_work_hours = None
            return

        # 기준 근무시간 구간: 9:00~18:00 (점심 12:00~13:00)
        work_start = datetime.combine(self.date, time(9, 0))
        work_lunch_start = datetime.combine(self.date, time(12, 0))
        work_lunch_end = work_lunch_start + timedelta(minutes=self.break_minutes)
        work_end = datetime.combine(self.date, time(18, 0))

        # 실제 근무 구간
        actual_start = datetime.combine(self.date, self.start_time)
        actual_end = datetime.combine(self.date, self.end_time)
        if actual_end < actual_start:
            actual_end += timedelta(days=1)

        # 기준 근무시간 내에서 실제 일한 시간만 계산
        # 오전 근무 (9:00~12:00)
        morning_start = max(actual_start, work_start)
        morning_end = min(actual_end, work_lunch_start)
        morning_minutes = max(0, (morning_end - morning_start).total_seconds() / 60)

        # 오후 근무 (13:00~18:00)
        afternoon_start = max(actual_start, work_lunch_end)
        afternoon_end = min(actual_end, work_end)
        afternoon_minutes = max(0, (afternoon_end - afternoon_start).total_seconds() / 60)

        total_minutes = morning_minutes + afternoon_minutes
        self.regular_work_hours = round(total_minutes / 60.0, 2)

    def _calculate_deduction_hours(self):
        """控除時間を計算 (공제시간 = 8.0 - 常動)"""
        # regular_work_hours가 비어있으면 null
        if self.regular_work_hours is None:
            self.deduction_hours = None
            return
        # 출근/퇴근시간이 같으면 null
        if self.start_time is not None and self.end_time is not None and self.start_time == self.end_time:
            self.deduction_hours = None
            return
        # 休日, 休日(法), 祝日인 경우 null
        if self.work_type in ['休日', '休日(法)', '祝日']:
            self.deduction_hours = None
            return

        # 기준 근무시간(9:00~18:00, 점심 1시간 제외) = 8.0
        standard_hours = 8.0
        deduction = standard_hours - self.regular_work_hours
        self.deduction_hours = round(max(0.0, deduction), 2)
    
    # --- ここから 休日用の残業・深夜時間計算関数を追加予定 ---
    # 休日用 残業時間計算
    def _calculate_overtime_hours_for_holiday(self, start_dt, end_dt):
        """
        休日の残業時間を計算する関数
        22:00~翌6:30を除いた時間を残業時間とする
        """
        # 深夜区間定義
        night1_start = datetime.combine(self.date, time(22, 0))
        next_day = self.date + timedelta(days=1)
        night1_end = datetime.combine(next_day, time(6, 30))

        # 残業区間: start_dt~end_dt から深夜区間を除いた部分
        overtime_minutes = 0.0
        current_start = start_dt
        current_end = end_dt

        # 22:00より前の部分
        if current_start < night1_start:
            overtime_end = min(current_end, night1_start)
            if current_start < overtime_end:
                overtime_minutes += (overtime_end - current_start).total_seconds() / 60.0
        # 翌6:30より後の部分
        if current_end > night1_end:
            overtime_start = max(current_start, night1_end)
            if overtime_start < current_end:
                overtime_minutes += (current_end - overtime_start).total_seconds() / 60.0
        return round(overtime_minutes / 60.0, 2)

    # 休日用 深夜時間計算
    def _calculate_late_night_overtime_hours_for_holiday(self, start_dt, end_dt):
        """
        休日の深夜時間を計算する関数
        22:00~翌6:30のうち、休憩(00:30~01:00, 03:00~03:30)を除いた実働時間
        """
        night1_start = datetime.combine(self.date, time(22, 0))
        next_day = self.date + timedelta(days=1)
        night1_end = datetime.combine(next_day, time(6, 30))

        # 深夜区間と実際の勤務区間の重なり
        overlap_start = max(start_dt, night1_start)
        overlap_end = min(end_dt, night1_end)
        late_night_minutes = 0.0
        if overlap_start < overlap_end:
            late_night_minutes = (overlap_end - overlap_start).total_seconds() / 60.0
            # 休憩1: 00:30~01:00
            break1_start = datetime.combine(next_day, time(0, 30))
            break1_end = datetime.combine(next_day, time(1, 0))
            if break1_start < overlap_end and break1_end > overlap_start:
                rest_start = max(break1_start, overlap_start)
                rest_end = min(break1_end, overlap_end)
                late_night_minutes -= (rest_end - rest_start).total_seconds() / 60.0
            # 休憩2: 03:00~03:30
            break2_start = datetime.combine(next_day, time(3, 0))
            break2_end = datetime.combine(next_day, time(3, 30))
            if break2_start < overlap_end and break2_end > overlap_start:
                rest_start = max(break2_start, overlap_start)
                rest_end = min(break2_end, overlap_end)
                late_night_minutes -= (rest_end - rest_start).total_seconds() / 60.0
        return round(max(0.0, late_night_minutes) / 60.0, 2)
    # --- ここまで 休日用の残業・深夜時間計算関数を追加予定 ---

    def _calculate_overtime_hours(self):
        """残業時間および深夜時間を計算"""
        # 출근/퇴근시간이 없거나 같으면 null
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.overtime_hours = None
            self.late_night_overtime_hours = None
            return
        # 休日, 休日(法), 祝日인 경우: 전체 근무시간을 残業・深夜로 분離
        if self.work_type in ['休日', '休日(法)', '祝日']:
            start_dt = datetime.combine(self.date, self.start_time)
            end_dt = datetime.combine(self.date, self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            # ここで休日用の残業・深夜時間計算関数を呼び出す
            self.overtime_hours = self._calculate_overtime_hours_for_holiday(start_dt, end_dt)
            self.late_night_overtime_hours = self._calculate_late_night_overtime_hours_for_holiday(start_dt, end_dt)
            return
        
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        
        # 다음날로 넘어가는 경우 처리
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        # 휴일/공휴일/대체휴일인 경우: 전체 근무시간이 잔업시간
        holiday_types = ['休日(法)', '祝日', '振替', '休日'] #'振替(休)'
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
        
        # 심야시간 계산 (22:00~06:30, 예외구간 포함)
        if end_dt > late_night_start:
            next_day = self.date + timedelta(days=1)
            # 심야구간 정의
            night1_start = datetime.combine(self.date, time(22, 0))
            night1_end = datetime.combine(next_day, time(3, 0))
            break_start = night1_end
            break_end = datetime.combine(next_day, time(4, 0))
            bonus_start = break_end
            bonus_end = datetime.combine(next_day, time(4, 30))
            night2_start = bonus_end
            night2_end = datetime.combine(next_day, time(6, 30))

            total_night_hours = 0.0
            # 1. 22:00~03:00 실제 일한 시간 (단, 22:00~22:30은 휴게시간)
            rest1_start = datetime.combine(self.date, time(22, 0))
            rest1_end = datetime.combine(self.date, time(22, 30))
            # 22:00~22:30 제외
            work_night1_start = datetime.combine(self.date, time(22, 30))
            work_night1_end = night1_end

            # 22:30~23:00 실제 일한 시간
            overlap1_start = max(start_dt, work_night1_start)
            overlap1_end = min(end_dt, work_night1_end)
            if overlap1_start < overlap1_end:
                total_night_hours += (overlap1_end - overlap1_start).total_seconds() / 3600.0
            # 2. 03:00~04:00 무조건 쉬는 시간(제외)
            # 3. 04:00~04:30 1분이라도 일하면 1.0
            overlap_bonus_start = max(start_dt, bonus_start)
            overlap_bonus_end = min(end_dt, bonus_end)
            if overlap_bonus_start < overlap_bonus_end:
                total_night_hours += 1.0
            # 4. 04:30~06:30 30분 단위로 0.5씩
            overlap2_start = max(start_dt, night2_start)
            overlap2_end = min(end_dt, night2_end)
            if overlap2_start < overlap2_end:
                minutes = (overlap2_end - overlap2_start).total_seconds() / 60.0
                half_hours = int(minutes // 30)
                total_night_hours += half_hours * 0.5
            self.late_night_overtime_hours = total_night_hours
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
        """휴일 근무시간 합계: 법정 휴일(休日(法)、祝日、振替)에 일한 잔업시간의 합"""
        total = 0.0
        legal_holiday_types = ['休日(法)', '祝日', '振替']
        
        for daily in self.daily_list:
            if (daily.work_type in legal_holiday_types and 
                daily.overtime_hours is not None):
                total += daily.overtime_hours
        
        return round(total, 2)

    @property
    def holiday_work_hours_night(self) -> float:
        """휴일 심야근무시간 합계: 법정 휴일에 심야근무한 시간의 합"""
        total = 0.0
        legal_holiday_types = ['休日(法)', '祝日', '振替']
        
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
