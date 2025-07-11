import os
from io import BytesIO
from calendar import monthrange, weekday
from datetime import date

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

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
        'FooterHeader': ParagraphStyle(name='FooterHeader', fontName=FONT_NAME, fontSize=8, alignment=TA_CENTER),
    }


class PDFReportGenerator:
    def __init__(self, employee, year, month):
        self.employee = employee
        self.year = year
        self.month = month
        self.styles = PDFStyles()
        self.story = []

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
            ["", "", ""]
        ], colWidths=[18*mm, 18*mm, 18*mm])

        stamp_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),  # 바깥 테두리
            # 세로선(열 구분선)만 직접 지정
            ('LINEAFTER', (0, 0), (0, 2), 0.5, colors.black),  # 1번째 열 오른쪽
            ('LINEAFTER', (1, 0), (1, 2), 0.5, colors.black),  # 2번째 열 오른쪽
            # 1행(헤더) 아래에만 가로선
            ('LINEBELOW', (0, 0), (2, 0), 0.5, colors.black),
            # 나머지 행(2행, 3행)에는 가로선 없음
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))

        # 5열 헤더 테이블 데이터
        header_data = [
            # 1행: 제목(왼쪽), 버전(오른쪽)
            [
                Paragraph('稼 働 報 告 書', ParagraphStyle('TitleLeft', parent=S['Title'], alignment=TA_LEFT)),
                '', '', '',  # 중간은 비움
                Paragraph("TA2025v1. 00", ParagraphStyle('SmallRight', parent=S['SmallRight'], alignment=TA_RIGHT))
            ],
            # 2행: 회사명(왼쪽), 연월(중앙), 도장(오른쪽)
            [
                Paragraph("(株)TEchAve", ParagraphStyle('CompanyLeft', parent=S['Company'], alignment=TA_LEFT)),
                '',  # 중간 비움
                Paragraph(f"{self.year}年 {self.month}月", S['Header']),
                '',  # 중간 비움
                stamp_table
            ],
            # 3행: 캘린더, PJ명, 작업자명 (점선)
            [
                Paragraph(f"カレンダー：{monthly_data.base_calendar or ''}", S['Normal']),
                Paragraph(f"PJ名：{monthly_data.project_name or ''}", S['Normal']),
                Paragraph(f"作業者：{self.employee.display_name or self.employee.employee_no}", S['Normal']),
                '', ''
            ],
            # 4행: 휴게시간, 기준시간 (이하 생략)
            [
                Paragraph(f"昼休み区分：{monthly_data.break_minutes}分間", S['Normal']),
                Paragraph(f"基準時間：{monthly_data.standard_work_hours}Hr", S['Normal']),
                '', '', ''
            ]
        ]

        # 5열 Table 생성
        header_table = Table(header_data, colWidths=[45*mm, 45*mm, 40*mm, 10*mm, 40*mm])

        # 스타일 설정
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
            # 캘린더, PJ명, 작업자명 행
            ('SPAN', (3, 2), (4, 2)),  # 오른쪽 병합
            # 3행 점선(밑줄)
