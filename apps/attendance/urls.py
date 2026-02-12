from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Teacher URLs
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/create-session/', views.create_session, name='create_session'),
    path('teacher/mark/<int:session_id>/', views.mark_attendance, name='mark_attendance'),
    path('teacher/session/<int:session_id>/', views.view_session_attendance, name='view_session_attendance'),
    path('teacher/sessions/', views.teacher_sessions_list, name='teacher_sessions_list'),
    
    # Student URLs
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/detail/', views.student_attendance_detail, name='student_attendance_detail'),
    
    # Management URLs
    path('management/dashboard/', views.management_dashboard, name='management_dashboard'),
    path('management/section/<int:section_id>/', views.section_report, name='section_report'),
    path('management/subject/<int:subject_id>/', views.subject_report, name='subject_report'),
]