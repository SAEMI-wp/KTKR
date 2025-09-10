# 일별 출근 관리 관련 뷰들
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from datetime import datetime, date
import json

from ..models import AttendanceMonthly, AttendanceDaily
from ..utils import get_or_create_monthly_structure, update_monthly_from_structure
from ..cache_utils import invalidate_monthly_cache
from ..structures import DailyData


# ===================== ユーティリティ関数 =====================
def parse_day_value(day_value):
    """
    day_valueが 'YYYY-MM-DD' 形式なら day部分だけ返し、
    そうでなければ int変換して返す
    """
    if isinstance(day_value, int):
        return day_value
    if isinstance(day_value, str):
        if '-' in day_value:
            try:
                return int(day_value.split('-')[2])
            except Exception:
                pass
        try:
            return int(day_value)
        except Exception:
            pass
    raise ValueError('Invalid day value')


# 日別データ更新ビュー（ログイン必須）
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class DailyDataUpdateView(View):
    def post(self, request, *args, **kwargs):
        print("=== DailyDataUpdateView called ===")
        print(f"Request method: {request.method}")
        print(f"Request content type: {request.content_type}")
        
        try:
            # JSON 또는 FormData 모두 처리
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # FormData 처리
                data = {}
                for key in request.POST:
                    data[key] = request.POST[key]
            
            print(f"Received data: {data}")
            
            # 日付の処理 - 日(day)のみを受け取り、現在の年月と組み合わせる
            day = data.get('day')
            if not day:
                print("Error: No day provided")
                return JsonResponse({'status': 'error', 'message': '日付が指定されていません'})
            
            year = data.get('year')
            month = data.get('month')
            
            if not year or not month:
                print("Error: No year or month provided")
                return JsonResponse({'status': 'error', 'message': '年月情報が不足しています'})
            
            print(f"Processing date: {year}-{month}-{day}")
            print(f"Raw day value: {day} (type: {type(day)})")
            
            try:
                day_int = parse_day_value(day)
                print(f"Parsed day_int: {day_int} (type: {type(day_int)})")
                target_date = date(int(year), int(month), day_int)
                print(f"Target date: {target_date} (type: {type(target_date)})")
            except ValueError as e:
                print(f"Date parsing error: {e}")
                return JsonResponse({'status': 'error', 'message': '無効な日付です'})
            
            # 구조체 기반으로 월별 데이터 가져오기
            print(f"=== 월별 데이터 조회 시작 ===")
            print(f"Employee: {request.user}")
            print(f"Year: {str(target_date.year)}")
            print(f"Month: {str(target_date.month)}")
            
            monthly_data = get_or_create_monthly_structure(
                employee=request.user,
                year=str(target_date.year),
                month=str(target_date.month)
            )
            
            print(f"Monthly data found: {monthly_data is not None}")
            if monthly_data:
                print(f"Monthly data details: employee_id={monthly_data.employee_id}, year={monthly_data.year}, month={monthly_data.month}")
            else:
                print("Error: No monthly data found")
                return JsonResponse({'status': 'error', 'message': '該当する月別勤怠情報が見つかりません'})
            
            # 필수 필드 검증
            work_type = data.get('work_type')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')
            alternative_work_date1_str = data.get('alternative_work_date1')
            alternative_work_date2_str = data.get('alternative_work_date2')
            alternative_work_date3_str = data.get('alternative_work_date3')
            
            print(f"=== 필수 필드 검증 시작 ===")
            print(f"work_type: '{work_type}' (type: {type(work_type)})")
            print(f"start_time_str: '{start_time_str}' (type: {type(start_time_str)})")
            print(f"end_time_str: '{end_time_str}' (type: {type(end_time_str)})")
            
            if not work_type:
                print("Error: work_type이 없습니다")
                return JsonResponse({'status': 'error', 'message': '勤務区分を選択してください'})
            
            # 휴일/휴가 타입이 아닌 경우에만 시간 필수
            if work_type not in ['休日(法)', '休日', '祝日', '年休', '年休(半)', '代休', '振替(休)', '振替(勤)', '欠勤', '特別休暇']:
                print(f"시간 필수 근무구분: {work_type}")
                if not start_time_str:
                    print("Error: start_time이 없습니다")
                    return JsonResponse({'status': 'error', 'message': '作業開始時刻を入力してください'})
                
                if not end_time_str:
                    print("Error: end_time이 없습니다")
                    return JsonResponse({'status': 'error', 'message': '作業終了時刻を入力してください'})
            else:
                print(f"시간 불필요 근무구분: {work_type}")
            
            print(f"=== 필수 필드 검증 완료 ===")
            
            print(f"=== 폼 데이터 디버깅 ===")
            print(f"전체 POST 데이터: {dict(data)}")
            print(f"Time strings: start={start_time_str}, end={end_time_str}")
            print(f"Alternative dates: alt1={alternative_work_date1_str}, alt2={alternative_work_date2_str}, alt3={alternative_work_date3_str}")
            print(f"=========================")
            
            start_time = '00:00:00'
            end_time = '00:00:00'
            alternative_work_date1 = None
            alternative_work_date2 = None
            alternative_work_date3 = None
            
            if start_time_str:
                try:
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    print(f"Parsed start_time: {start_time}")
                except ValueError as e:
                    print(f"Start time parsing error: {e}")
                    pass
            
            if end_time_str:
                try:
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    print(f"Parsed end_time: {end_time}")
                except ValueError as e:
                    print(f"End time parsing error: {e}")
                    pass
            
            if alternative_work_date1_str:
                try:
                    alternative_work_date1 = datetime.strptime(alternative_work_date1_str, '%Y-%m-%d').date()
                    print(f"Parsed alternative_work_date1: {alternative_work_date1}")
                except ValueError as e:
                    print(f"Alternative work date 1 parsing error: {e}")
                    
            if alternative_work_date2_str:
                try:
                    alternative_work_date2 = datetime.strptime(alternative_work_date2_str, '%Y-%m-%d').date()
                    print(f"Parsed alternative_work_date2: {alternative_work_date2}")
                except ValueError as e:
                    print(f"Alternative work date 2 parsing error: {e}")
                    
            if alternative_work_date3_str:
                try:
                    alternative_work_date3 = datetime.strptime(alternative_work_date3_str, '%Y-%m-%d').date()
                    print(f"Parsed alternative_work_date3: {alternative_work_date3}")
                except ValueError as e:
                    print(f"Alternative work date 3 parsing error: {e}")
                    pass
            
            # 기존 일별 데이터 찾기 또는 새로 생성
            existing_daily = None
            for daily in monthly_data.daily_list:
                if daily.date == target_date:
                    existing_daily = daily
                    break
            
            # 승인 대기/완료 상태면 수정 불가
            if existing_daily and (existing_daily.is_required or existing_daily.is_confirmed):
                return JsonResponse({'status': 'error', 'message': 'この日の勤怠情報は承認申請中または承認済みのため、修正できません。'})
            
            if existing_daily:
                # 기존 데이터 업데이트
                existing_daily.work_type = work_type
                existing_daily.start_time = start_time
                existing_daily.end_time = end_time
                existing_daily.alternative_work_date1 = alternative_work_date1
                existing_daily.alternative_work_date2 = alternative_work_date2
                existing_daily.alternative_work_date3 = alternative_work_date3
                existing_daily.notes = data.get('notes', '')
                # 시간 계산 실행
                existing_daily.calculate_work_hours()
                print(f"=== 기존 데이터 업데이트 ===")
                print(f"alternative_work_date1: {existing_daily.alternative_work_date1}")
                print(f"alternative_work_date2: {existing_daily.alternative_work_date2}")
                print(f"alternative_work_date3: {existing_daily.alternative_work_date3}")
                print(f"=========================")
                message = '更新しました'
            else:
                # 새 데이터 생성
                # base_calendar가 문자열인 경우 처리
                break_minutes = 60  # 기본값
                standard_work_hours = 8.0  # 기본값
                
                if monthly_data.base_calendar:
                    if hasattr(monthly_data.base_calendar, 'break_minutes'):
                        # Calendar 객체인 경우
                        break_minutes = monthly_data.base_calendar.break_minutes
                        standard_work_hours = monthly_data.base_calendar.standard_work_hours
                    else:
                        # 문자열인 경우 기본값 사용
                        print(f"Warning: base_calendar가 문자열입니다: {monthly_data.base_calendar}")
                
                new_daily = DailyData(
                    date=target_date,
                    work_type=data.get('work_type', '出勤'),
                    start_time=start_time,
                    end_time=end_time,
                    alternative_work_date1=alternative_work_date1,
                    alternative_work_date2=alternative_work_date2,
                    alternative_work_date3=alternative_work_date3,
                    notes=data.get('notes', ''),
                    break_minutes=break_minutes,
                    standard_work_hours=standard_work_hours
                )
                print(f"=== 새 데이터 생성 ===")
                print(f"alternative_work_date1: {new_daily.alternative_work_date1}")
                print(f"alternative_work_date2: {new_daily.alternative_work_date2}")
                print(f"alternative_work_date3: {new_daily.alternative_work_date3}")
                print(f"===================")
                # 시간 계산 실행
                new_daily.calculate_work_hours()
                monthly_data.daily_list.append(new_daily)
                print("Daily data created")
                message = '新規登録しました'
            
            # DB에 저장
            try:
                update_monthly_from_structure(monthly_data, request.user)
                print(f"DB 저장 성공: {message}")
            except Exception as e:
                print(f"DB 저장 실패: {e}")
                import traceback
                traceback.print_exc()
                return JsonResponse({'status': 'error', 'message': f'DB 저장 중 오류가 발생했습니다: {str(e)}'})
            
            # 캐시 무효화 (해당 월의 캐시 삭제)
            invalidate_monthly_cache(
                employee_id=request.user.employee_no,
                year=str(target_date.year),
                month=str(target_date.month)
            )
            
            print(f"Success: {message}")
            return JsonResponse({'status': 'success', 'message': message})
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'JSONデータの解析に失敗しました'})
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)})


