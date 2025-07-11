from django.contrib import admin
from django.urls import path, include
from attendance.admin import custom_admin_site

urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('attendance/', include(('attendance.urls', 'attendance'), namespace='attendance')),
    path('', include(('attendance.urls', 'attendance_root'), namespace='attendance_root')),
] 