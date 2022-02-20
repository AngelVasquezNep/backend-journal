from django.urls import path
from core import views

app_name = "courses"

urlpatterns = [
    path('', views.index, name='course_list'),
    path('date/', views.get_date, name='date'),
    path('<int:course_id>/enroll/', views.enroll, name='enroll'),
]
