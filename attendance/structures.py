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

    def _time_to_excel_decimal(self, time_obj: time) -> float:
        """時間をエクセル時間形式に変換 (24時間を1とする)"""
        # 例: 19:00 -> 0.791667, 19:30 -> 0.8125
        total_minutes = time_obj.hour * 60 + time_obj.minute
        result = total_minutes / (24 * 60)
        # 소수점 7번째 자리에서 무조건 올림
        return round(result + 0.0000001, 6)

    def _time_to_hr_decimal(self, time_obj: time) -> float:
        """時間をHr形式に変換 (1時間を1とする)"""
        # 例: 19:00 -> 19.0, 19:30 -> 19.5
        return time_obj.hour + time_obj.minute / 60.0

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
        """常勤時間計算の関数 (Excel時間基準)"""
        # 時間をExcel時間形式に変換 (例: 9:30 -> 0.395833)
        time_decimal = self._time_to_excel_decimal(time_obj)
        
        if break_minutes == 60:
            return self._get_time_value_60min(time_decimal)
        elif break_minutes == 45:
            return self._get_time_value_45min(time_decimal)
        else:
            # デフォルト値 (必要に応じて他のbreak_minutes値を追加)
            return 0.0

    def _get_time_value_common(self, time_decimal):
        """共通時間-値マッピング (0:00 ~ 11:50まで)"""
        # 0:00 ~ 7:35 = 0.0
        if time_decimal < 0.315972:  # 7:35 = 0.315972
            return 0.0
        
        # 7:35 ~ 8:20 = 8.75
        elif 0.315972 <= time_decimal < 0.347222:  # 7:35 ~ 8:20
            return 8.75
        
        # 8:20 ~ 8:35 = 8.5
        elif 0.347222 <= time_decimal < 0.357639:  # 8:20 ~ 8:35
            return 8.5
        
        # 8:35 ~ 8:50 = 8.25
        elif 0.357639 <= time_decimal < 0.368056:  # 8:35 ~ 8:50
            return 8.25
        
        # 8:50 ~ 9:05 = 8.0
        elif 0.368056 <= time_decimal < 0.378472:  # 8:50 ~ 9:05
            return 8.0
        
        # 9:05 ~ 9:20 = 7.75
        elif 0.378472 <= time_decimal < 0.388889:  # 9:05 ~ 9:20
            return 7.75
        
        # 9:20 ~ 9:35 = 7.5
        elif 0.388889 <= time_decimal < 0.399306:  # 9:20 ~ 9:35
            return 7.5
        
        # 9:35 ~ 9:50 = 7.25
        elif 0.399306 <= time_decimal < 0.409722:  # 9:35 ~ 9:50
            return 7.25
        
        # 9:50 ~ 10:05 = 7.0
        elif 0.409722 <= time_decimal < 0.420139:  # 9:50 ~ 10:05
            return 7.0
        
        # 10:05 ~ 10:20 = 6.75
        elif 0.420139 <= time_decimal < 0.430556:  # 10:05 ~ 10:20
            return 6.75
        
        # 10:20 ~ 10:35 = 6.5
        elif 0.430556 <= time_decimal < 0.440972:  # 10:20 ~ 10:35
            return 6.5
        
        # 10:35 ~ 10:50 = 6.25
        elif 0.440972 <= time_decimal < 0.451389:  # 10:35 ~ 10:50
            return 6.25
        
        # 10:50 ~ 11:05 = 6.0
        elif 0.451389 <= time_decimal < 0.461806:  # 10:50 ~ 11:05
            return 6.0
        
        # 11:05 ~ 11:20 = 5.75
        elif 0.461806 <= time_decimal < 0.472222:  # 11:05 ~ 11:20
            return 5.75
        
        # 11:20 ~ 11:35 = 5.5
        elif 0.472222 <= time_decimal < 0.482639:  # 11:20 ~ 11:35
            return 5.5
        
        # 11:35 ~ 11:50 = 5.25
        elif 0.482639 <= time_decimal < 0.493056:  # 11:35 ~ 11:50
            return 5.25
        
        # その他の時間: 0.0
        else:
            return 0.0

    def _get_time_value_60min(self, time_decimal):
        """break_minutesが60の場合の時間-値マッピング"""
        # 共通部分の処理 (0:00 ~ 11:50)
        if time_decimal < 0.5:
            return self._get_time_value_common(time_decimal)
        
        # 11:50 ~ 13:05 = 5.0
        elif 0.493056 <= time_decimal < 0.545139:  # 11:50 ~ 13:05
            return 5.0
        
        # 13:05 ~ 13:20 = 4.75
        elif 0.545139 <= time_decimal < 0.555556:  # 13:05 ~ 13:20
            return 4.75
        
        # 13:20 ~ 13:35 = 4.5
        elif 0.555556 <= time_decimal < 0.565972:  # 13:20 ~ 13:35
            return 4.5
        
        # 13:35 ~ 13:50 = 4.25
        elif 0.565972 <= time_decimal < 0.576389:  # 13:35 ~ 13:50
            return 4.25
        
        # 13:50 ~ 14:05 = 4.0
        elif 0.576389 <= time_decimal < 0.586806:  # 13:50 ~ 14:05
            return 4.0
        
        # 14:05 ~ 14:20 = 3.75
        elif 0.586806 <= time_decimal < 0.597222:  # 14:05 ~ 14:20
            return 3.75
        
        # 14:20 ~ 14:35 = 3.5
        elif 0.597222 <= time_decimal < 0.607639:  # 14:20 ~ 14:35
            return 3.5
        
        # 14:35 ~ 14:50 = 3.25
        elif 0.607639 <= time_decimal < 0.618056:  # 14:35 ~ 14:50
            return 3.25
        
        # 14:50 ~ 15:05 = 3.0
        elif 0.618056 <= time_decimal < 0.628472:  # 14:50 ~ 15:05
            return 3.0
        
        # 15:05 ~ 15:20 = 2.75
        elif 0.628472 <= time_decimal < 0.638889:  # 15:05 ~ 15:20
            return 2.75
        
        # 15:20 ~ 15:35 = 2.5
        elif 0.638889 <= time_decimal < 0.649306:  # 15:20 ~ 15:35
            return 2.5
        
        # 15:35 ~ 15:50 = 2.25
        elif 0.649306 <= time_decimal < 0.659722:  # 15:35 ~ 15:50
            return 2.25
        
        # 15:50 ~ 16:05 = 2.0
        elif 0.659722 <= time_decimal < 0.670139:  # 15:50 ~ 16:05
            return 2.0
        
        # 16:05 ~ 16:20 = 1.75
        elif 0.670139 <= time_decimal < 0.680556:  # 16:05 ~ 16:20
            return 1.75
        
        # 16:20 ~ 16:35 = 1.5
        elif 0.680556 <= time_decimal < 0.690972:  # 16:20 ~ 16:35
            return 1.5
        
        # 16:35 ~ 16:50 = 1.25
        elif 0.690972 <= time_decimal < 0.701389:  # 16:35 ~ 16:50
            return 1.25
        
        # 16:50 ~ 17:05 = 1.0
        elif 0.701389 <= time_decimal < 0.711806:  # 16:50 ~ 17:05
            return 1.0
        
        # 17:05 ~ 17:20 = 0.75
        elif 0.711806 <= time_decimal < 0.722222:  # 17:05 ~ 17:20
            return 0.75
        
        # 17:20 ~ 17:35 = 0.5
        elif 0.722222 <= time_decimal < 0.732639:  # 17:20 ~ 17:35
            return 0.5
        
        # 17:35 ~ 17:50 = 0.25
        elif 0.732639 <= time_decimal < 0.743056:  # 17:35 ~ 17:50
            return 0.25
        
        # 17:50 以降 = 0.0
        elif time_decimal >= 0.743056:
            return 0.0
        
        # その他の時間: 0.0
        else:
            return 0.0

    def _get_time_value_45min(self, time_decimal):
        """break_minutesが45の場合の時間-値マッピング"""
        # 共通部分の処理 (0:00 ~ 11:50)
        if time_decimal < 0.5:
            return self._get_time_value_common(time_decimal)
        
        # 11:50 ~ 12:50 = 5.0
        elif 0.493056 <= time_decimal < 0.534722:  # 11:50 ~ 12:50
            return 5.0
        
        # 12:50 ~ 13:05 = 4.75
        elif 0.534722 <= time_decimal < 0.545139:  # 12:50 ~ 13:05
            return 4.75
        
        # 13:05 ~ 13:20 = 4.5
        elif 0.545139 <= time_decimal < 0.555556:  # 13:05 ~ 13:20
            return 4.5
        
        # 13:20 ~ 13:35 = 4.25
        elif 0.555556 <= time_decimal < 0.565972:  # 13:20 ~ 13:35
            return 4.25
        
        # 13:35 ~ 13:50 = 4.0
        elif 0.565972 <= time_decimal < 0.576389:  # 13:35 ~ 13:50
            return 4.0
        
        # 13:50 ~ 14:05 = 3.75
        elif 0.576389 <= time_decimal < 0.586806:  # 13:50 ~ 14:05
            return 3.75
        
        # 14:05 ~ 14:20 = 3.5
        elif 0.586806 <= time_decimal < 0.597222:  # 14:05 ~ 14:20
            return 3.5
        
        # 14:20 ~ 14:35 = 3.25
        elif 0.597222 <= time_decimal < 0.607639:  # 14:20 ~ 14:35
            return 3.25
        
        # 14:35 ~ 14:50 = 3.0
        elif 0.607639 <= time_decimal < 0.618056:  # 14:35 ~ 14:50
            return 3.0
        
        # 14:50 ~ 15:05 = 2.75
        elif 0.618056 <= time_decimal < 0.628472:  # 14:50 ~ 15:05
            return 2.75
        
        # 15:05 ~ 15:20 = 2.5
        elif 0.628472 <= time_decimal < 0.638889:  # 15:05 ~ 15:20
            return 2.5
        
        # 15:20 ~ 15:35 = 2.25
        elif 0.638889 <= time_decimal < 0.649306:  # 15:20 ~ 15:35
            return 2.25
        
        # 15:35 ~ 15:50 = 2.0
        elif 0.649306 <= time_decimal < 0.659722:  # 15:35 ~ 15:50
            return 2.0
        
        # 15:50 ~ 16:05 = 1.75
        elif 0.659722 <= time_decimal < 0.670139:  # 15:50 ~ 16:05
            return 1.75
        
        # 16:05 ~ 16:20 = 1.5
        elif 0.670139 <= time_decimal < 0.680556:  # 16:05 ~ 16:20
            return 1.5
        
        # 16:20 ~ 16:35 = 1.25
        elif 0.680556 <= time_decimal < 0.690972:  # 16:20 ~ 16:35
            return 1.25
        
        # 16:35 ~ 16:50 = 1.0
        elif 0.690972 <= time_decimal < 0.701389:  # 16:35 ~ 16:50
            return 1.0
        
        # 16:50 ~ 17:05 = 0.75
        elif 0.701389 <= time_decimal < 0.711806:  # 16:50 ~ 17:05
            return 0.75
        
        # 17:05 ~ 17:20 = 0.5
        elif 0.711806 <= time_decimal < 0.722222:  # 17:05 ~ 17:20
            return 0.5
        
        # 17:20 以降 = 0.25
        elif time_decimal >= 0.722222:
            return 0.25
        
        # その他の時間: 0.0
        else:
            return 0.0

    def _get_overtime_value(self, time_obj):
        """残業値を返す関数"""
        # 時間をExcel時間形式に変換 (例: 19:00 -> 0.791667, 19:30 -> 0.8125)
        time_decimal = self._time_to_excel_decimal(time_obj)
        
        # 18:00 ~ 18:30 = 0 (0.75 ~ 0.770833)
        if 0.75 <= time_decimal < 0.770833:
            return 0.0
        
        # 18:30 ~ 19:00 = 0.5 (0.770833 ~ 0.791667)
        elif 0.770833 <= time_decimal < 0.791667:
            return 0.5
        
        # 19:00 ~ 19:30 = 1 (0.791667 ~ 0.8125)
        elif 0.791667 <= time_decimal < 0.8125:
            return 1.0
        
        # 19:30 ~ 20:00 = 1.5 (0.8125 ~ 0.833333)
        elif 0.8125 <= time_decimal < 0.833333:
            return 1.5
        
        # 20:00 ~ 20:30 = 1.5 (0.833333 ~ 0.854167)
        elif 0.833333 <= time_decimal < 0.854167:
            return 1.5
        
        # 20:30 ~ 21:00 = 2 (0.854167 ~ 0.875)
        elif 0.854167 <= time_decimal < 0.875:
            return 2.0
        
        # 21:00 ~ 21:30 = 2.5 (0.875 ~ 0.895833)
        elif 0.875 <= time_decimal < 0.895833:
            return 2.5
        
        # 21:30 ~ 22:00 = 3 (0.895833 ~ 0.916667)
        elif 0.895833 <= time_decimal < 0.916667:
            return 3.0
        
        # 22:00 ~ 6:30 = 3.5 (0.916667 ~ 1.0 또는 0.0 ~ 0.270833)
        elif 0.916667 <= time_decimal < 1.0 or 0.0 <= time_decimal < 0.270833:
            return 3.5
        
        # 6:30 ~ 7:00 = 4 (0.270833 ~ 0.291667)
        elif 0.270833 <= time_decimal < 0.291667:
            return 4.0
        
        # 7:00 ~ 7:30 = 4.5 (0.291667 ~ 0.3125)
        elif 0.291667 <= time_decimal < 0.3125:
            return 4.5
        
        # 7:30 ~ 8:00 = 5 (0.3125 ~ 0.333333)
        elif 0.3125 <= time_decimal < 0.333333:
            return 5.0
        
        # 8:00 ~ 8:30 = 5.5 (0.333333 ~ 0.354167)
        elif 0.333333 <= time_decimal < 0.354167:
            return 5.5
        
        # 8:30 ~ 9:00 = 6 (0.354167 ~ 0.375)
        elif 0.354167 <= time_decimal < 0.375:
            return 6.0
        
        # 9:00 ~ 9:35 = 6.5 (0.375 ~ 0.398611)
        elif 0.375 <= time_decimal < 0.398611:
            return 6.5
        
        # その他の時間: 0
        else:
            return 0.0

    def _get_late_night_value(self, time_obj):
        """深夜値を返す関数"""
        # 時間をExcel時間形式に変換 (例: 23:30 -> 0.979167, 0:00 -> 0.0)
        time_decimal = self._time_to_excel_decimal(time_obj)
        
        # 23:00 ~ 23:30 = 0.5 (0.958333 ~ 0.979167)
        if 0.958333 <= time_decimal < 0.979167:
            return 0.5
        
        # 23:30 ~ 0:00 = 1 (0.979167 ~ 1.0)
        elif 0.979167 <= time_decimal < 1.0:
            return 1.0
        
        # 0:00 ~ 0:30 = 1.5 (0.0 ~ 0.020833)
        elif 0.0 <= time_decimal < 0.020833:
            return 1.5
        
        # 0:30 ~ 1:00 = 2 (0.020833 ~ 0.041667)
        elif 0.020833 <= time_decimal < 0.041667:
            return 2.0
        
        # 1:00 ~ 1:30 = 2.5 (0.041667 ~ 0.0625)
        elif 0.041667 <= time_decimal < 0.0625:
            return 2.5
        
        # 1:30 ~ 2:00 = 3 (0.0625 ~ 0.083333)
        elif 0.0625 <= time_decimal < 0.083333:
            return 3.0
        
        # 2:00 ~ 2:30 = 3.5 (0.083333 ~ 0.104167)
        elif 0.083333 <= time_decimal < 0.104167:
            return 3.5
        
        # 2:30 ~ 3:00 = 4 (0.104167 ~ 0.125)
        elif 0.104167 <= time_decimal < 0.125:
            return 4.0
        
        # 3:00 ~ 4:00 = 4.5 (0.125 ~ 0.166667)
        elif 0.125 <= time_decimal < 0.166667:
            return 4.5
        
        # 4:00 ~ 4:30 = 5 (0.166667 ~ 0.1875)
        elif 0.166667 <= time_decimal < 0.1875:
            return 5.0
        
        # 4:30 ~ 5:00 = 5.5 (0.1875 ~ 0.208333)
        elif 0.1875 <= time_decimal < 0.208333:
            return 5.5
        
        # 5:00 ~ 5:30 = 6 (0.208333 ~ 0.229167)
        elif 0.208333 <= time_decimal < 0.229167:
            return 6.0
        
        # 5:30 ~ 6:00 = 6.5 (0.229167 ~ 0.25)
        elif 0.229167 <= time_decimal < 0.25:
            return 6.5
        
        # 6:00 ~ 22:00 = 0 (0.25 ~ 0.916667) - 심야시간이 아님
        elif 0.25 <= time_decimal < 0.916667:
            return 0.0
        
        # 22:00 ~ 23:00 = 7 (0.916667 ~ 0.958333)
        elif 0.916667 <= time_decimal < 0.958333:
            return 7.0
        
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
        """残業時間計算"""
        # ① start_time または end_timeがNULL、またはstart_timeとend_timeが同じ場合、NULLを返す
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.overtime_hours = None
            return

        # 2．計算された退勤時間を作成（24時間を超える場合の処理）
        calculated_end_time = self.end_time
        if self.end_time < self.start_time:
            # 退勤時間が出勤時間より小さい場合、翌日に跨がったと判断
            # 24時間を加算して処理
            calculated_end_time = time((self.end_time.hour + 24) % 24, self.end_time.minute)

        # 출근시간을 엑셀 시간으로 변환
        start_decimal = self._time_to_excel_decimal(self.start_time)
        end_decimal = self._time_to_excel_decimal(calculated_end_time)

        overtime_value = 0.0

        # 첫번째 조건: 0.75 < start_time < 1.25 (18:00 ~ 30:00)
        if 0.75 < start_decimal < 1.25:
            # 계산된 퇴근시간을 넣어서 얻은 값 - 출근시간을 넣어서 얻은 값
            end_value = self._get_overtime_value(calculated_end_time)
            start_value = self._get_overtime_value(self.start_time)
            overtime_value = end_value - start_value
        else:
            # 0.7 < 계산된 퇴근시간 < 1.376 (16:48 ~ 33:02) 인지 확인
            if 0.7 < end_decimal < 1.376:
                # 계산된 퇴근시간을 넣어서 얻은 값만 가져옴
                overtime_value = self._get_overtime_value(calculated_end_time)
            else:
                # 해당하지 않으면 0을 반환
                overtime_value = 0.0

        # break_minutes가 45면서 standard_work_hours > 0.76 이면 0.5를 더함
        # 이 조건은 실제 잔업시간이 있을 때만 적용되어야 함
        if self.break_minutes == 45 and self.standard_work_hours > 0.76:
            overtime_value += 0.5

        # calculated_hours가 standard_work_hours보다 컸다면 calculated_hours - standard_work_hours를 더함
        # calculated_hours를 다시 계산해야 함 (exclude_types인 경우 None이므로)
        exclude_types = ['休日(法)', '祝日', '振替(法)', '休日', '振替(休)', '代休(休)']
        if self.work_type in exclude_types:
            # exclude_types인 경우 calculated_hours를 직접 계산 (Hr基準)
            start_value = self._get_time_value(self.start_time, self.break_minutes)
            end_value = self._get_time_value(calculated_end_time, self.break_minutes)
            calculated_hours = start_value - end_value
        else:
            # exclude_types가 아닌 경우 기존 계산된 값 사용 (Hr基準)
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
        """深夜時間計算"""
        # ① start_time または end_timeがNULL、またはstart_timeとend_timeが同じ場合、NULLを返す
        if not self.start_time or not self.end_time or self.start_time == self.end_time:
            self.late_night_overtime_hours = None
            return

        # 計算された退勤時間を作成（24時間を超える場合の処理）
        calculated_end_time = self.end_time
        if self.end_time < self.start_time:
            # 退勤時間が出勤時間より小さい場合、翌日に跨がったと判断
            # 24時間を加算して処理
            calculated_end_time = time((self.end_time.hour + 24) % 24, self.end_time.minute)

        # 출근시간을 엑셀 시간으로 변환
        start_decimal = self._time_to_excel_decimal(self.start_time)
        end_decimal = self._time_to_excel_decimal(calculated_end_time)

        late_night_value = 0.0

        # 첫번째 조건: 0.75 < start_time < 1.25 (18:00 ~ 30:00)
        if 0.75 < start_decimal < 1.25:
            # 계산된 퇴근시간을 넣어서 얻은 값 - 출근시간을 넣어서 얻은 값
            end_value = self._get_late_night_value(calculated_end_time)
            start_value = self._get_late_night_value(self.start_time)
            late_night_value = end_value - start_value
        else:
            # 0.7 < 계산된 퇴근시간 < 1.376 (16:48 ~ 33:02) 인지 확인
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
