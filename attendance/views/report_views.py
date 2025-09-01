# 리포트 관련 뷰들
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
import tempfile
import json
import threading
import time

from ..excel_generator import ExcelReportGenerator
from ..pdf_generator import PDFReportGenerator
from ..models import Employee
from django.core.mail import EmailMessage
from django.conf import settings
import urllib.parse


def create_edge_compatible_filename(filename):
    """
    Microsoft Edge에서 파일명이 제대로 표시되도록 인코딩을 처리합니다.
    """
    
    # ASCII 전용 파일명 생성 (Edge 호환성)
    ascii_filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # UTF-8 인코딩된 파일명
    utf8_filename = urllib.parse.quote(filename.encode('utf-8'))
    
    # Edge 호환 Content-Disposition 헤더 생성
    content_disposition = (
        f'attachment; filename="{ascii_filename}"; '
        f'filename*=UTF-8\'\'{utf8_filename}'
    )
    
    return content_disposition


def send_email_async(user_email, user_password, to_email, subject, body, attachment_data, filename, mime_type):
    """비동기로 메일을 전송하는 함수"""
    def email_worker():
        try:
            print(f"비동기 메일 전송 시작 - From: {user_email}, To: {to_email}", flush=True)
            print(f"첨부파일: {filename}, 크기: {len(attachment_data)} bytes", flush=True)
            
            from attendance.utils import send_mail_dynamic
            
            send_mail_dynamic(
                user=user_email,
                password=user_password,
                to_email=to_email,
                subject=subject,
                body=body,
                attachment=attachment_data,
                attachment_filename=filename,
                mime_type=mime_type
            )
            print("비동기 메일 전송 성공", flush=True)
        except Exception as e:
            print(f"비동기 메일 전송 실패: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
    
    # 별도 스레드에서 실행
    thread = threading.Thread(target=email_worker)
    thread.daemon = True
    thread.start()


# エクセルダウンロードビュー（ログイン必須）
@method_decorator(login_required, name='dispatch')
class ExcelDownloadView(View):
    def get(self, request, *args, **kwargs):
        # URLパラメータから年月을 取得
        year = request.GET.get('year')
        month = request.GET.get('month')
        employee_no = request.GET.get('employee_no')
        
        if not year or not month:
            return JsonResponse({'status': 'error', 'message': '年月が指定されていません'})
        
        # 대상 직원 결정
        if employee_no:
            # 관리자 권한 체크
            if not request.user.has_perm('attendance.can_access_admin'):
                return JsonResponse({'status': 'error', 'message': '権限がありません。'})
            target_employee = get_object_or_404(Employee, employee_no=employee_no)
        else:
            target_employee = request.user
        
        try:
            # ExcelReportGeneratorを使用してエクセルファイルを生成
            generator = ExcelReportGenerator(target_employee, int(year), int(month))
            workbook = generator.generate_report()
            
            # employee_nameを '名前_社員番号' 형식で設정（括弧をアンダーバーに変환）
            employee_name = f"{target_employee.display_name}_{target_employee.employee_no}"
            filename = f"{year}_{month}_稼動報告書_{employee_name}.xlsx"
            
            # レスポンスを作成
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            # Edge 호환 Content-Disposition 헤더 설정
            response['Content-Disposition'] = create_edge_compatible_filename(filename)
            
            # 추가 헤더로 Edge 호환성 향상
            response['Cache-Control'] = 'no-cache'
            response['Pragma'] = 'no-cache'
            
            # 엑셀 저장 직전
            print("엑셀 저장 직전")
            workbook.save(response)
            print("엑셀 저장 성공")
            return response
            
        except ValueError as e:
            print(f"ValueError in Excel download: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            print(f"Error creating Excel file: {e}")
            return JsonResponse({'status': 'error', 'message': f'エクセルファイルの作成中にエラーが発生しました: {str(e)}'})


# PDF 미리보기 뷰（ログ인必須）
@method_decorator(login_required, name='dispatch')
class PDFPreviewView(View):
    def get(self, request, *args, **kwargs):
        # URLパラメータから年月을 取得
        year = request.GET.get('year')
        month = request.GET.get('month')
        employee_no = request.GET.get('employee_no')
        
        if not year or not month:
            return JsonResponse({'status': 'error', 'message': '年月が指定されていません'})
        
        # 대상 직원 결정
        if employee_no:
            # 관리자 권한 체크
            if not request.user.has_perm('attendance.can_access_admin'):
                return JsonResponse({'status': 'error', 'message': '権限がありません。'})
            target_employee = get_object_or_404(Employee, employee_no=employee_no)
        else:
            target_employee = request.user
        
        try:
            # PDFReportGeneratorを使用してPDFファイルを生成
            generator = PDFReportGenerator(target_employee, int(year), int(month))
            pdf_buffer = generator.generate_pdf()
            
            # employee_nameを '名前_社員番号' 형식で설정（括弧をアンダーバーに変환）
            employee_name = f"{target_employee.display_name}({target_employee.employee_no})"
            filename = f"{year}_{month}_稼動報告書_{employee_name}.pdf"
            
            # レスポンスを作成
            response = HttpResponse(
                content_type='application/pdf'
            )
            
            # Edge 호환 Content-Disposition 헤더 설정 (inline + filename)
            response['Content-Disposition'] = f'inline; filename="{filename}"; filename*=UTF-8\'\'{urllib.parse.quote(filename.encode("utf-8"))}'
            
            # iframe에서 표시할 수 있도록 X-Frame-Options 헤더 설정
            response['X-Frame-Options'] = 'SAMEORIGIN'
            
            # 추가 헤더로 Edge 호환성 향상
            response['Cache-Control'] = 'no-cache'
            response['Pragma'] = 'no-cache'
            
            # PDFデータをレスポンスに書き込み
            response.write(pdf_buffer.getvalue())
            return response
            
        except ValueError as e:
            print(f"ValueError in PDF preview: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            print(f"Error creating PDF file: {e}")
            return JsonResponse({'status': 'error', 'message': f'PDFファイルの作成中にエラーが発生しました: {str(e)}'})


# PDF 다운로드 뷰（ログ인必須）
@method_decorator(login_required, name='dispatch')
class PDFDownloadView(View):
    def get(self, request, *args, **kwargs):
        # URLパラメータから年月을 取得
        year = request.GET.get('year')
        month = request.GET.get('month')
        employee_no = request.GET.get('employee_no')
        
        if not year or not month:
            return JsonResponse({'status': 'error', 'message': '年月が指定されていません'})
        
        # 대상 직원 결정
        if employee_no:
            # 관리자 권한 체크
            if not request.user.has_perm('attendance.can_access_admin'):
                return JsonResponse({'status': 'error', 'message': '권한がありません。'})
            target_employee = get_object_or_404(Employee, employee_no=employee_no)
        else:
            target_employee = request.user
        
        try:
            # PDFReportGeneratorを使用してPDFファイルを生成
            generator = PDFReportGenerator(target_employee, int(year), int(month))
            pdf_buffer = generator.generate_pdf()
            
            # employee_nameを '名前_社員番号' 형식で설정（括弧をアンダーバーに変換）
            employee_name = f"{target_employee.display_name}({target_employee.employee_no})"
            filename = f"{year}_{month}_稼動報告書_{employee_name}.pdf"
            
            # レスポンスを作成
            response = HttpResponse(
                content_type='application/pdf'
            )
            
            # Edge 호환 Content-Disposition 헤더 설정
            response['Content-Disposition'] = create_edge_compatible_filename(filename)
            
            # 추가 헤더로 Edge 호환성 향상
            response['Cache-Control'] = 'no-cache'
            response['Pragma'] = 'no-cache'
            
            # PDFデータをレスポンスに書き込み
            response.write(pdf_buffer.getvalue())
            return response
            
        except ValueError as e:
            print(f"ValueError in PDF download: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            print(f"Error creating PDF file: {e}")
            return JsonResponse({'status': 'error', 'message': f'PDFファイルの作成中にエラーが発生しました: {str(e)}'})


# メール送信ビュー
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class EmailSendView(View):
    def post(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            email_to = data.get('email')
            file_type = data.get('file_type')
            year = data.get('year')
            month = data.get('month')
            email_host_user = data.get('email_host_user')
            email_host_password = data.get('email_host_password')
            employee_no = data.get('employee_no')
            
            if not email_to or not file_type or not year or not month:
                return JsonResponse({'status': 'error', 'message': '必要な情報が不足しています。'})
            
            # 대상 직원 결정
            if employee_no:
                # 관리자 권한 체크
                if not request.user.has_perm('attendance.can_access_admin'):
                    return JsonResponse({'status': 'error', 'message': '権限がありません。'})
                target_employee = get_object_or_404(Employee, employee_no=employee_no)
            else:
                target_employee = request.user
            
            employee_name = f"{target_employee.display_name}_{target_employee.employee_no}"
            
            # ファイル生成
            if file_type == 'pdf':
                from ..pdf_generator import PDFReportGenerator
                generator = PDFReportGenerator(target_employee, int(year), int(month))
                file_buffer = generator.generate_pdf()
                file_ext = 'pdf'
                mime_type = 'application/pdf'
            elif file_type == 'excel':
                try:
                    print("Excel生成開始", flush=True)
                    generator = ExcelReportGenerator(target_employee, int(year), int(month))
                    
                    # Excel 생성 시간 측정
                    start_time = time.time()
                    workbook = generator.generate_report()
                    generation_time = time.time() - start_time
                    print(f"Excel生成完了 (소요시간: {generation_time:.2f}초)", flush=True)
                    
                    # 메모리 사용량 최적화: BytesIO 사용
                    from io import BytesIO
                    file_buffer = BytesIO()
                    workbook.save(file_buffer)
                    file_buffer.seek(0)
                    print("Excel메모리 저장 성공", flush=True)
                    
                    file_ext = 'xlsx'
                    mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                except Exception as e:
                    print(f"Excel生成中のエラー: {str(e)}", flush=True)
                    import traceback
                    traceback.print_exc()
                    return JsonResponse({'status': 'error', 'message': f'Excelファイルの生成に失敗しました: {str(e)}'})
            else:
                return JsonResponse({'status': 'error', 'message': 'ファイル種別が不正です。'})
            # メール送信
            subject = f"[{employee_name}]{year}年{month}月 稼働報告書"
            # メール本文を指定フォーマットで作成
            body = f"""===========================\n提出者：{target_employee.display_name}({target_employee.employee_no})\n期間：{year}年{int(month):d}月\n添付：稼働報告書\n\nいつもお世話になっております。{int(month):d}月稼働報告書を提出します。\n==========================="""
            
            # 送信者メールを設定 (フォームから入力された値のみ使用)
            if not email_host_user:
                return JsonResponse({'status': 'error', 'message': '発信者メールを入力してください。'})
            if not email_host_password:
                return JsonResponse({'status': 'error', 'message': 'アプリのパスワードを入力してください。'})
            
            from_email = email_host_user
            
            print('첨부파일 데이터 준비 시작', flush=True)
            month_str = f"{int(month):02d}"
            # 添付ファイルデータを準備
            if file_type == 'pdf':
                # 月を必ず2桁で表示（ゼロ埋め）
                filename = f"Attendance Report({year}_{month_str})_{target_employee.employee_no}.pdf"
                attachment_data = file_buffer.getvalue()
            else:
                filename = f"Attendance Report({year}_{month_str})_{target_employee.employee_no}.xlsx"
                attachment_data = file_buffer.getvalue()  # BytesIO에서 바로 가져오기
            
            print(f"첨부파일 크기: {len(attachment_data)} bytes", flush=True)

            # 비동기로 메일 전송 (즉시 응답 반환)
            print(f"비동기 메일 전송 요청 - From: {from_email}, To: {email_to}", flush=True)
            
            # Excel의 경우 BytesIO를 사용하므로 임시 파일 불필요
            temp_file_path = None
            
            # 비동기 메일 전송 시작
            send_email_async(
                user_email=from_email,
                user_password=email_host_password,
                to_email=email_to,
                subject=subject,
                body=body,
                attachment_data=attachment_data,
                filename=filename,
                mime_type=mime_type
            )
            
            print("비동기 메일 전송 작업 시작됨 - 즉시 응답 반환", flush=True)
            return JsonResponse({'status': 'success', 'message': 'メール送信を開始しました。送信完了まで少々お待ちください。'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': f'送信中にエラーが発生しました: {str(e)}'}) 


 