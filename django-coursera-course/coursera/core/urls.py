from django.urls import path
from core import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('date/', views.get_date, name='date'),
]
