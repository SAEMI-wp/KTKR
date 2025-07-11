# views 패키지 초기화 파일
# 모든 뷰 모듈을 import하여 기존 views.py와 동일한 인터페이스 제공

from .auth_views import (
    login_view,
    logout_view,
    password_change_view,
    signup_view,
    PasswordChangeForm
)

from .main_views import MainView

from .monthly_views import (
    MonthlyAttendanceCreateView,
    MonthlyAttendanceUpdateView,
    MonthlyAttendanceDeleteView,
    MonthlyBulkInfoView
)

from .daily_views import (
    DailyDataUpdateView,
    DailyDataGetView,
    DailyAttendanceDeleteView,
    DailyApproveView,
    attendance_require_day
)

from .report_views import (
    ExcelDownloadView,
    PDFPreviewView,
    EmailSendView
)

from .utility_views import copy_prev_month

__all__ = [
    # Auth views
    'login_view',
    'logout_view', 
    'password_change_view',
    'signup_view',
    'PasswordChangeForm',
    
    # Main views
    'MainView',
    
    # Monthly views
    'MonthlyAttendanceCreateView',
    'MonthlyAttendanceUpdateView', 
    'MonthlyAttendanceDeleteView',
    'MonthlyBulkInfoView',
    
    # Daily views
    'DailyDataUpdateView',
    'DailyDataGetView',
    'DailyAttendanceDeleteView',
    'DailyApproveView',
    
    # Report views
    'ExcelDownloadView',
    'PDFPreviewView',
    'EmailSendView',
    
    # Utility views
    'copy_prev_month',
    'attendance_require_day'
] 