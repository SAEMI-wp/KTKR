from typing import List, Optional
from datetime import date, time
from .models import Employee, AttendanceMonthly, AttendanceDaily, Calendar
from .structures import DailyData, MonthlyData
import os
import urllib.parse

def convert_daily_to_structure(daily_model: AttendanceDaily, 
                              break_minutes: int = 60,
                              standard_work_hours: float = 8.0) -> DailyData:
    """AttendanceDailyモデルをDailyData構造体に変換"""
    return DailyData(
        date=daily_model.date,
        work_type=daily_model.work_type,
        start_time=daily_model.start_time,
        end_time=daily_model.end_time,
        alternative_work_date1=daily_model.alternative_work_date1,
        alternative_work_date2=daily_model.alternative_work_date2,
        alternative_work_date3=daily_model.alternative_work_date3,
        notes=daily_model.notes,
        is_required=daily_model.is_required,
        is_confirmed=daily_model.is_confirmed,
        break_minutes=break_minutes,
        standard_work_hours=standard_work_hours
    )

def convert_monthly_to_structure(monthly_model: AttendanceMonthly) -> MonthlyData:
    """AttendanceMonthlyモデルをMonthlyData構造体に変換"""
    # 日別データリストを作成
    daily_list = []
    daily_models = AttendanceDaily.objects.filter(
        monthly_attendance=monthly_model
    ).order_by('date')
    
    # base_calendar属性を安全に取得
    base_calendar = monthly_model.base_calendar
    calendar_id = None
    calendar_name = None
    break_minutes = 60  # default
    standard_work_hours = 8.0  # default
    standard_start_time = None
    standard_end_time = None
    
    if base_calendar:
        calendar_id = base_calendar.id
        calendar_name = getattr(base_calendar, 'calendar_name', None) or str(base_calendar)
        break_minutes = getattr(base_calendar, 'break_minutes', 60)
        standard_work_hours = getattr(base_calendar, 'standard_work_hours', 8.0)
        standard_start_time = getattr(base_calendar, 'start_time', None)
        standard_end_time = getattr(base_calendar, 'end_time', None)
    
    for daily_model in daily_models:
        daily_data = convert_daily_to_structure(
            daily_model,
            break_minutes=break_minutes,
            standard_work_hours=standard_work_hours
        )
        daily_list.append(daily_data)
    
    return MonthlyData(
        employee_id=monthly_model.employee.employee_no,
        year=monthly_model.year,
        month=monthly_model.month,
        project_name=monthly_model.project_name,
        calendar_id=calendar_id,
        calendar_name=calendar_name,
        break_minutes=break_minutes,
        standard_work_hours=standard_work_hours,
        standard_start_time=standard_start_time,
        standard_end_time=standard_end_time,
        daily_list=daily_list
    )

def get_monthly_structure(employee: Employee, year: str, month: str) -> Optional[MonthlyData]:
    """月別構造体を取得（存在しない場合はNoneを返す）"""
    monthly_model = AttendanceMonthly.objects.filter(
        employee=employee,
        year=year,
        month=month.zfill(2)
    ).first()
    if not monthly_model:
        # 월정보가 없으면 None 반환 (자동 생성하지 않음)
        return None
    monthly_data = convert_monthly_to_structure(monthly_model)
    monthly_data.calculate_all_daily_hours()
    return monthly_data

def create_monthly_structure(employee: Employee, year: str, month: str) -> MonthlyData:
    """月別構造体を新規作成"""
    # デフォルトのCalendarを取得
    default_calendar = Calendar.objects.first()
    if not default_calendar:
        # Calendarが存在しない場合は作成
        default_calendar = Calendar.objects.create(
            calendar_name='基準',
            break_minutes=60,
            standard_work_hours=8.0
        )
    
    monthly_model = AttendanceMonthly.objects.create(
        employee=employee,
        year=year,
        month=month.zfill(2),
        project_name='',
        base_calendar=default_calendar
    )
    monthly_data = convert_monthly_to_structure(monthly_model)
    monthly_data.calculate_all_daily_hours()
    return monthly_data

def get_or_create_monthly_structure(employee: Employee, year: str, month: str) -> Optional[MonthlyData]:
    """月別構造体を取得または新規作成（存在しない場合は新規作成して返す）"""
    return get_monthly_structure(employee, year, month) or create_monthly_structure(employee, year, month)

def save_daily_from_structure(daily_data: DailyData, monthly_model: AttendanceMonthly) -> AttendanceDaily:
    """DailyData構造体をDBに保存"""
    # 既存のデータがあるか確認
    existing_daily = AttendanceDaily.objects.filter(
        monthly_attendance=monthly_model,
        date=daily_data.date
    ).first()
    
    if existing_daily:
        # 既存のデータを更新
        existing_daily.work_type = daily_data.work_type
        existing_daily.start_time = daily_data.start_time
        existing_daily.end_time = daily_data.end_time
        existing_daily.alternative_work_date1 = daily_data.alternative_work_date1
        existing_daily.alternative_work_date2 = daily_data.alternative_work_date2
        existing_daily.alternative_work_date3 = daily_data.alternative_work_date3
        existing_daily.notes = daily_data.notes
        existing_daily.is_confirmed = daily_data.is_confirmed
        existing_daily.is_required = daily_data.is_required
        existing_daily.save()
        return existing_daily
    else:
        # 새 데이터 생성
        return AttendanceDaily.objects.create(
            monthly_attendance=monthly_model,
            date=daily_data.date,
            work_type=daily_data.work_type,
            start_time=daily_data.start_time,
            end_time=daily_data.end_time,
            alternative_work_date1=daily_data.alternative_work_date1,
            alternative_work_date2=daily_data.alternative_work_date2,
            alternative_work_date3=daily_data.alternative_work_date3,
            notes=daily_data.notes,
            is_confirmed=daily_data.is_confirmed,
            is_required=daily_data.is_required,
        )

