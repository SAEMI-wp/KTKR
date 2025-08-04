from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    MainView, MonthlyAttendanceCreateView, MonthlyAttendanceUpdateView, DailyDataUpdateView, DailyDataGetView,
    login_view, logout_view, MonthlyAttendanceDeleteView, DailyAttendanceDeleteView, ExcelDownloadView, PDFPreviewView, EmailSendView, password_change_view, copy_prev_month, DailyApproveView,
    CalendarPartialView, FormPartialView, MonthlyInfoSectionView
)
from .views import attendance_require_day
from .views.utility_views import email_candidates


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
    path('attendance/require_day/', attendance_require_day, name='attendance_require_day'),
    path('api/email_candidates/', email_candidates, name='email_candidates'),  # 推奨メール受信者API
    # TTL 기반 캐시 사용으로 인해 수동 캐시 초기화 API 제거
    # path('api/clear_cache/', clear_cache, name='clear_cache'),  # 캐시 초기화 API
    
    # ===================== AJAX용 Partial 뷰들 =====================
    path('calendar_partial/', CalendarPartialView.as_view(), name='calendar_partial'),
    path('form_partial/', FormPartialView.as_view(), name='form_partial'),
    path('monthly-info/section/', MonthlyInfoSectionView.as_view(), name='monthly_info_section'),
]

# 개발 환경에서 static 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 