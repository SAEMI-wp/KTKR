from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from attendance.admin import custom_admin_site

urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('attendance/', include(('attendance.urls', 'attendance'), namespace='attendance')),
    path('', include(('attendance.urls', 'attendance_root'), namespace='attendance_root')),
    path('favicon.ico', RedirectView.as_view(url='/static/attendance/favicon.ico', permanent=True)),
]

# 開発環境での静的ファイル提供
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 