#           ('LINEBELOW', (0, 2), (2, 2), 0.5, colors.black, None, [2, 2]),
            # 휴게시간, 기준시간 행
            ('SPAN', (3, 3), (4, 3)),  # 오른쪽 병합
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
        """일별 데이터 테이블을 생성합니다."""
        
        # 테이블 헤더
        headers = ["月/日", "曜\n日", "勤務区分", "代休/振替\nの勤務日", "作業開始\n時 刻", "作業終了\n時 刻", "常 勤\n(Hr)", "控 除\n(Hr)", "残 業\n(Hr)", "深 夜\n(Hr)", "小 計\n(Hr)", "実施作業内容・備考"]
        
        # Paragraph로 변환 (줄바꿈 처리)
        header_paragraphs = [Paragraph(h.replace('\n', '<br/>'), self.styles.STYLES['NormalCenter']) for h in headers]
        
        data = [header_paragraphs]
        
        _, last_day = monthrange(self.year, self.month)
        daily_dict = {daily.date.day: daily for daily in daily_list}
        
        # 합계 계산을 위한 변수
        sums = {'H': 0.0, 'I': 0.0, 'J': 0.0, 'K': 0.0, 'L': 0.0}

        # 일별 데이터 행 추가
        for day in range(1, last_day + 1):
            current_date = date(self.year, self.month, day)
            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
            weekday_str = weekday_names[current_date.weekday()]
            
            row_data = [
                Paragraph(f"{self.month}/{day}", self.styles.STYLES['NormalCenter']),
                Paragraph(weekday_str, self.styles.STYLES['NormalCenter'])
            ]
            is_holiday_row = False

            if day in daily_dict:
                daily = daily_dict[day]
                work_type = daily.work_type or ""
                holiday_keywords = ["休日", "休日(法)", "振替(休)", "振替(法)", "祝日"]
                if any(keyword in work_type for keyword in holiday_keywords):
                    is_holiday_row = True

                row_data.append(Paragraph(work_type if work_type != "出勤" else "", self.styles.STYLES['NormalCenter']))
                row_data.append(Paragraph(daily.alternative_work_date.strftime("%m/%d") if daily.alternative_work_date else "", self.styles.STYLES['NormalCenter']))
                row_data.append(Paragraph(daily.start_time.strftime("%H:%M") if daily.start_time else "", self.styles.STYLES['NormalRight']))
                row_data.append(Paragraph(daily.end_time.strftime("%H:%M") if daily.end_time else "", self.styles.STYLES['NormalRight']))

                # 출근/퇴근 데이터가 있으면 None도 0으로 출력
                if daily.start_time or daily.end_time:
                    reg_h = daily.regular_work_hours if daily.regular_work_hours is not None else 0
                    ded_h = daily.deduction_hours if daily.deduction_hours is not None else 0
                    ovt_h = daily.overtime_hours if daily.overtime_hours is not None else 0
                    nit_h = daily.late_night_overtime_hours if daily.late_night_overtime_hours is not None else 0
                else:
                    reg_h = daily.regular_work_hours or 0
                    ded_h = daily.deduction_hours or 0
                    ovt_h = daily.overtime_hours or 0
                    nit_h = daily.late_night_overtime_hours or 0

                sub_h = reg_h + ovt_h + nit_h - ded_h

                sums['H'] += reg_h
                sums['I'] += ded_h
                sums['J'] += ovt_h
                sums['K'] += nit_h
                sums['L'] += sub_h
                
                # 常勤, 控除는 0.00, 残業, 深夜는 0.0으로 출력
                row_data.append(Paragraph(f"{reg_h:.2f}" if (reg_h or (daily.start_time or daily.end_time)) else "", self.styles.STYLES['NormalRight']))
                row_data.append(Paragraph(f"{ded_h:.2f}" if (ded_h or (daily.start_time or daily.end_time)) else "", self.styles.STYLES['NormalRight']))
                row_data.append(Paragraph(f"{ovt_h:.1f}" if (ovt_h or (daily.start_time or daily.end_time)) else "", self.styles.STYLES['NormalRight']))
                row_data.append(Paragraph(f"{nit_h:.1f}" if (nit_h or (daily.start_time or daily.end_time)) else "", self.styles.STYLES['NormalRight']))
                row_data.append(Paragraph(f"{sub_h:.2f}" if sub_h > 0 else "", self.styles.STYLES['NormalRight']))
                row_data.append(Paragraph(daily.notes or "", self.styles.STYLES['Normal']))
            else:
                # 데이터가 없는 날
                work_type = ""
                if weekday_str == "土": work_type = "休日"
                elif weekday_str == "日": work_type = "休日(法)"
                if work_type: is_holiday_row = True
                
                row_data.extend([Paragraph(work_type, self.styles.STYLES['NormalCenter']), '', '', '', '', '', '', '', '', Paragraph('', self.styles.STYLES['Normal'])])

            data.append(row_data)
            
            # 휴일 행 스타일 추가
            if is_holiday_row:
                row_index = len(data) - 1
                # self.daily_table_style.add('BACKGROUND', (1, row_index), (1, row_index), self.styles.HOLIDAY_FILL)
                # self.daily_table_style.add('TEXTCOLOR', (1, row_index), (1, row_index), self.styles.RED_FONT)
                # 위 방식은 동적으로 어려우므로 아래 테이블 생성 후 처리
        
        # 합계 행 추가
        total_row = [
            Paragraph("合 計", self.styles.STYLES['NormalCenter']), '', '', '', '', '',
            Paragraph(f"{sums['H']:.2f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{sums['I']:.2f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{sums['J']:.1f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{sums['K']:.1f}", self.styles.STYLES['NormalRight']),
            Paragraph(f"{sums['L']:.2f}", self.styles.STYLES['NormalRight']),
            ''
        ]
        data.append(total_row)
        
        # 컬럼 너비 설정 (엑셀과 유사하게)
        col_widths = [14*mm, 10*mm, 18*mm, 18*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 35*mm]
        
        daily_table = Table(data, colWidths=col_widths)
        
        # 테이블 스타일
        style_cmds = [
            # 기본 정렬 및 패딩
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), # 기본 중앙 정렬
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),

            # 헤더 스타일
            ('BACKGROUND', (0, 0), (-1, 0), self.styles.HEADER_FILL),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black), # DOUBLE과 유사한 효과

            # 전체 테두리
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            
            # 특정 열 정렬 (기본 정렬 덮어쓰기)
            ('ALIGN', (4, 1), (10, -2), 'RIGHT'), # 숫자 열들 오른쪽 정렬
            ('ALIGN', (11, 1), (11, -2), 'LEFT'), # 비고 열 왼쪽 정렬
            ('ALIGN', (6, -1), (10, -1), 'RIGHT'), # 합계 행 숫자들 오른쪽 정렬

            # 병합
            ('SPAN', (11, 0), (11, 0)), # 헤더 비고
            ('SPAN', (0, -1), (5, -1)), # 합계 라벨
        ]

        # 데이터 행 병합 및 휴일 스타일링
        for i in range(1, len(data) - 1):  # 헤더와 합계행 제외
            style_cmds.append(('SPAN', (11, i), (11, i)))  # 비고란 SPAN

            # 날짜와 요일 셀을 Paragraph로 변환 (폰트 적용을 위해)
            data[i][0] = Paragraph(str(data[i][0]), self.styles.STYLES['NormalCenter'])

            work_type_val = data[i][2]
            is_holiday = isinstance(work_type_val, Paragraph) and any(kw in work_type_val.text for kw in ["休日", "休日(法)", "振替(休)", "振替(法)", "祝日"])

            # 요일 한자 추출
            weekday_text = str(data[i][1])
            if is_holiday:
                # 휴일: 노란 배경 + 빨간 글자
                style_cmds.append(('BACKGROUND', (1, i), (1, i), self.styles.HOLIDAY_FILL))
                data[i][1] = Paragraph(weekday_text, ParagraphStyle(name='holiday', fontName=FONT_NAME, alignment=TA_CENTER, textColor=self.styles.RED_FONT))
            else:
                data[i][1] = Paragraph(weekday_text, self.styles.STYLES['NormalCenter'])


        # 소계, 합계 배경색
        style_cmds.append(('BACKGROUND', (10, 1), (10, -2), self.styles.SUBTOTAL_FILL)) # 소계 열
        style_cmds.append(('BACKGROUND', (6, -1), (10, -1), self.styles.SUBTOTAL_FILL)) # 합계 행

        daily_table.setStyle(TableStyle(style_cmds))
        self.story.append(daily_table)

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
            f"{getattr(monthly_data, 'holiday_overtime_hours', 0):.2f}",
            f"{getattr(monthly_data, 'holiday_late_night_overtime_hours', 0):.2f}",
            f"{overtime_conversion:.2f}",
        ]
        p_values = [Paragraph(v, self.styles.STYLES['NormalCenter']) for v in values]

        data = [
            [Paragraph("報告値", self.styles.STYLES['NormalCenter']), '', *p_labels],
            ['', '', *p_values]
        ]

        # 엑셀의 D열부터 시작하므로 앞의 B, C열에 해당하는 너비 추가
        col_widths = [15*mm, 9*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm, 22*mm]

        summary_table = Table(data, colWidths=col_widths)
        style = TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
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
        self.story.append(summary_table)

