from django.urls import path
from core import views

app_name = "courses"

urlpatterns = [
    path('', views.CourseListView.as_view(), name='popular_course_list'),
    path('date/', views.get_date, name='date'),
    path('<int:course_id>/enroll/', views.EnrollView.as_view(), name='enroll'),
    path('<int:course_id>/', views.CourseDetailsView.as_view(), name="course"),
    path('logout/', views.logout_request, name="logout"),
    path('login/', views.login_request, name='login'),
    path('registration/', views.registration_request, name='registration'),
]

# urlpatterns = [
#     path('', views.CourseListView.as_view(), name="course")
# ]
