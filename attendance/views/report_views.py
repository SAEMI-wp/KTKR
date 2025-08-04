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
            
            # employee_nameを '名前_社員番号' 形式で設定（括弧をアンダーバーに変換）
            employee_name = f"{request.user.display_name}_{request.user.employee_no}"
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
            
            # employee_nameを '名前_社員番号' 形式で設定（括弧をアンダーバーに変換）
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
        employee_name = f"{request.user.display_name}_{request.user.employee_no}"
        try:
            data = json.loads(request.body)
            email_to = data.get('email')
            file_type = data.get('file_type')
            year = data.get('year')
            month = data.get('month')
            email_host_user = data.get('email_host_user')
            email_host_password = data.get('email_host_password')
            
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
            # メール本文を指定フォーマットで作成
            body = f"""===========================\n提出者：{request.user.display_name}({request.user.employee_no})\n期間：{year}年{int(month):d}月\n添付：稼働報告書\n\nいつもお世話になっております。{int(month):d}月稼働報告書を提出します。\n==========================="""
            
            # 발신자 이메일 설정 (폼에서 입력받은 값만 사용)
            if not email_host_user:
                return JsonResponse({'status': 'error', 'message': '発信者メールを入力してください。'})
            if not email_host_password:
                return JsonResponse({'status': 'error', 'message': 'アプリのパスワードを入力してください。'})
            
            from_email = email_host_user
            
            print('send_mail_dynamic 호출 전', flush=True)
            month_str = f"{int(month):02d}"
            # 첨부파일 데이터 준비
            if file_type == 'pdf':
                # 月を必ず2桁で表示（ゼロ埋め）
                filename = f"Attendance Report({year}_{month_str})_{request.user.employee_no}.pdf"
                attachment_data = file_buffer.getvalue()
            else:
                filename = f"Attendance Report({year}_{month_str})_{request.user.employee_no}.xlsx"
                file_buffer.seek(0)
                attachment_data = file_buffer.read()

            # send_mail_dynamic 함수 호출 (utils에서 import 필요)
            from attendance.utils import send_mail_dynamic
            try:
                send_mail_dynamic(
                    user=from_email,
                    password=email_host_password,
                    to_email=email_to,
                    subject=subject,
                    body=body,
                    attachment=attachment_data,
                    attachment_filename=filename,
                    mime_type=mime_type
                )
            except Exception as e:
                raise
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


 