# ------------- 급여명세서 (모듈화 필요) -------------------- #
def generate_payslip_pdf(employee, payslip, year, month):
    """
    給与明細書PDFを生成し、BytesIO로 반환합니다.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = PDFStyles()
    story = []
    # 제목
    story.append(Paragraph('給与明細書', styles.STYLES['Title']))
    story.append(Spacer(1, 8*mm))
    # 직원 정보 테이블
    info_data = [
        ['社員番号', employee.employee_no],
        ['氏名', f'{employee.last_name}{employee.first_name}'],
        ['勤務先', employee.place_work],
        ['年月', f'{year}年 {month}月'],
    ]
    info_table = Table(info_data, colWidths=[30*mm, 100*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8*mm))
    # 급여 정보 테이블
    payslip_data = [
        ['支給額', f'{payslip.payment} 円'],
        ['控除額', f'{payslip.deduction} 円'],
        ['差引支給額', f'{payslip.net_payment} 円'],
        ['備考', payslip.notes or ''],
    ]
    payslip_table = Table(payslip_data, colWidths=[40*mm, 90*mm])
    payslip_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(payslip_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_attendance_pdf(employee, monthly, daily_list, year, month):
    """
    勤怠詳細PDFを生成し、BytesIO로 반환합니다.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = PDFStyles()
    story = []
    # 제목
    story.append(Paragraph('勤怠詳細', styles.STYLES['Title']))
    story.append(Spacer(1, 8*mm))
    # 직원 정보 테이블
    info_data = [
        ['社員番号', employee.employee_no],
        ['氏名', f'{employee.last_name}{employee.first_name}'],
        ['勤務先', employee.place_work],
        ['年月', f'{year}年 {month}月'],
        ['PJ名', monthly.project_name if monthly else ''],
    ]
    info_table = Table(info_data, colWidths=[30*mm, 100*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8*mm))
    # 근태 상세 테이블
    table_data = [
        ['日付', '勤務区分', '開始', '終了', '備考']
    ]
    for d in daily_list:
        table_data.append([
            str(d.date),
            d.work_type or '',
            d.start_time.strftime('%H:%M') if d.start_time else '',
            d.end_time.strftime('%H:%M') if d.end_time else '',
            d.notes or ''
        ])
    att_table = Table(table_data, colWidths=[25*mm, 30*mm, 20*mm, 20*mm, 55*mm])
    att_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(att_table)
    doc.build(story)
    buffer.seek(0)
    return buffer