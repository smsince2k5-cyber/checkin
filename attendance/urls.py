from django.urls import path
from . import views

urlpatterns = [path('', views.home, name='home'),

    path('enroll/', views.enroll_employee, name='enroll_employee'),
    path('checkin/', views.check_in, name='checkin'),
    path('checkout/', views.check_out, name='checkout'),
    path("attendance/<int:emp_id>/", views.attendance_calendar, name="attendance_calendar"),
    path("login/", views.login_phone, name="login_phone"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("attendance/<int:emp_id>/", views.attendance_calendar, name="attendance_calendar"),
]