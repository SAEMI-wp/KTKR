from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, time, datetime, timedelta

@dataclass
class DailyData:
    date: date
    work_type: Optional[str]
    start_time: Optional[time]                          # 開始時間
    end_time: Optional[time]                            # 終了時間
    alternative_work_date: Optional[date] = None        # 代休/振替
    notes: Optional[str] = None                         # 備考
    is_required: bool = False                           # 必須
    is_confirmed: bool = False                          # 確認
    
    break_minutes: int = 0                              # 昼休み時間(45, 60)
    standard_work_hours: float = 0.0                    # 標準勤務時間(7.5, 8)
    
    regular_work_hours: Optional[float] = None          # 常勤
    deduction_hours: Optional[float] = None             # 控除
    overtime_hours: Optional[float] = None              # 残業
    late_night_overtime_hours: Optional[float] = None   # 深夜
    total_hours: Optional[float] = None                 # 合計
    jk_overtime: float = 0.0                            # 常勤超過時間（計算用）

    def calculate_work_hours(self):
        """勤務時間計算"""
        self._calculate_regular_work_hours()    #常勤
        self._calculate_deduction_hours()       #控除
        self._calculate_overtime_hours()        #残業
        self._calculate_late_night_hours()      #深夜
        self._calculate_total_hours()           #合計

    def _get_overlap_minutes(self, period_start, period_end, check_start, check_end):
        """두 시간대의 겹치는 시간을 분으로 반환"""
        overlap_start = max(period_start, check_start)
        overlap_end = min(period_end, check_end)
        if overlap_start < overlap_end:
            return (overlap_end - overlap_start).total_seconds() / 60.0
        return 0.0

    def _get_work_value_by_time(self, time_obj: time) -> float:
        """時間による作業値計算（新しいロジック）"""
        hour = time_obj.hour
        minute = time_obj.minute
        
        # 11:50以前の時間帯処理（共通）
        if hour < 11 or (hour == 11 and minute < 50):
            return self._get_work_value_before_1150(hour, minute)
        
        # 11:50以降の時間帯処理（break_minutes別）
        else:
            return self._get_work_value_after_1150(hour, minute)
    
    def _get_work_value_before_1150(self, hour: int, minute: int) -> float:
        """11:50以前の時間値計算"""
        # 07:35以前 → 0
        if hour < 7 or (hour == 7 and minute < 35):
            return 0.0
        
        # 07:35~08:20 → 8.75
        elif hour == 7 and minute >= 35:
            return 8.75
        elif hour == 8 and minute < 20:
            return 8.75
            
        # 08:20~08:35 → 8.5
        elif hour == 8 and 20 <= minute < 35:
            return 8.5
            
        # 08:35~08:50 → 8.25
        elif hour == 8 and 35 <= minute < 50:
            return 8.25
            
        # 08:50~09:05 → 8.0
        elif hour == 8 and minute >= 50:
            return 8.0
        elif hour == 9 and minute < 5:
            return 8.0
            
        # 09:05~09:20 → 7.75
        elif hour == 9 and 5 <= minute < 20:
            return 7.75
            
        # 09:20~09:35 → 7.5
        elif hour == 9 and 20 <= minute < 35:
            return 7.5
            
        # 09:35~09:50 → 7.25
        elif hour == 9 and 35 <= minute < 50:
            return 7.25
            
        # 09:50~10:05 → 7.0
        elif hour == 9 and minute >= 50:
            return 7.0
        elif hour == 10 and minute < 5:
            return 7.0
            
        # 10:05~10:20 → 6.75
        elif hour == 10 and 5 <= minute < 20:
            return 6.75
            
        # 10:20~10:35 → 6.5
        elif hour == 10 and 20 <= minute < 35:
            return 6.5
            
        # 10:35~10:50 → 6.25
        elif hour == 10 and 35 <= minute < 50:
            return 6.25
            
        # 10:50~11:05 → 6.0
        elif hour == 10 and minute >= 50:
            return 6.0
        elif hour == 11 and minute < 5:
            return 6.0
            
        # 11:05~11:20 → 5.75
        elif hour == 11 and 5 <= minute < 20:
            return 5.75
            
        # 11:20~11:35 → 5.5
        elif hour == 11 and 20 <= minute < 35:
            return 5.5
            
        # 11:35~11:50 → 5.25
        elif hour == 11 and 35 <= minute < 50:
            return 5.25
            
        else:
            return 0.0
    
    def _get_work_value_after_1150(self, hour: int, minute: int) -> float:
        """11:50以降の時間値計算（break_minutes別）"""
        if self.break_minutes == 60:
            return self._get_work_value_after_1150_60min(hour, minute)
        elif self.break_minutes == 45:
            return self._get_work_value_after_1150_45min(hour, minute)
        else:
            return 0.0
    
    def _get_work_value_after_1150_60min(self, hour: int, minute: int) -> float:
        """11:50以降60分休憩の時間値計算"""
        # 11:50~13:05 → 5.0
        if hour == 11 and minute >= 50:
            return 5.0
        elif hour == 12:
            return 5.0
        elif hour == 13 and minute < 5:
            return 5.0
            
        # 13:05~13:20 → 4.75
        elif hour == 13 and 5 <= minute < 20:
            return 4.75
            
        # 13:20~13:35 → 4.5
        elif hour == 13 and 20 <= minute < 35:
            return 4.5
            
        # 13:35~13:50 → 4.25
        elif hour == 13 and 35 <= minute < 50:
            return 4.25
            
        # 13:50~14:05 → 4.0
        elif hour == 13 and minute >= 50:
            return 4.0
        elif hour == 14 and minute < 5:
            return 4.0
            
        # 14:05~14:20 → 3.75
        elif hour == 14 and 5 <= minute < 20:
            return 3.75
            
        # 14:20~14:35 → 3.5
        elif hour == 14 and 20 <= minute < 35:
            return 3.5
            
        # 14:35~14:50 → 3.25
        elif hour == 14 and 35 <= minute < 50:
            return 3.25
            
        # 14:50~15:05 → 3.0
        elif hour == 14 and minute >= 50:
            return 3.0
        elif hour == 15 and minute < 5:
            return 3.0
            
        # 15:05~15:20 → 2.75
        elif hour == 15 and 5 <= minute < 20:
            return 2.75
            
        # 15:20~15:35 → 2.5
        elif hour == 15 and 20 <= minute < 35:
            return 2.5
            
        # 15:35~15:50 → 2.25
        elif hour == 15 and 35 <= minute < 50:
            return 2.25
            
        # 15:50~16:05 → 2.0
        elif hour == 15 and minute >= 50:
            return 2.0
        elif hour == 16 and minute < 5:
            return 2.0
            
        # 16:05~16:20 → 1.75
        elif hour == 16 and 5 <= minute < 20:
            return 1.75
            
        # 16:20~16:35 → 1.5
        elif hour == 16 and 20 <= minute < 35:
            return 1.5
            
        # 16:35~16:50 → 1.25
        elif hour == 16 and 35 <= minute < 50:
            return 1.25
            
        # 16:50~17:05 → 1.0
        elif hour == 16 and minute >= 50:
            return 1.0
        elif hour == 17 and minute < 5:
            return 1.0
            
        # 17:05~17:20 → 0.75
        elif hour == 17 and 5 <= minute < 20:
            return 0.75
            
        # 17:20~17:35 → 0.5
        elif hour == 17 and 20 <= minute < 35:
            return 0.5
            
        # 17:35~17:50 → 0.25
        elif hour == 17 and 35 <= minute < 50:
            return 0.25
            
        # 17:50以降 → 0.0
        else:
            return 0.0
    
    def _get_work_value_after_1150_45min(self, hour: int, minute: int) -> float:
        """11:50以降45分休憩の時間値計算"""
        # 11:50~12:50 → 5.0
        if hour == 11 and minute >= 50:
            return 5.0
        elif hour == 12 and minute < 50:
            return 5.0
            
        # 12:50~13:05 → 4.75
        elif hour == 12 and minute >= 50:
            return 4.75
        elif hour == 13 and minute < 5:
            return 4.75
            
        # 13:05~13:20 → 4.5
        elif hour == 13 and 5 <= minute < 20:
            return 4.5
            
        # 13:20~13:35 → 4.25
        elif hour == 13 and 20 <= minute < 35:
            return 4.25
            
        # 13:35~13:50 → 4.0
        elif hour == 13 and 35 <= minute < 50:
            return 4.0
            
        # 13:50~14:05 → 3.75
        elif hour == 13 and minute >= 50:
            return 3.75
        elif hour == 14 and minute < 5:
            return 3.75
            
        # 14:05~14:20 → 3.5
        elif hour == 14 and 5 <= minute < 20:
            return 3.5
            
        # 14:20~14:35 → 3.25
        elif hour == 14 and 20 <= minute < 35:
            return 3.25
            
        # 14:35~14:50 → 3.0
        elif hour == 14 and 35 <= minute < 50:
            return 3.0
            
        # 14:50~15:05 → 2.75
        elif hour == 14 and minute >= 50:
            return 2.75
        elif hour == 15 and minute < 5:
            return 2.75
            
        # 15:05~15:20 → 2.5
        elif hour == 15 and 5 <= minute < 20:
            return 2.5
            
        # 15:20~15:35 → 2.25
        elif hour == 15 and 20 <= minute < 35:
            return 2.25
            
        # 15:35~15:50 → 2.0
        elif hour == 15 and 35 <= minute < 50:
            return 2.0
            
        # 15:50~16:05 → 1.75
        elif hour == 15 and minute >= 50:
            return 1.75
        elif hour == 16 and minute < 5:
            return 1.75
            
        # 16:05~16:20 → 1.5
        elif hour == 16 and 5 <= minute < 20:
            return 1.5
            
        # 16:20~16:35 → 1.25
        elif hour == 16 and 20 <= minute < 35:
            return 1.25
            
        # 16:35~16:50 → 1.0
        elif hour == 16 and 35 <= minute < 50:
            return 1.0
            
        # 16:50~17:05 → 0.75
        elif hour == 16 and minute >= 50:
            return 0.75
        elif hour == 17 and minute < 5:
            return 0.75
            
        # 17:05~17:20 → 0.5
        elif hour == 17 and 5 <= minute < 20:
            return 0.5
            
        # 17:20以降 → 0.25（固定値）
        else:
            return 0.25

    def _get_overtime_value_by_time(self, time_obj: time) -> float:
        """残業時間値計算"""
        hour = time_obj.hour
        minute = time_obj.minute
        
        # 18:30以前 → 0
        if hour < 18 or (hour == 18 and minute < 30):
            return 0.0
        
        # 18:30~19:00 → 0.5
        elif hour == 18 and minute >= 30:
            return 0.5
            
        # 19:00~19:30 → 1
        elif hour == 19 and minute < 30:
            return 1.0
            
        # 19:30~20:30 → 1.5（休憩時間）
        elif hour == 19 and minute >= 30:
            return 1.5
        elif hour == 20 and minute < 30:
            return 1.5
            
        # 20:30~21:00 → 2
        elif hour == 20 and minute >= 30:
            return 2.0
            
        # 21:00~21:30 → 2.5
        elif hour == 21 and minute < 30:
            return 2.5
            
        # 21:30~22:00 → 3
        elif hour == 21 and minute >= 30:
            return 3.0
            
        # 22:00~6:30 → 3.5
        elif hour >= 22 or hour < 6 or (hour == 6 and minute < 30):
            return 3.5
            
        # 6:30~9:00 → 30分ずつ増加
        elif hour == 6 and minute >= 30:
            return 4.0  # 6:30~7:00
        elif hour == 7 and minute < 30:
            return 4.5  # 7:00~7:30
        elif hour == 7 and minute >= 30:
            return 5.0  # 7:30~8:00
        elif hour == 8 and minute < 30:
            return 5.5  # 8:00~8:30
        elif hour == 8 and minute >= 30:
            return 6.0  # 8:30~9:00
            
        # 9:01~18:30 → 0
        else:
            return 0.0

    def _get_late_night_value_by_time(self, time_obj: time) -> float:
        """深夜時間値計算"""
        hour = time_obj.hour
        minute = time_obj.minute
        
        # 9:01~23:00 → 0
        if (hour > 9) and (hour < 23):
            return 0.0
        elif hour == 9 and minute > 0:
            return 0.0
            
        # 23:00~23:30 → 0.5
        elif hour == 23 and minute < 30:
            return 0.5
            
        # 23:30~24:00 → 1
        elif hour == 23 and minute >= 30:
            return 1.0
            
        # 0:00~0:30 → 1.5
        elif hour == 0 and minute < 30:
            return 1.5
            
        # 0:30~1:00 → 2
        elif hour == 0 and minute >= 30:
            return 2.0
            
        # 1:00~1:30 → 2.5
        elif hour == 1 and minute < 30:
            return 2.5
            
        # 1:30~2:00 → 3
        elif hour == 1 and minute >= 30:
            return 3.0
            
        # 2:00~2:30 → 3.5
        elif hour == 2 and minute < 30:
            return 3.5
            
        # 2:30~3:00 → 4
        elif hour == 2 and minute >= 30:
            return 4.0
            
        # 3:00~4:00 → 4.5（休憩時間）
        elif hour == 3:
            return 4.5
            
        # 4:00~4:30 → 5
        elif hour == 4 and minute < 30:
            return 5.0
            
        # 4:30~5:00 → 5.5
        elif hour == 4 and minute >= 30:
            return 5.5
            
        # 5:00~5:30 → 6
        elif hour == 5 and minute < 30:
            return 6.0
            
        # 5:30~6:00 → 6.5
        elif hour == 5 and minute >= 30:
            return 6.5
            
        # 6:00~9:00 → 7
        elif (hour >= 6 and hour <= 9):
            return 7.0
            
        # 9:00以降 → 0
        else:
            return 0.0

    def _calculate_regular_work_hours(self):
        """常勤時間計算"""
        # 1. 出勤時間と退勤時間が両方存在するか確認
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.regular_work_hours = None
            return
        
        # 2. work_typeが計算対象外のものか確認
        exclude_types = ['休日(法)', '祝日', '振替(法)', '休日', '振替(休)', '代休(休)']
        if self.work_type in exclude_types:
            self.regular_work_hours = None
            return

        # 3. 計算用変数設定
        start_value: float = 0.0
        end_value: float = 0.0
        jyokin_work: float = 0.0
        
        # 4. start_value計算
        start_value = self._get_work_value_by_time(self.start_time)
        
        # 5. end_value計算
        end_value = self._get_work_value_by_time(self.end_time)
        
        # 6. jyokin_work計算
        jyokin_work = start_value - end_value
        
        # 7. regular_work_hours設定（standard_work_hoursとjyokin_workの小さい方）
        self.regular_work_hours = round(min(jyokin_work, self.standard_work_hours), 2)

    def _calculate_deduction_hours(self):
        """控除時間計算"""
        # 1. regular_work_hoursがnullの場合、nullを返す
        if self.regular_work_hours is None:
            self.deduction_hours = None
            return
        
        # 2. 計算用変数設定
        start_value = self._get_work_value_by_time(self.start_time)
        end_value = self._get_work_value_by_time(self.end_time)
        jyokin_work = start_value - end_value
        
        # 3. 有給(半)の場合特別処理
        if self.work_type == "有給(半)":
            # standard_work_hours - regular_work_hours - 4
            deduction = self.standard_work_hours - self.regular_work_hours - 4
        else:
            # standard_work_hours - jyokin_work
            deduction = self.standard_work_hours - jyokin_work
        
        # 4. 結果が負の場合は0、正の場合はそのまま設定
        if deduction < 0:
            self.deduction_hours = 0.0
            # 5. jk_overtime計算用変数（後でovertime_hoursに加算）
            jk_overtime = abs(deduction)
            # この値は後でovertime_hours計算時に使用される
            self.jk_overtime = jk_overtime
        else:
            self.deduction_hours = round(deduction, 2)
            self.jk_overtime = 0.0

    def _calculate_overtime_hours(self):
        """残業時間計算"""
        # 1. start_timeまたはend_timeがNULL、またはstart_timeとend_timeが同じ場合、NULLを返す
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.overtime_hours = None
            return
        
        # 2. 実行条件チェック: 退勤時間が18:00以降または出勤時間が9:00以前
        if not (self.end_time.hour >= 18 or self.end_time.hour < 9):
            self.overtime_hours = self.jk_overtime
            return
        
        # 3. 計算用変数設定
        start_value = 0.0
        end_value = 0.0
        
        # 4. start_value計算
        if self.start_time.hour < 18 or (self.start_time.hour == 18 and self.start_time.minute < 30):
            start_value = 0.0
        else:
            start_value = self._get_overtime_value_by_time(self.start_time)
        
        # 5. end_value計算
        end_value = self._get_overtime_value_by_time(self.end_time)
        
        # 6. 残業時間計算
        overtime_value = end_value - start_value + self.jk_overtime
        
        # 7. break_minutes=45かつ退勤時間が18:00超過時は0.5加算
        if self.break_minutes == 45 and self.start_time.hour < 18 and (self.end_time.hour > 18 or (self.end_time.hour == 18 and self.end_time.minute > 0) or self.end_time.hour < self.start_time.hour):
            overtime_value += 0.5
        
        self.overtime_hours = round(max(0.0, overtime_value), 2)
        
    def _calculate_late_night_hours(self):
        """深夜時間計算"""
        # 1. start_timeまたはend_timeがNULL、またはstart_timeとend_timeが同じ場合、NULLを返す
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.late_night_overtime_hours = None
            return
        
        # 2. 実行条件チェック: 退勤時間が22:30以降または出勤時間>退勤時間（日付変更）
        date_changed = self.start_time > self.end_time
        late_end_time = (self.end_time.hour > 22) or (self.end_time.hour == 22 and self.end_time.minute >= 30)
        
        if not (late_end_time or date_changed):
            self.late_night_overtime_hours = 0.0
            return
        
        # 3. 計算用変数設定
        start_value = 0.0
        end_value = 0.0
        
        # 4. start_value計算
        if self.start_time.hour < 23:
            start_value = 0.0
        else:
            start_value = self._get_late_night_value_by_time(self.start_time)
        
        # 5. end_value計算
        end_value = self._get_late_night_value_by_time(self.end_time)
        
        # 6. 深夜時間計算
        late_night_value = end_value - start_value
        
        self.late_night_overtime_hours = round(max(0.0, late_night_value), 2)

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
            daily.base_calendar = self.base_calendar
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
        """無給日: 代休(勤)で、alternative_work_dateの年または月がdateと異なる場合のみカウント"""
        count = 0
        for d in self.daily_list:
            if d.work_type == "代休(勤)":
                if d.alternative_work_date:
                    if (d.date.year != d.alternative_work_date.year) or (d.date.month != d.alternative_work_date.month):
                        count += 1
                else:
                    # alternative_work_dateがない時もカウント
                    count += 1
        return round(float(count), 1)
