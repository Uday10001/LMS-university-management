from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # ── Teacher ───────────────────────────────────────────────
    path('teacher/dashboard/',
         views.teacher_dashboard,
         name='teacher_dashboard'),

    path('teacher/timetable/',
         views.teacher_timetable,
         name='teacher_timetable'),

    path('teacher/request-change/',
         views.request_timetable_change,
         name='request_timetable_change'),

    path('teacher/mark/<int:session_id>/',
         views.mark_attendance,
         name='mark_attendance'),

    path('teacher/session/<int:session_id>/',
         views.view_session_attendance,
         name='view_session_attendance'),

    path('teacher/sessions/',
         views.teacher_sessions_list,
         name='teacher_sessions_list'),

    # ── Student ───────────────────────────────────────────────
    path('student/dashboard/',
         views.student_dashboard,
         name='student_dashboard'),

    path('student/detail/',
         views.student_attendance_detail,
         name='student_attendance_detail'),

    path('student/schedule/',
         views.student_schedule,
         name='student_schedule'),

    path('student/timetable/',
         views.student_timetable,
         name='student_timetable'),

    # ── Management ────────────────────────────────────────────
    path('management/dashboard/',
         views.management_dashboard,
         name='management_dashboard'),

    path('management/timetable/',
         views.management_timetable,
         name='management_timetable'),

    path('management/timetable/review/<int:request_id>/',
         views.review_change_request,
         name='review_change_request'),

    path('management/section/<int:section_id>/',
         views.section_report,
         name='section_report'),

    path('management/subject/<int:subject_id>/',
         views.subject_report,
         name='subject_report'),
]