# 日別データ取得ビュー（ログ인必須）
@method_decorator(login_required, name='dispatch')
class DailyDataGetView(View):
    def get(self, request, *args, **kwargs):
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'status': 'error', 'message': '日付が指定されていません'})
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # 구조체 기반으로 월별 데이터 가져오기
            monthly_data = get_or_create_monthly_structure(
                employee=request.user,
                year=str(target_date.year),
                month=str(target_date.month)
            )
            
            if not monthly_data:
                return JsonResponse({'status': 'success', 'record': None})
            
            # 해당 날짜의 일별 데이터 찾기
            daily_data = None
            for daily in monthly_data.daily_list:
                if daily.date == target_date:
                    daily_data = daily
                    break
            
            if daily_data:
                record = {
                    'work_type': daily_data.work_type,
                    'start_time': daily_data.start_time.strftime('%H:%M') if daily_data.start_time else '',
                    'end_time': daily_data.end_time.strftime('%H:%M') if daily_data.end_time else '',
                    'alternative_work_date1': daily_data.alternative_work_date1.strftime('%Y-%m-%d') if daily_data.alternative_work_date1 else '',
                    'alternative_work_date2': daily_data.alternative_work_date2.strftime('%Y-%m-%d') if daily_data.alternative_work_date2 else '',
                    'alternative_work_date3': daily_data.alternative_work_date3.strftime('%Y-%m-%d') if daily_data.alternative_work_date3 else '',
                    'notes': daily_data.notes or ''
                }
                return JsonResponse({'status': 'success', 'record': record})
            else:
                return JsonResponse({'status': 'success', 'record': None})
                
        except ValueError:
            return JsonResponse({'status': 'error', 'message': '無効な日付形式です'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})


