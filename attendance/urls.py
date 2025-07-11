from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    MainView, MonthlyAttendanceCreateView, MonthlyAttendanceUpdateView, DailyDataUpdateView, DailyDataGetView,
    login_view, logout_view, MonthlyAttendanceDeleteView, DailyAttendanceDeleteView, ExcelDownloadView, PDFPreviewView, EmailSendView, password_change_view, copy_prev_month, DailyApproveView #, signup_view
)
from .views import attendance_require_day


app_name = 'attendance'

urlpatterns = [
    path('', MainView.as_view(), name='main'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('monthly/create/', MonthlyAttendanceCreateView.as_view(), name='monthly_create'),
    path('monthly/update/', MonthlyAttendanceUpdateView.as_view(), name='monthly_update'),
    path('monthly/delete/', MonthlyAttendanceDeleteView.as_view(), name='monthly_delete'),
    path('daily/update/', DailyDataUpdateView.as_view(), name='daily_update'),
    path('daily/get/', DailyDataGetView.as_view(), name='daily_get'),
    path('daily/delete/', DailyAttendanceDeleteView.as_view(), name='daily_delete'),
    path('daily/approve/', DailyApproveView.as_view(), name='daily_approve'),
    path('excel/download/', ExcelDownloadView.as_view(), name='excel_download'),
    path('pdf/preview/', PDFPreviewView.as_view(), name='pdf_preview'),
    path('email/send/', EmailSendView.as_view(), name='email_send'),
    path('password_change/', password_change_view, name='password_change'),
    path('copy_prev_month/', copy_prev_month, name='copy_prev_month'),
    path('daily/approve/', DailyApproveView.as_view(), name='daily_approve'),
    path('attendance/require_day/', attendance_require_day, name='attendance_require_day'),

]

# 개발 환경에서 static 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 