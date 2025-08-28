import os
from io import BytesIO
from calendar import monthrange, weekday
from datetime import date, datetime

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from .models import AttendanceMonthly, AttendanceDaily
from .utils import get_or_create_monthly_structure
# --- 폰트 등록 (사용자 지정 폰트 사용) ---
# .ttc (TrueType Collection) 파일은 여러 폰트가 포함되어 있을 수 있습니다.
try:
    # 1. 폰트 파일 경로 설정
    # 사용자가 'attendance/static/attendance/fonts/'에 추가한 폰트를 사용합니다.
    GOTHIC_FONT_PATH = os.path.join(settings.BASE_DIR, 'attendance', 'static', 'attendance', 'fonts', 'MSGOTHIC.TTC')
    MINCHO_FONT_PATH = os.path.join(settings.BASE_DIR, 'attendance', 'static', 'attendance', 'fonts', 'MSMINCHO.TTC')

    # 2. 폰트 파일 존재 여부 확인
    if not os.path.exists(GOTHIC_FONT_PATH):
        raise FileNotFoundError(f"Gothic 폰트 파일({GOTHIC_FONT_PATH})을 찾을 수 없습니다.")
    if not os.path.exists(MINCHO_FONT_PATH):
        raise FileNotFoundError(f"Mincho 폰트 파일({MINCHO_FONT_PATH})을 찾을 수 없습니다.")

    # 3. reportlab에 폰트 등록
    # MS Gothic을 기본 폰트로, MS Mincho를 Bold 폰트로 등록합니다.
    # TTC 파일의 폰트 인덱스를 1로 변경합니다. (요일 글자 깨짐 현상 해결 시도)
    # 일반적으로 0은 MS Gothic, 1은 MS PGothic 입니다. 렌더링에 필요한 글리프가 다른 인덱스에 있을 수 있습니다.
    pdfmetrics.registerFont(TTFont('MS-Gothic', GOTHIC_FONT_PATH, subfontIndex=1))
    pdfmetrics.registerFont(TTFont('MS-Mincho', MINCHO_FONT_PATH, subfontIndex=1))

    # 4. 사용할 폰트 이름 변수 설정
    FONT_NAME = 'MS-Gothic'
    FONT_NAME_BOLD = 'MS-Mincho'
    
    print("MS GothicとMS Minchoフォントを登録しました。(インデックス1使用)")

    #
    COL_WIDTHS = [14*mm, 10*mm, 16*mm, 17*mm, 16*mm, 16*mm, 14*mm, 14*mm, 14*mm, 14*mm, 14*mm, 35*mm]  # 合計180mm

except Exception as e:
    print(f"フォント読み込みエラー: {e}")
    # 폰트 로드 실패 시, PDF 생성이 깨질 수 있음을 알리고 기본 폰트로 대체
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'


# --- 스타일 상수 정의 (엑셀 스타일과 유사하게) ---
class PDFStyles:
    # 색상 정의 (HexColor)
    ACTIVE_FILL = colors.HexColor("#FFFFFF")
    INACTIVE_FILL = colors.HexColor("#E9F2F9")
    HEADER_FILL = colors.HexColor("#87cefa")
    SUBTOTAL_FILL = colors.HexColor("#81c147")
    ORANGE_FILL = colors.HexColor("#f8ad85")
    YELLOW_FILL = colors.HexColor("#ffff00")
    HOLIDAY_FILL = colors.HexColor("#FFFF99")
    RED_FONT = colors.HexColor("#FF0000")
    BLACK_FONT = colors.HexColor("#000000")

    # Paragraph 스타일 정의
    STYLES = {
        'Normal': ParagraphStyle(name='Normal', fontName=FONT_NAME, fontSize=10),
        'NormalCenter': ParagraphStyle(name='NormalCenter', fontName=FONT_NAME, fontSize=10, alignment=TA_CENTER),
        'NormalRight': ParagraphStyle(name='NormalRight', fontName=FONT_NAME, fontSize=10, alignment=TA_RIGHT),
        'SmallRight': ParagraphStyle(name='SmallRight', fontName=FONT_NAME, fontSize=8, alignment=TA_RIGHT),
        'Title': ParagraphStyle(name='Title', fontName=FONT_NAME_BOLD, fontSize=18, alignment=TA_CENTER),
        'Header': ParagraphStyle(name='Header', fontName=FONT_NAME_BOLD, fontSize=12, alignment=TA_CENTER),
        'HeaderSmall': ParagraphStyle(name='HeaderSmall', fontName=FONT_NAME, fontSize=9, alignment=TA_CENTER),
        'Company': ParagraphStyle(name='Company', fontName=FONT_NAME_BOLD, fontSize=11),
        'FooterHeader': ParagraphStyle(name='FooterHeader', fontName=FONT_NAME, fontSize=9, alignment=TA_CENTER), 
    }


