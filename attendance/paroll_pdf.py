import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors

# 必要なフォント名はpdf_generator.pyと同じく定義されている前提
try:
    FONT_NAME = 'MS-Gothic'
    FONT_NAME_BOLD = 'MS-Mincho'
except Exception:
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'

# 給与明細書PDF生成

def generate_payslip_pdf(employee, payslip, year, month):
    """
    給与明細書PDFを生成し、BytesIO로 반환します。
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = {
        'Title': ParagraphStyle(name='Title', fontName=FONT_NAME_BOLD, fontSize=18, alignment=1),
        'Normal': ParagraphStyle(name='Normal', fontName=FONT_NAME, fontSize=11),
    }
    story = []
    # タイトル
    story.append(Paragraph('給与明細書', styles['Title']))
    story.append(Spacer(1, 8*mm))
    # 社員情報テーブル
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
    # 給与情報テーブル
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

# 勤怠詳細PDF生成

def generate_attendance_pdf(employee, monthly, daily_list, year, month):
    """
    勤怠詳細PDFを生成し、BytesIO로 반환します。
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = {
        'Title': ParagraphStyle(name='Title', fontName=FONT_NAME_BOLD, fontSize=18, alignment=1),
        'Normal': ParagraphStyle(name='Normal', fontName=FONT_NAME, fontSize=11),
    }
    story = []
    # タイトル
    story.append(Paragraph('勤怠詳細', styles['Title']))
    story.append(Spacer(1, 8*mm))
    # 社員情報テーブル
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
    # 勤怠詳細テーブル
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