# 日別勤怠削除ビュー（ログ인必須）
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class DailyAttendanceDeleteView(View):
    def post(self, request, *args, **kwargs):
        print("=== DailyAttendanceDeleteView called ===")
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            
            if not date_str:
                return JsonResponse({'status': 'error', 'message': '日付が指定されていません'})
            
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'status': 'error', 'message': '無効な日付形式です'})
            
            # 구조체 기반으로 월별 데이터 가져오기
            monthly_data = get_or_create_monthly_structure(
                employee=request.user,
                year=str(target_date.year),
                month=str(target_date.month)
            )
            
            if not monthly_data:
                return JsonResponse({'status': 'error', 'message': '該当する月別勤怠情報が見つかりません'})
            
            # 해당 날짜의 일별 데이터 찾기 및 제거
            daily_to_remove = None
            for daily in monthly_data.daily_list:
                if daily.date == target_date:
                    daily_to_remove = daily
                    break
            
            if daily_to_remove:
                monthly_data.daily_list.remove(daily_to_remove)
                
                # DB에서도 삭제
                monthly_model = AttendanceMonthly.objects.filter(
                    employee=request.user,
                    year=str(target_date.year),
                    month=str(target_date.month).zfill(2)
                ).first()
                
                if monthly_model:
                    AttendanceDaily.objects.filter(
                        monthly_attendance=monthly_model,
                        date=target_date
                    ).delete()
                
                # 구조체를 DB에 저장
                update_monthly_from_structure(monthly_data, request.user)
                
                # 캐시 무효화 (해당 월의 캐시 삭제)
                invalidate_monthly_cache(
                    employee_id=request.user.employee_no,
                    year=str(target_date.year),
                    month=str(target_date.month)
                )
                
                return JsonResponse({
                    'status': 'success', 
                    'message': f'{target_date.strftime("%Y年%m月%d日")}の勤怠情報を削除しました。'
                })
            else:
                return JsonResponse({'status': 'error', 'message': '該当する日別勤怠情報が見つかりません'})
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({'status': 'error', 'message': 'JSONデータの解析に失敗しました'})
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)})


