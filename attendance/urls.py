from django.urls import path
from . import views

urlpatterns = [path('', views.home, name='home'),

    path('enroll/', views.enroll_employee, name='enroll_employee'),
    path('checkin/', views.check_in, name='checkin'),
    path('checkout/', views.check_out, name='checkout'),
]
