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

    def _get_time_value(self, time_obj, break_minutes):
        """常勤時間計算の関数"""
        # 時間を小数点形式に変換 (例: 9:30 -> 9.50)
        hour = time_obj.hour
        minute = time_obj.minute
        time_decimal = hour + minute / 60.0
        
        if break_minutes == 60:
            return self._get_time_value_60min(time_decimal)
        elif break_minutes == 45:
            return self._get_time_value_45min(time_decimal)
        else:
            # デフォルト値 (必要に応じて他のbreak_minutes値を追加)
            return 0.0

    def _get_time_value_common(self, time_decimal):
        """共通時間-値マッピング (0:00 ~ 11:50まで)"""
        # 0:00 ~ 7:34 = 0.0
        if time_decimal < 7.567:  # 7:34 = 7.567
            return 0.0
        
        # 7:35 ~ 8:19 = 8.75
        elif 7.583 <= time_decimal < 8.317:  # 7:35 ~ 8:19
            return 8.75
        
        # 8:20 ~ 11:50 = 15分間隔で0.25ずつ減少
        elif 8.333 <= time_decimal < 11.833:  # 8:20 ~ 11:50
            # 8:20から始まり、15分ごとに0.25ずつ減少
            # 8:20=8.5, 8:35=8.25, 8:50=8.0, ..., 11:35=5.5
            minutes_from_820 = (time_decimal - 8.333) * 60
            quarter_hours = int(minutes_from_820 / 15)
            return round(8.5 - quarter_hours * 0.25, 2)
        
        # 11:50から = 5.0
        elif 11.833 <= time_decimal < 12.0:
            return 5.0
        
        # その他の時間: 0.0
        else:
            return 0.0

    def _get_time_value_60min(self, time_decimal):
        """break_minutesが60の場合の時間-値マッピング"""
        # 共通部分の処理 (0:00 ~ 11:50)
        if time_decimal < 12.0:
            return self._get_time_value_common(time_decimal)
        
        # 12:00 ~ 13:04 = 5.0
        elif 12.0 <= time_decimal < 13.067:  # 12:00 ~ 13:04
            return 5.0
        
        # 13:05から 15分間隔で0.25ずつ減少
        elif 13.083 <= time_decimal < 17.833:  # 13:05 ~ 17:50
            minutes_from_1305 = (time_decimal - 13.083) * 60
            quarter_hours = int(minutes_from_1305 / 15)
            return round(5.0 - quarter_hours * 0.25, 2)
        
        # 17:50 以降 = 0.0
        elif time_decimal >= 17.833:
            return 0.0
        
        # その他の時間: 0.0
        else:
            return 0.0

    def _get_time_value_45min(self, time_decimal):
        """break_minutesが45の場合の時間-値マッピング"""
        # 共通部分の処理 (0:00 ~ 11:50)
        if time_decimal < 12.0:
            return self._get_time_value_common(time_decimal)
        
        # 12:00 ~ 12:49 = 5.0
        elif 12.0 <= time_decimal < 12.817:  # 12:00 ~ 12:49
            return 5.0
        
        # 12:50から 15分間隔で0.25ずつ減少
        elif 12.833 <= time_decimal < 17.333:  # 12:50 ~ 17:20
            minutes_from_1250 = (time_decimal - 12.833) * 60
            quarter_hours = int(minutes_from_1250 / 15)
            return round(5.0 - quarter_hours * 0.25, 2)
        
        # 17:20 以降 = 0.25
        elif time_decimal >= 17.333:
            return 0.25
        
        # その他の時間: 0.0
        else:
            return 0.0

    def _get_overtime_value(self, time_obj):
        """잔업값을 반환하는 함수 (24시간을 1로 하는 방식)"""
        # 시간을 소수점 형태로 변환 (예: 9:30 -> 9.5, 18:00 -> 18.0)
        hour = time_obj.hour
        minute = time_obj.minute
        time_decimal = hour + minute / 60.0
        
        # 18:00 ~ 18:30 = 0
        if 18.0 <= time_decimal < 18.5:
            return 0.0
        
        # 18:30 ~ 19:00 = 0.5
        elif 18.5 <= time_decimal < 19.0:
            return 0.5
        
        # 19:00 ~ 19:30 = 1
        elif 19.0 <= time_decimal < 19.5:
            return 1.0
        
        # 19:30 ~ 20:00 = 1.5 (19:30~20:00 휴식)
        elif 19.5 <= time_decimal < 20.0:
            return 1.5
        
        # 20:00 ~ 20:30 = 1.5
        elif 20.0 <= time_decimal < 20.5:
            return 1.5
        
        # 20:30 ~ 21:00 = 2
        elif 20.5 <= time_decimal < 21.0:
            return 2.0
        
        # 21:00 ~ 21:30 = 2.5
        elif 21.0 <= time_decimal < 21.5:
            return 2.5
        
        # 21:30 ~ 22:00 = 3
        elif 21.5 <= time_decimal < 22.0:
            return 3.0
        
        # 22:00 ~ 6:30 = 3.5 (22:00~22:30 휴식)
        elif 22.0 <= time_decimal < 24.0 or 0.0 <= time_decimal < 6.5:
            return 3.5
        
        # 6:30 ~ 7:00 = 4
        elif 6.5 <= time_decimal < 7.0:
            return 4.0
        
        # 7:00 ~ 7:30 = 4.5
        elif 7.0 <= time_decimal < 7.5:
            return 4.5
        
        # 7:30 ~ 8:00 = 5
        elif 7.5 <= time_decimal < 8.0:
            return 5.0
        
        # 8:00 ~ 8:30 = 5.5
        elif 8.0 <= time_decimal < 8.5:
            return 5.5
        
        # 8:30 ~ 9:00 = 6
        elif 8.5 <= time_decimal < 9.0:
            return 6.0
        
        # 9:00 ~ 9:35 = 6.5
        elif 9.0 <= time_decimal < 9.583:
            return 6.5
        
        # 그 외 시간: 0
        else:
            return 0.0

    def _get_late_night_value(self, time_obj):
        """심야값을 반환하는 함수 (24시간을 1로 하는 방식)"""
        # 시간을 소수점 형태로 변환 (예: 23:30 -> 23.5, 0:00 -> 0.0)
        hour = time_obj.hour
        minute = time_obj.minute
        time_decimal = hour + minute / 60.0
        
        # 23:00 ~ 23:30 = 0.5
        if 23.0 <= time_decimal < 23.5:
            return 0.5
        
        # 23:30 ~ 0:00 = 1
        elif 23.5 <= time_decimal < 24.0:
            return 1.0
        
        # 0:00 ~ 0:30 = 1.5
        elif 0.0 <= time_decimal < 0.5:
            return 1.5
        
        # 0:30 ~ 1:00 = 2
        elif 0.5 <= time_decimal < 1.0:
            return 2.0
        
        # 1:00 ~ 1:30 = 2.5
        elif 1.0 <= time_decimal < 1.5:
            return 2.5
        
        # 1:30 ~ 2:00 = 3
        elif 1.5 <= time_decimal < 2.0:
            return 3.0
        
        # 2:00 ~ 2:30 = 3.5
        elif 2.0 <= time_decimal < 2.5:
            return 3.5
        
        # 2:30 ~ 3:00 = 4
        elif 2.5 <= time_decimal < 3.0:
            return 4.0
        
        # 3:00 ~ 4:00 = 4.5
        elif 3.0 <= time_decimal < 4.0:
            return 4.5
        
        # 4:00 ~ 4:30 = 5
        elif 4.0 <= time_decimal < 4.5:
            return 5.0
        
        # 4:30 ~ 5:00 = 5.5
        elif 4.5 <= time_decimal < 5.0:
            return 5.5
        
        # 5:00 ~ 5:30 = 6
        elif 5.0 <= time_decimal < 5.5:
            return 6.0
        
        # 5:30 ~ 6:00 = 6.5
        elif 5.5 <= time_decimal < 6.0:
            return 6.5
        
        # 6:00 ~ 18:00 = 7
        elif 6.0 <= time_decimal < 18.0:
            return 7.0
        
        # 18:00 ~ 23:00 = 0
        elif 18.0 <= time_decimal < 23.0:
            return 0.0
        
        # 그 외 시간: 0
        else:
            return 0.0

    def _calculate_regular_work_hours(self):
        """常勤. 出勤時間と退勤時間が両方存在し、work_typeが特定のものでない場合に計算"""
        # 1．出勤時間と退勤時間が両方存在するか確認
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.regular_work_hours = None
            return
        
        # 2．work_typeが計算対象外のものか確認
        exclude_types = ['休日(法)', '祝日', '振替(法)', '休日', '振替(休)', '代休(休)']
        if self.work_type in exclude_types:
            self.regular_work_hours = None
            return

        # 3．計算式: 時間代入関数(出勤時間) - 時間代入関数(退勤時間)
        start_value = self._get_time_value(self.start_time, self.break_minutes)
        end_value = self._get_time_value(self.end_time, self.break_minutes)
        
        calculated_hours = start_value - end_value
        
        # 4．結果結果とstandard_work_hours のうち、小さい方が最終値
        self.regular_work_hours = round(min(calculated_hours, self.standard_work_hours), 2)



    def _calculate_deduction_hours(self):
        """控除時間計算"""
        # 1．regular_work_hoursがnullの場合、nullを返す
        if self.regular_work_hours is None:
            self.deduction_hours = None
            return
        
        # 2．regular_work_hoursがnullでない場合、計算
        if self.work_type == "有給(半)":
            # 有給(半)の場合: standard_work_hours - regular_work_hours - 4
            deduction = self.standard_work_hours - self.regular_work_hours - 4
        else:
            # その他の場合: standard_work_hours - regular_work_hours
            deduction = self.standard_work_hours - self.regular_work_hours
        
        # 3．0.0보다 小さい場合、0を返す、そうでない場合、計算された値を返す
        self.deduction_hours = round(max(0.0, deduction), 2)

    def _calculate_overtime_hours(self):
        """잔업시간 계산"""
        # ① start_time 또는 end_time이 NULL → NULL
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.overtime_hours = None
            return

        # 계산된 퇴근시간 만들기
        calculated_end_time = self.end_time
        if self.end_time < self.start_time and self.end_time < time(1, 0):
            # end_time < start_time 이면서 end_time < 1 (다음날 퇴근했는데 다음날 처리가 안됨)
            # 퇴근시간에 +24시간을 해줌 (1일 추가)
            calculated_end_time = time((self.end_time.hour + 24) % 24, self.end_time.minute)

        # 출근시간을 소수점으로 변환
        start_decimal = self.start_time.hour + self.start_time.minute / 60.0
        end_decimal = calculated_end_time.hour + calculated_end_time.minute / 60.0

        overtime_value = 0.0

        # 첫번째 조건: 0.75 < start_time < 1.25
        if 0.75 < start_decimal < 1.25:
            # 계산된 퇴근시간을 넣어서 얻은 값 - 출근시간을 넣어서 얻은 값
            end_value = self._get_overtime_value(calculated_end_time)
            start_value = self._get_overtime_value(self.start_time)
            overtime_value = end_value - start_value
        else:
            # 0.7 < 계산된 퇴근시간 < 1.376 인지 확인
            if 0.7 < end_decimal < 1.376:
                # 계산된 퇴근시간을 넣어서 얻은 값만 가져옴
                overtime_value = self._get_overtime_value(calculated_end_time)
            else:
                # 해당하지 않으면 0을 반환
                overtime_value = 0.0

        # break_minutes가 45면서 standard_work_hours > 0.76 이면 0.5를 더함
        if self.break_minutes == 45 and self.standard_work_hours > 0.76:
            overtime_value += 0.5

        # calculated_hours가 standard_work_hours보다 컸다면 calculated_hours - standard_work_hours를 더함
        # calculated_hours를 다시 계산해야 함 (exclude_types인 경우 None이므로)
        exclude_types = ['休日(法)', '祝日', '振替(法)', '休日', '振替(休)', '代休(休)']
        if self.work_type in exclude_types:
            # exclude_types인 경우 calculated_hours를 직접 계산
            start_value = self._get_time_value(self.start_time, self.break_minutes)
            end_value = self._get_time_value(calculated_end_time, self.break_minutes)
            calculated_hours = start_value - end_value
        else:
            # exclude_types가 아닌 경우 기존 계산된 값 사용
            start_value = self._get_time_value(self.start_time, self.break_minutes)
            end_value = self._get_time_value(calculated_end_time, self.break_minutes)
            calculated_hours = start_value - end_value

        if calculated_hours > self.standard_work_hours:
            overtime_value += calculated_hours - self.standard_work_hours

        # work_type이 exclude_types에 해당되면 calculated_hours와 standard_work_hours를 비교해 더 작은 값을 더함
        if self.work_type in exclude_types:
            min_value = min(calculated_hours, self.standard_work_hours)
            overtime_value += min_value

        self.overtime_hours = round(overtime_value, 2)
        
    def _calculate_late_night_hours(self):
        """심야시간 계산"""
        # ① start_time 또는 end_time이 NULL → NULL
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.late_night_overtime_hours = None
            return

        # 계산된 퇴근시간 만들기 (잔업시간과 동일)
        calculated_end_time = self.end_time
        if self.end_time < self.start_time and self.end_time < time(1, 0):
            # end_time < start_time 이면서 end_time < 1 (다음날 퇴근했는데 다음날 처리가 안됨)
            # 퇴근시간에 +24시간을 해줌 (1일 추가)
            calculated_end_time = time((self.end_time.hour + 24) % 24, self.end_time.minute)

        # 출근시간을 소수점으로 변환
        start_decimal = self.start_time.hour + self.start_time.minute / 60.0
        end_decimal = calculated_end_time.hour + calculated_end_time.minute / 60.0

        late_night_value = 0.0

        # 첫번째 조건: 0.75 < start_time < 1.25
        if 0.75 < start_decimal < 1.25:
            # 계산된 퇴근시간을 넣어서 얻은 값 - 출근시간을 넣어서 얻은 값
            end_value = self._get_late_night_value(calculated_end_time)
            start_value = self._get_late_night_value(self.start_time)
            late_night_value = end_value - start_value
        else:
            # 0.7 < 계산된 퇴근시간 < 1.376 인지 확인
            if 0.7 < end_decimal < 1.376:
                # 계산된 퇴근시간을 넣어서 얻은 값만 가져옴
                late_night_value = self._get_late_night_value(calculated_end_time)
            else:
                # 해당하지 않으면 0을 반환
                late_night_value = 0.0

        self.late_night_overtime_hours = round(late_night_value, 2)

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