# 日別勤怠承認ビュー（ロ그인必須）
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class DailyApproveView(View):
    def post(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            if not date_str:
                return JsonResponse({'status': 'error', 'message': '日付が指定されていません'})
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'status': 'error', 'message': '無効な日付形式です'})
            # 월별 데이터 가져오기
            monthly_data = get_or_create_monthly_structure(
                employee=request.user,
                year=str(target_date.year),
                month=str(target_date.month)
            )
            if not monthly_data:
                return JsonResponse({'status': 'error', 'message': '該当する月別勤怠情報が見つかりません'})
            # 해당 날짜의 일별 데이터 찾기
            daily_data = None
            for daily in monthly_data.daily_list:
                if daily.date == target_date:
                    daily_data = daily
                    break
            if not daily_data:
                return JsonResponse({'status': 'error', 'message': '該当する日別勤怠情報が見つかりません'})
            if daily_data.is_required == 1:
                return JsonResponse({'status': 'error', 'message': 'すでに承認申請中です。'})
            daily_data.is_required = 1
            update_monthly_from_structure(monthly_data, request.user)
            invalidate_monthly_cache(
                employee_id=request.user.employee_no,
                year=str(target_date.year),
                month=str(target_date.month)
            )
            return JsonResponse({'status': 'success', 'message': '承認申請しました。'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@login_required
def attendance_require_day(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            if not date_str:
                return JsonResponse({'status': 'error', 'message': '日付が指定されていません'})
            from datetime import datetime
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            monthly = AttendanceMonthly.objects.filter(
                employee=request.user, year=str(target_date.year), month=str(target_date.month).zfill(2)
            ).first()
            if not monthly:
                return JsonResponse({'status': 'error', 'message': '該当する月別勤怠情報が見つかりません'})
            daily = AttendanceDaily.objects.filter(monthly_attendance=monthly, date=target_date).first()
            if not daily:
                return JsonResponse({'status': 'error', 'message': '該当する日別勤怠情報が見つかりません'})
            daily.is_required = True
            daily.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}) 