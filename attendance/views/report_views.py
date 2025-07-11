# 리포트 관련 뷰들
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse, HttpResponse
import tempfile
import json

from ..excel_generator import ExcelReportGenerator
from ..pdf_generator import PDFReportGenerator
from django.core.mail import EmailMessage
from django.conf import settings


# エクセルダウンロードビュー（ログイン必須）
@method_decorator(login_required, name='dispatch')
class ExcelDownloadView(View):
    def get(self, request, *args, **kwargs):
        # URLパラメータから年月を取得
        year = request.GET.get('year')
        month = request.GET.get('month')
        
        if not year or not month:
            return JsonResponse({'status': 'error', 'message': '年月が指定されていません'})
        
        try:
            # ExcelReportGeneratorを使用してエクセルファイルを生成
            generator = ExcelReportGenerator(request.user, int(year), int(month))
            workbook = generator.generate_report()
            
            # employee_name을 '이름_사원번호' 형식으로 설정
            employee_name = f"{request.user.display_name}({request.user.employee_no})"
            filename = f"{year}_{month}_稼動報告書_{employee_name}.xlsx"
            
            # レスポンスを作成
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
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
        # URLパラメータから年月を取得
        year = request.GET.get('year')
        month = request.GET.get('month')
        
        if not year or not month:
            return JsonResponse({'status': 'error', 'message': '年月が指定されていません'})
        
        try:
            # PDFReportGeneratorを使用してPDFファイルを生成
            generator = PDFReportGenerator(request.user, int(year), int(month))
            pdf_buffer = generator.generate_pdf()
            
            # employee_name을 '이름_사원번호' 형식으로 설정
            employee_name = f"{request.user.display_name}({request.user.employee_no})"
            filename = f"{year}_{month}_稼動報告書_{employee_name}.pdf"
            
            # レスポンスを作成
            response = HttpResponse(
                content_type='application/pdf'
            )
            
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # iframe에서 표시할 수 있도록 X-Frame-Options 헤더 설정
            response['X-Frame-Options'] = 'SAMEORIGIN'
            
            # PDFデータをレスポンスに書き込み
            response.write(pdf_buffer.getvalue())
            return response
            
        except ValueError as e:
            print(f"ValueError in PDF preview: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            print(f"Error creating PDF file: {e}")
            return JsonResponse({'status': 'error', 'message': f'PDFファイルの作成中にエラーが発生しました: {str(e)}'})


# 이메일 전송 뷰
@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class EmailSendView(View):
    def post(self, request, *args, **kwargs):
        import json
        employee_name = f"{request.user.display_name}({request.user.employee_no})"
        try:
            data = json.loads(request.body)
            email_to = data.get('email')
            file_type = data.get('file_type')
            year = data.get('year')
            month = data.get('month')
            email_host_user = data.get('email_host_user') or settings.EMAIL_HOST_USER
            email_host_password = data.get('email_host_password') or settings.EMAIL_HOST_PASSWORD
            
            if not email_to or not file_type or not year or not month:
                return JsonResponse({'status': 'error', 'message': '必要な情報が不足しています。'})
            # 파일 생성
            if file_type == 'pdf':
                from ..pdf_generator import PDFReportGenerator
                generator = PDFReportGenerator(request.user, int(year), int(month))
                file_buffer = generator.generate_pdf()
                file_ext = 'pdf'
                mime_type = 'application/pdf'
            elif file_type == 'excel':
                generator = ExcelReportGenerator(request.user, int(year), int(month))
                workbook = generator.generate_report()
                file_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                try:
                    print("엑셀 저장 직전")
                    workbook.save(file_buffer.name)
                    print("엑셀 저장 성공")
                except Exception as e:
                    print("엑셀 저장 중 에러:", e)
                file_ext = 'xlsx'
                mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                return JsonResponse({'status': 'error', 'message': 'ファイル種別が不正です。'})
            # 메일 전송
            subject = f"[{employee_name}]{year}年{month}月 稼働報告書"
            body = f"{year}年{month}月の稼働報告書を添付します。"
            
            # 발신자 이메일 설정 (폼에서 입력받은 값 우선, 없으면 사원 이메일, 없으면 기본값)
            from_email = email_host_user if email_host_user else (request.user.email if request.user.email else settings.EMAIL_HOST_USER)
            
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[email_to],
            )

            if file_type == 'pdf':
                filename = f"{year}_{month}_稼働報告書_{employee_name}.pdf"
                email.attach(filename, file_buffer.getvalue(), mime_type)
            else:
                filename = f"{year}_{month}_稼働報告書_{employee_name}.xlsx"
                file_buffer.seek(0)
                email.attach(filename, file_buffer.read(), mime_type)
            
            # 이메일 전송
            email.send(fail_silently=False)
            # 임시파일 정리
            if file_type == 'excel':
                import os
                file_buffer.close()
                os.unlink(file_buffer.name)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': f'送信中にエラーが発生しました: {str(e)}'}) 


 