class PDFReportGenerator:
    def __init__(self, employee, year, month):
        self.employee = employee
        self.year = year
        self.month = month
        self.styles = PDFStyles()
        self.story = []
        # 중앙 정렬 스타일을 한 번만 생성
        styles = getSampleStyleSheet()
        self.center_style = styles['Normal'].clone('centered')
        self.center_style.alignment = TA_CENTER
    
    def _get_month_holidays_optimized(self, year, month):
        """해당 월의 공휴일만 효율적으로 가져옵니다."""
        try:
            import requests
            
            print(f"[PDF HOLIDAY OPTIMIZED] {year}년 {month}월 공휴일 가져오기 시작", flush=True)
            
            # 해당 년도의 공휴일만 가져오기
            url = f"https://holidays-jp.github.io/api/v1/{year}/date.json"
            response = requests.get(url, timeout=5)  # 타임아웃 단축
            response.raise_for_status()
            
            holidays_data = response.json()
            print(f"[PDF HOLIDAY OPTIMIZED] {year}년 전체 공휴일: {len(holidays_data)}개", flush=True)
            
            # 해당 월의 공휴일만 필터링
            month_holidays = set()
            month_str = f"{month:02d}"
            
            for date_str, holiday_name in holidays_data.items():
                # YYYY-MM-DD 형식에서 월 확인
                if date_str.startswith(f"{year}-{month_str}"):
                    try:
                        holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        month_holidays.add(holiday_date)
                        print(f"[PDF HOLIDAY OPTIMIZED] {date_str} ({holiday_name}) 추가", flush=True)
                    except ValueError:
                        continue
            
            print(f"[PDF HOLIDAY OPTIMIZED] {year}년 {month}월 공휴일: {len(month_holidays)}개", flush=True)
            return month_holidays
            
        except Exception as e:
            print(f"[PDF HOLIDAY OPTIMIZED] 공휴일 가져오기 실패: {e}", flush=True)
            return set()

    def generate_pdf(self):
        """가동보고서 PDF 파일을 생성합니다."""
        buffer = BytesIO()
        # A4 세로 방향으로 변경, 여백 최소화
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=10*mm, bottomMargin=10*mm)

        try:
            monthly_data = get_or_create_monthly_structure(
                employee=self.employee,
                year=str(self.year),
                month=str(self.month)
            )
            if not monthly_data:
                raise ValueError("해당 월의 정보를 찾을 수 없습니다.")
            
            # 공휴일 데이터 가져오기 (해당 월만 최적화)
            self.api_holiday_dates = self._get_month_holidays_optimized(self.year, self.month)

            # PDF 내용 생성
            self._create_header_and_info(monthly_data)
            self._create_daily_table(monthly_data.daily_list)
            self._create_summary_tables(monthly_data)
            
            # 문서 빌드
            doc.build(self.story)
            buffer.seek(0)
            return buffer
        
        except Exception as e:
            print(f"PDF generation error: {e}")
            raise

    def _create_header_and_info(self, monthly_data):
        # 스타일 단축
        S = self.styles.STYLES

        # 도장(승인/확인/신청) 표 (3행)
        stamp_table = Table([
            [Paragraph("承認", S['HeaderSmall']), Paragraph("確認", S['HeaderSmall']), Paragraph("申請", S['HeaderSmall'])],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""]
        ], colWidths=[15*mm, 15*mm, 15*mm])

        stamp_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),  # 바깥 테두리
            # 全行に縦線（열 구분선）を追加
            ('LINEAFTER', (0, 0), (0, 3), 0.5, colors.black),  # 1번째 열 오른쪽 (0~3행)
            ('LINEAFTER', (1, 0), (1, 3), 0.5, colors.black),  # 2번째 열 오른쪽 (0~3행)
            ('LINEBELOW', (0, 0), (2, 0), 0.5, colors.black),  # 1행(헤더) 아래에만 가로선
            # 정렬・패딩
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))

        # ヘッダーテーブル データ
        header_data = [
            # 1行：バージョン(右)
            ['', '', '', '', Paragraph("TA2025v1. 00", ParagraphStyle('SmallRight', parent=S['SmallRight'], alignment=TA_RIGHT))],
            # 2行：タイトル(左)、スタンプ(右、2~5行 結合)
            [Paragraph('稼 働 報 告 書', ParagraphStyle('TitleLeft', parent=S['Title'], alignment=TA_LEFT)), '', '', '', stamp_table],
            # 3行：会社名(左)、年月(中央)
            [Paragraph("(株)TEchAve", ParagraphStyle('CompanyLeft', parent=S['Company'], alignment=TA_LEFT)), '', Paragraph(f"{self.year}年 {self.month}月", S['Header']), '', ''],
            # 4行：カレンダー、基準時間、PJ名 等
            [Paragraph(f"カレンダー：{monthly_data.base_calendar or ''}", S['Normal']), Paragraph(f"基準時間：{monthly_data.standard_work_hours}Hr", S['Normal']), Paragraph(f"PJ名：{monthly_data.project_name or ''}", S['Normal']), '', ''],
            # 5行：昼休み区分、作成者名 等
            [Paragraph(f"昼休み区分：{monthly_data.break_minutes}分間", S['Normal']), Paragraph(f"作成者：{self.employee.display_name or self.employee.employee_no}", S['Normal']), '', '', '']
        ]

        header_table = Table(header_data, colWidths=[40*mm, 40*mm, 50*mm, 20*mm, 30*mm])

        header_table.setStyle(TableStyle([
            # 제목 행 병합
            ('SPAN', (0, 0), (3, 0)),  # 제목은 왼쪽 4칸 병합
            # 버전은 우측정렬
            ('ALIGN', (4, 0), (4, 0), 'RIGHT'),
            # 회사명 행 병합
            ('SPAN', (0, 1), (1, 1)),  # 회사명은 왼쪽 2칸 병합
            ('SPAN', (2, 1), (3, 1)),  # 연월은 중간 2칸 병합
            # 도장 표는 오른쪽 끝에
            ('VALIGN', (4, 1), (4, 1), 'TOP'),
            # 4행: PJ명 병합 (긴 텍스트를 한 줄로 표시)
            ('SPAN', (2, 3), (3, 3)),  # PJ명 2칸 병합
            # 5행: 작성자 병합
            ('SPAN', (1, 4), (2, 4)),  # 작성자 2칸 병합
            # 도장 표를 2~5행에 병합
            ('SPAN', (4, 1), (4, 4)),  # 도장(stamp_table)을 2~5행(1~4 인덱스) 5번째 열에 병합
            # 전체 패딩/정렬
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        self.story.append(header_table)
        self.story.append(Spacer(1, 8*mm))


    def _create_daily_table(self, daily_list):
        """日次データテーブルを作成"""
        
        # テーブル ヘッダー
        headers = ["月/日", "曜\n日", "勤務区分", "代休/振替\nの勤務日", "作業開始\n時 刻", "作業終了\n時 刻", "常 勤\n(Hr)", "控 除\n(Hr)", "残 業\n(Hr)", "深 夜\n(Hr)", "小 計\n(Hr)", "実施作業内容・備考"]
        
        # Paragraphに変換 (改行処理)
        header_paragraphs = [Paragraph(h.replace('\n', '<br/>'), self.styles.STYLES['NormalCenter']) for h in headers]
        
        data = [header_paragraphs]
        
        _, last_day = monthrange(self.year, self.month)
        daily_dict = {daily.date.day: daily for daily in daily_list}
        
        # 合計計算用変数
        sums = {'H': 0.0, 'I': 0.0, 'J': 0.0, 'K': 0.0, 'L': 0.0}

        special_types = ["欠勤", "有給", "特別休暇", "振替(休)", "代休(休)"]
        # 日次データ行を追加
        for day in range(1, last_day + 1):
            calendar_date = date(self.year, self.month, day)
            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
            weekday_str = weekday_names[calendar_date.weekday()]
            row_data = [
                Paragraph(f"{self.month}/{day}", self.styles.STYLES['NormalCenter']),
                Paragraph(weekday_str, self.styles.STYLES['NormalCenter'])
            ]
            is_holiday_row = False

            if day in daily_dict:
                daily = daily_dict[day]
                work_type = daily.work_type or ""
                
                # 공휴일 체크
                is_api_holiday = calendar_date in getattr(self, 'api_holiday_dates', set())
                
                # 공휴일이고 work_type이 비어있거나 祝日이면 祝日로 설정
                if is_api_holiday and (not work_type or work_type == "祝日"):
                    work_type = "祝日"
                
                holiday_keywords = ["休日", "休日(法)", "振替(休)", "振替(法)", "祝日"]
                if any(keyword in work_type for keyword in holiday_keywords):
                    is_holiday_row = True
                # 出勤/退勤時間が同じ、または特定勤務区分なら 구분만 표시, 나머지는 빈칸
                if work_type in special_types or (daily.start_time and daily.end_time and daily.start_time == daily.end_time):
                    row_data.append(Paragraph(work_type if work_type != "出勤" else "", self.styles.STYLES['NormalCenter']))
                    # 나머지 11개를 정확히 추가
                    while len(row_data) < 12:
                        row_data.append('')
                else:
                    row_data.append(Paragraph(work_type if work_type != "出勤" else "", self.styles.STYLES['NormalCenter']))
                    # 代休/振替の勤務日: 8/1 형식으로 변경 (앞의 0 제거)
                    if daily.alternative_work_date:
                        alt_date_str = f"{daily.alternative_work_date.month}/{daily.alternative_work_date.day}"
                        row_data.append(Paragraph(alt_date_str, self.styles.STYLES['NormalCenter']))
                    else:
                        row_data.append(Paragraph("", self.styles.STYLES['NormalCenter']))
                    # 작업시작시각 (앞의 0 제거)
                    start_time_str = daily.start_time.strftime("%H:%M") if daily.start_time else ""
                    if start_time_str.startswith("0"):
                        start_time_str = start_time_str[1:]
                    row_data.append(Paragraph(start_time_str, self.styles.STYLES['NormalRight']))
                    
                    # 작업종료시각 (앞의 0 제거)
                    end_time_str = daily.end_time.strftime("%H:%M") if daily.end_time else ""
                    if end_time_str.startswith("0"):
                        end_time_str = end_time_str[1:]
                    row_data.append(Paragraph(end_time_str, self.styles.STYLES['NormalRight']))
                    reg_h = daily.regular_work_hours if daily.regular_work_hours is not None else 0.0
                    ded_h = daily.deduction_hours if daily.deduction_hours is not None else 0.0
                    ovt_h = daily.overtime_hours if daily.overtime_hours is not None else 0.0
                    nit_h = daily.late_night_overtime_hours if daily.late_night_overtime_hours is not None else 0.0
                    sub_h = daily.total_hours if daily.total_hours is not None else 0.0
                    if work_type in ["休日", "休日(法)", "祝日"]:
                        row_data.append(Paragraph("", self.styles.STYLES['NormalRight']))
                        row_data.append(Paragraph("", self.styles.STYLES['NormalRight']))
                    else:
                        row_data.append(Paragraph(f"{reg_h:.2f}", self.styles.STYLES['NormalRight']))
                        row_data.append(Paragraph(f"{ded_h:.2f}", self.styles.STYLES['NormalRight']))
                    row_data.append(Paragraph(f"{ovt_h:.1f}", self.styles.STYLES['NormalRight']))
                    row_data.append(Paragraph(f"{nit_h:.1f}", self.styles.STYLES['NormalRight']))
                    row_data.append(Paragraph(f"{sub_h:.2f}", self.styles.STYLES['NormalRight']))
                    row_data.append(Paragraph(daily.notes or "", self.styles.STYLES['Normal']))
                    # 혹시라도 부족하면 빈 칸 추가
                    while len(row_data) < 12:
                        row_data.append('')
            else:
                work_type = ""
                
                # 공휴일 체크
                is_api_holiday = calendar_date in getattr(self, 'api_holiday_dates', set())
                
                if is_api_holiday:
                    work_type = "祝日"
                    is_holiday_row = True
                elif weekday_str == "土": 
                    work_type = "休日"
                    is_holiday_row = True
                elif weekday_str == "日": 
                    work_type = "休日(法)"
                    is_holiday_row = True
                row_data.extend([Paragraph(work_type, self.styles.STYLES['NormalCenter'])])
                while len(row_data) < 12:
                    row_data.append('')

            data.append(row_data)
            
            # 휴일 행 스타일 추가
            if is_holiday_row:
                row_index = len(data) - 1
                # self.daily_table_style.add('BACKGROUND', (1, row_index), (1, row_index), self.styles.HOLIDAY_FILL)
                # self.daily_table_style.add('TEXTCOLOR', (1, row_index), (1, row_index), self.styles.RED_FONT)
                # 위 방식은 동적으로 어려우므로 아래 테이블 생성 후 처리
        
        # 合計行 추가 (각 열의 실제 값 합계)
        total_reg = sum(d.regular_work_hours or 0.0 for d in daily_list)
        total_ded = sum(d.deduction_hours or 0.0 for d in daily_list)
        total_ovt = sum(d.overtime_hours or 0.0 for d in daily_list)
        total_nit = sum(d.late_night_overtime_hours or 0.0 for d in daily_list)
        total_sub = sum(d.total_hours or 0.0 for d in daily_list)
        total_row = [
            Paragraph("合 計", self.styles.STYLES['NormalCenter']), '', '', '', '', '',
            Paragraph(f"{total_reg:.2f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{total_ded:.2f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{total_ovt:.2f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{total_nit:.2f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{total_sub:.2f}", self.styles.STYLES['NormalRight']),
            Paragraph('', self.styles.STYLES['Normal'])
        ]
        data.append(total_row)
        
        daily_table = Table(data, colWidths=COL_WIDTHS, hAlign='CENTER')
        
        # 테이블 스타일
        style_cmds = [
            # 기본 정렬 및 패딩
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), # 기본 중앙 정렬
            ('LEFTPADDING', (0, 0), (-1, -1), 0),  # 좌측 패딩 최소화
            ('RIGHTPADDING', (0, 0), (-1, -1), 2), # 우측 패딩 약간 추가
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),

            # 헤더 스타일
            ('BACKGROUND', (0, 0), (-1, 0), self.styles.HEADER_FILL),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black), # DOUBLE과 유사한 효과

            # 전체 테두리
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            
            # 특정 열 정렬 (기본 정렬 덮어쓰기)
            ('ALIGN', (4, 1), (10, -2), 'RIGHT'), # 숫자 열들 오른쪽 정렬 (4~10)
            ('ALIGN', (11, 1), (11, -2), 'LEFT'), # 비고 열 왼쪽 정렬 (11)
            ('ALIGN', (6, -1), (10, -1), 'RIGHT'), # 합계 행 숫자들 오른쪽 정렬 (6~10)

            # 병합
            ('SPAN', (11, 0), (11, 0)), # 헤더 비고 (11)
            ('SPAN', (0, -1), (5, -1)), # 합계 라벨
        ]

        # 데이터 행 병합 및 휴일 스타일링
        for i in range(1, len(data) - 1):  # 헤더와 합계행 제외
            style_cmds.append(('SPAN', (11, i), (11, i)))  # 비고란 SPAN (11)

            # 날짜와 요일 셀을 Paragraph로 변환 (폰트 적용을 위해)
            data[i][0] = Paragraph(str(data[i][0]), self.styles.STYLES['NormalCenter'])

            work_type_val = data[i][2]
            is_holiday = isinstance(work_type_val, Paragraph) and any(kw in work_type_val.text for kw in ["休日", "休日(法)", "振替(休)", "振替(法)", "祝日"])

            # 요일 한자 추출
            weekday_text = str(data[i][1])
            if is_holiday:
                # 휴일: 노란 배경만 (빨간 글자 제거)
                style_cmds.append(('BACKGROUND', (1, i), (1, i), self.styles.HOLIDAY_FILL))
                data[i][1] = Paragraph(weekday_text, self.styles.STYLES['NormalCenter'])
            else:
                data[i][1] = Paragraph(weekday_text, self.styles.STYLES['NormalCenter'])


        # 소계, 합계 배경색
        style_cmds.append(('BACKGROUND', (10, 1), (10, -2), self.styles.SUBTOTAL_FILL)) # 小計 열만 초록색
        style_cmds.append(('BACKGROUND', (6, -1), (10, -1), self.styles.SUBTOTAL_FILL)) # 합계 행

        daily_table.setStyle(TableStyle(style_cmds))
        # 표를 중앙에 배치하기 위해 Paragraph(align='center')로 감싼다
        # 파일 상단에만 import
        self.story.append(Paragraph('<br/>', self.center_style))  # 위 여백
        self.story.append(Paragraph('<para alignment="center"></para>', self.center_style))
        self.story.append(daily_table)
        self.story.append(Paragraph('<br/>', self.center_style))  # 아래 여백

    def _create_summary_tables(self, monthly_data):
        """하단 통계 테이블을 생성합니다."""
        self.story.append(Spacer(1, 2*mm))

        labels = ["出勤日", "年次\n有給", "特別\n有給", "無給日", "常勤", "控除", "残業", "深夜", "休日", "休日\n深夜", "残業換算(h)"]
        p_labels = [Paragraph(h.replace('\n', '<br/>'), self.styles.STYLES['FooterHeader']) for h in labels]
        
        overtime_conversion = getattr(monthly_data, 'overtime_conversion_hours', monthly_data.total_overtime_hours + monthly_data.total_late_night_overtime_hours)

        values = [
            f"{monthly_data.work_days:.1f}",
            f"{monthly_data.paid_leave_days:.1f}",
            f"{getattr(monthly_data, 'special_paid_leave_days', 0):.1f}",
            f"{getattr(monthly_data, 'unpaid_leave_days', 0):.1f}",
            f"{monthly_data.total_regular_work_hours:.2f}",
            f"{monthly_data.total_deduction_hours:.2f}",
            f"{monthly_data.total_overtime_hours:.2f}",
            f"{monthly_data.total_late_night_overtime_hours:.2f}",
            # 休日・祝日の残業・深夜時間は structures.py のプロパティを参照
            f"{monthly_data.total_holiday_work_hours:.2f}",
            f"{monthly_data.holiday_work_hours_night:.2f}",
            f"{monthly_data.holiday_work_hours_overtime:.2f}",
        ]
        p_values = [Paragraph(v, self.styles.STYLES['NormalCenter']) for v in values]

        data_summary = [
            [Paragraph("報告値", self.styles.STYLES['NormalCenter']), '', *p_labels],  # 총 12개 열
            ['', '', *p_values]  # 총 12개 열
        ]
        SUMMARY_COL_WIDTHS = [10*mm, 14*mm, 14*mm, 14*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 18*mm]  # 合計180mm, 12列
        summary_table = Table(data_summary, colWidths=SUMMARY_COL_WIDTHS, hAlign='CENTER')

        style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('SPAN', (0, 0), (1, 1)), # 보고치
            ('SPAN', (12, 0), (12, 0)), # 잔업환산 헤더 (실제로는 p_labels에 포함됨)
            ('SPAN', (12, 1), (12, 1)), # 잔업환산 값 (실제로는 p_values에 포함됨)
            
            # 배경색
            ('BACKGROUND', (2, 0), (-1, 0), self.styles.ORANGE_FILL),
            ('BACKGROUND', (2, 1), (-1, 1), self.styles.YELLOW_FILL),
            
            # 테두리
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ])
        
        summary_table.setStyle(style)
        # 요약표도 동일하게 중앙에 배치
        self.story.append(Paragraph('<br/>', self.center_style))
        self.story.append(Paragraph('<para alignment="center"></para>', self.center_style))
        self.story.append(summary_table)
        self.story.append(Paragraph('<br/>', self.center_style))