def _get_calendar_object(calendar_id=None):
    """CalendarオブジェクトをIDで安全に取得"""
    if calendar_id:
        try:
            return Calendar.objects.get(id=calendar_id)
        except Calendar.DoesNotExist:
            pass
    
    # デフォルトのCalendar使用
    return Calendar.objects.first()

def update_monthly_from_structure(monthly_data: MonthlyData, employee: Employee) -> AttendanceMonthly:
    """MonthlyData構造体をDBに保存/更新"""
    # 既存の月別データを取得
    monthly_model = AttendanceMonthly.objects.filter(
        employee=employee,
        year=monthly_data.year,
        month=monthly_data.month
    ).first()
    
    # calendarオブジェクトを安全に取得
    calendar_obj = _get_calendar_object(calendar_id=monthly_data.calendar_id)
    
    if monthly_model:
        # 既存のデータを更新
        monthly_model.project_name = monthly_data.project_name
        monthly_model.base_calendar = calendar_obj
        monthly_model.save()
    else:
        # 新しいデータを作成
        monthly_model = AttendanceMonthly.objects.create(
            employee=employee,
            year=monthly_data.year,
            month=monthly_data.month,
            project_name=monthly_data.project_name,
            base_calendar=calendar_obj
        )
    
    # 日別データも保存
    for daily_data in monthly_data.daily_list:
        save_daily_from_structure(daily_data, monthly_model)
    
    return monthly_model 

def send_mail_dynamic(user, password, to_email, subject, body, attachment=None, attachment_filename=None, mime_type=None):
    user = user.strip()
    password = password.strip()
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'plain'))

    # 첨부파일 처리
    if attachment and attachment_filename:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment)
        encoders.encode_base64(part)
        # 添付ファイル名はASCIIのみ（日本語や括弧は含まない）
        part.add_header('Content-Disposition', f'attachment; filename="{attachment_filename}"')
        if mime_type:
            part.add_header('Content-Type', mime_type)
        msg.attach(part)

    try:
        print(f"SMTP 접속 시도: smtp.gmail.com:587", flush=True)
        
        # Railway에서 포트 587이 차단될 수 있으므로 대체 포트도 시도
        ports_to_try = [587, 465, 25]
        server = None
        
        for port in ports_to_try:
            try:
                print(f"포트 {port} 연결 시도...", flush=True)
                if port == 465:
                    # SSL 포트
                    server = smtplib.SMTP_SSL('smtp.gmail.com', port, timeout=30)
                else:
                    # TLS 포트
                    server = smtplib.SMTP('smtp.gmail.com', port, timeout=30)
                print(f"포트 {port} 연결 성공!", flush=True)
                break
            except Exception as e:
                print(f"포트 {port} 연결 실패: {e}", flush=True)
                if server:
                    try:
                        server.quit()
                    except:
                        pass
                server = None
                continue
        
        if not server:
            error_msg = """
모든 SMTP 포트 연결 실패 - Railway에서 Gmail SMTP가 차단되었을 수 있습니다.

            """.strip()
            raise Exception(error_msg)
        
        with server:
            # SSL이 아닌 경우에만 STARTTLS 실행
            if not isinstance(server, smtplib.SMTP_SSL):
                server.ehlo()
                print("EHLO 성공", flush=True)
                server.starttls()
                print("STARTTLS 성공", flush=True)
                server.ehlo()
            else:
                print("SMTP_SSL 사용 - STARTTLS 건너뛰기", flush=True)
            
            print(f'로그인 시도 - 사용자: {user}', flush=True)
            server.login(user, password)
            print("로그인 성공", flush=True)
            
            print(f"메일 전송 시도 - To: {to_email}", flush=True)
            server.sendmail(user, [to_email], msg.as_string())
            print('메일 전송 성공', flush=True)
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f'Gmail 인증 실패: {str(e)} - 이메일 주소와 앱 비밀번호를 확인해주세요'
        print(error_msg, flush=True)
        raise Exception(error_msg)
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f'수신자 주소 오류: {str(e)}'
        print(error_msg, flush=True)
        raise Exception(error_msg)
    except smtplib.SMTPServerDisconnected as e:
        error_msg = f'SMTP 서버 연결 실패: {str(e)}'
        print(error_msg, flush=True)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f'메일 전송 실패: {str(e)}'
        print(error_msg, flush=True)
        raise Exception(error_msg) 

def get_group_name_by_code(code):
    """
    employee_groupテーブルからgroup_codeでgroup_name(auth_group.name)を安全に取得する
    """
    from django.db import connection
    if not code:
        return None
    with connection.cursor() as cursor:
        cursor.execute("SELECT group_name FROM employee_group WHERE group_code = %s", [code])
        row = cursor.fetchone()
        if row:
            return row[0]
    return None 