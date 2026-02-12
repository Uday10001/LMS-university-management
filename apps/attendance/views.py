from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from apps.accounts.decorators import teacher_required, student_required, management_required
from apps.accounts.models import Student, Teacher
from apps.academic.models import Subject, Section
from .models import ClassSession, Attendance
from .forms import ClassSessionForm, AttendanceMarkingForm, AttendanceFilterForm


# ============================================================================
# TEACHER VIEWS - Attendance Marking
# ============================================================================

@teacher_required
def teacher_dashboard(request):
    """
    Teacher dashboard showing upcoming sessions and quick stats.
    """
    teacher = request.user.teacher_profile
    
    # Get today's sessions
    today_sessions = ClassSession.objects.filter(
        teacher=teacher,
        date=timezone.now().date()
    ).select_related('subject', 'section').order_by('start_time')
    
    # Get upcoming sessions (next 7 days)
    upcoming_sessions = ClassSession.objects.filter(
        teacher=teacher,
        date__gt=timezone.now().date(),
        date__lte=timezone.now().date() + timedelta(days=7)
    ).select_related('subject', 'section').order_by('date', 'start_time')[:10]
    
    # Get recent sessions where attendance is not marked
    pending_sessions = ClassSession.objects.filter(
        teacher=teacher,
        attendance_marked=False,
        date__lte=timezone.now().date()
    ).select_related('subject', 'section').order_by('-date')[:5]
    
    # Stats
    total_sessions = ClassSession.objects.filter(teacher=teacher).count()
    marked_sessions = ClassSession.objects.filter(teacher=teacher, attendance_marked=True).count()
    
    context = {
        'teacher': teacher,
        'today_sessions': today_sessions,
        'upcoming_sessions': upcoming_sessions,
        'pending_sessions': pending_sessions,
        'total_sessions': total_sessions,
        'marked_sessions': marked_sessions,
    }
    
    return render(request, 'attendance/teacher_dashboard.html', context)


@teacher_required
def create_session(request):
    """
    Create a new class session.
    """
    teacher = request.user.teacher_profile
    
    if request.method == 'POST':
        form = ClassSessionForm(request.POST, teacher=teacher)
        if form.is_valid():
            session = form.save(commit=False)
            session.teacher = teacher
            
            # Check if teacher is assigned to this subject and section
            if session.subject not in teacher.subjects.all():
                messages.error(request, 'You are not assigned to this subject.')
                return redirect('attendance:create_session')
            
            if session.section not in teacher.sections.all():
                messages.error(request, 'You are not assigned to this section.')
                return redirect('attendance:create_session')
            
            session.save()
            messages.success(request, f'Session created successfully! You can now mark attendance.')
            return redirect('attendance:mark_attendance', session_id=session.id)
    else:
        form = ClassSessionForm(teacher=teacher)
    
    context = {
        'form': form,
        'teacher': teacher,
    }
    
    return render(request, 'attendance/create_session.html', context)


@teacher_required
def mark_attendance(request, session_id):
    """
    Mark attendance for a specific class session.
    """
    teacher = request.user.teacher_profile
    session = get_object_or_404(ClassSession, id=session_id, teacher=teacher)
    
    # Check if attendance already marked
    if session.attendance_marked:
        messages.warning(request, 'Attendance already marked for this session.')
        return redirect('attendance:view_session_attendance', session_id=session.id)
    
    # Get students from this section
    students = Student.objects.filter(
        section=session.section,
        is_active=True
    ).select_related('user').order_by('roll_number')
    
    if request.method == 'POST':
        form = AttendanceMarkingForm(request.POST, students=students)
        
        if form.is_valid():
            with transaction.atomic():
                # Create attendance records
                for student in students:
                    is_present = form.cleaned_data.get(f'student_{student.id}', False)
                    remarks = form.cleaned_data.get(f'remarks_{student.id}', '')
                    
                    Attendance.objects.create(
                        class_session=session,
                        student=student,
                        is_present=is_present,
                        remarks=remarks.strip()
                    )
                
                # Mark session as completed
                session.attendance_marked = True
                session.save()
            
            messages.success(
                request,
                f'Attendance marked successfully! {session.get_present_count()}/{session.get_total_students()} students present.'
            )
            return redirect('attendance:teacher_dashboard')
    else:
        form = AttendanceMarkingForm(students=students)
    
    context = {
        'form': form,
        'session': session,
        'students': students,
        'total_students': students.count(),
    }
    
    return render(request, 'attendance/mark_attendance.html', context)


@teacher_required
def view_session_attendance(request, session_id):
    """
    View attendance for a specific session (read-only).
    """
    teacher = request.user.teacher_profile
    session = get_object_or_404(ClassSession, id=session_id, teacher=teacher)
    
    attendance_records = Attendance.objects.filter(
        class_session=session
    ).select_related('student', 'student__user').order_by('student__roll_number')
    
    context = {
        'session': session,
        'attendance_records': attendance_records,
        'present_count': session.get_present_count(),
        'absent_count': session.get_absent_count(),
        'total_students': session.get_total_students(),
        'attendance_percentage': session.get_attendance_percentage(),
    }
    
    return render(request, 'attendance/view_session_attendance.html', context)


@teacher_required
def teacher_sessions_list(request):
    """
    List all sessions created by the teacher with filters.
    """
    teacher = request.user.teacher_profile
    
    sessions = ClassSession.objects.filter(
        teacher=teacher
    ).select_related('subject', 'section').order_by('-date', '-start_time')
    
    # Apply filters
    filter_form = AttendanceFilterForm(request.GET)
    
    if filter_form.is_valid():
        subject = filter_form.cleaned_data.get('subject')
        section = filter_form.cleaned_data.get('section')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if subject:
            sessions = sessions.filter(subject=subject)
        if section:
            sessions = sessions.filter(section=section)
        if date_from:
            sessions = sessions.filter(date__gte=date_from)
        if date_to:
            sessions = sessions.filter(date__lte=date_to)
    
    context = {
        'sessions': sessions,
        'filter_form': filter_form,
        'teacher': teacher,
    }
    
    return render(request, 'attendance/teacher_sessions_list.html', context)


# ============================================================================
# STUDENT VIEWS - View Own Attendance
# ============================================================================

@student_required
def student_dashboard(request):
    """
    Student dashboard showing attendance summary and recent records.
    """
    student = request.user.student_profile
    
    # Overall attendance percentage
    overall_percentage = student.get_attendance_percentage()
    
    # Subject-wise attendance
    subjects_attendance = []
    
    # Get all subjects for student's section
    class_sessions = ClassSession.objects.filter(
        section=student.section
    ).values('subject').distinct()
    
    for session in class_sessions:
        subject = Subject.objects.get(id=session['subject'])
        
        total = Attendance.objects.filter(
            student=student,
            class_session__subject=subject
        ).count()
        
        if total > 0:
            present = Attendance.objects.filter(
                student=student,
                class_session__subject=subject,
                is_present=True
            ).count()
            
            percentage = round((present / total) * 100, 2)
            
            subjects_attendance.append({
                'subject': subject,
                'total': total,
                'present': present,
                'absent': total - present,
                'percentage': percentage
            })
    
    # Recent attendance records
    recent_records = Attendance.objects.filter(
        student=student
    ).select_related(
        'class_session',
        'class_session__subject',
        'class_session__teacher',
        'class_session__teacher__user'
    ).order_by('-class_session__date')[:10]
    
    context = {
        'student': student,
        'overall_percentage': overall_percentage,
        'subjects_attendance': subjects_attendance,
        'recent_records': recent_records,
    }
    
    return render(request, 'attendance/student_dashboard.html', context)


@student_required
def student_attendance_detail(request):
    """
    Detailed view of student's attendance with filters.
    """
    student = request.user.student_profile
    
    attendance_records = Attendance.objects.filter(
        student=student
    ).select_related(
        'class_session',
        'class_session__subject',
        'class_session__section',
        'class_session__teacher',
        'class_session__teacher__user'
    ).order_by('-class_session__date')
    
    # Apply filters
    filter_form = AttendanceFilterForm(request.GET)
    
    if filter_form.is_valid():
        subject = filter_form.cleaned_data.get('subject')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if subject:
            attendance_records = attendance_records.filter(class_session__subject=subject)
        if date_from:
            attendance_records = attendance_records.filter(class_session__date__gte=date_from)
        if date_to:
            attendance_records = attendance_records.filter(class_session__date__lte=date_to)
    
    context = {
        'student': student,
        'attendance_records': attendance_records,
        'filter_form': filter_form,
    }
    
    return render(request, 'attendance/student_attendance_detail.html', context)


# ============================================================================
# MANAGEMENT VIEWS - Analytics & Reports
# ============================================================================

@management_required
def management_dashboard(request):
    """
    Management dashboard with overall analytics.
    """
    # Overall stats
    total_students = Student.objects.filter(is_active=True).count()
    total_teachers = Teacher.objects.filter(is_active=True).count()
    total_sessions = ClassSession.objects.count()
    total_attendance_records = Attendance.objects.count()
    
    # Average attendance percentage
    avg_attendance = Attendance.objects.filter(
        is_present=True
    ).count() / total_attendance_records * 100 if total_attendance_records > 0 else 0
    
    # Section-wise attendance
    sections = Section.objects.all()
    section_stats = []
    
    for section in sections:
        students = Student.objects.filter(section=section, is_active=True)
        if students.exists():
            total_records = Attendance.objects.filter(student__in=students).count()
            present_records = Attendance.objects.filter(student__in=students, is_present=True).count()
            
            percentage = round((present_records / total_records * 100), 2) if total_records > 0 else 0
            
            section_stats.append({
                'section': section,
                'student_count': students.count(),
                'total_sessions': total_records,
                'percentage': percentage
            })
    
    # Low attendance students (below 75%)
    low_attendance_students = []
    all_students = Student.objects.filter(is_active=True)
    
    for student in all_students:
        percentage = student.get_attendance_percentage()
        if percentage < 75 and percentage > 0:
            low_attendance_students.append({
                'student': student,
                'percentage': percentage
            })
    
    # Sort by percentage
    low_attendance_students.sort(key=lambda x: x['percentage'])
    
    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_sessions': total_sessions,
        'avg_attendance': round(avg_attendance, 2),
        'section_stats': section_stats,
        'low_attendance_students': low_attendance_students[:20],  # Top 20
    }
    
    return render(request, 'attendance/management_dashboard.html', context)


@management_required
def section_report(request, section_id):
    """
    Detailed report for a specific section.
    """
    section = get_object_or_404(Section, id=section_id)
    
    students = Student.objects.filter(
        section=section,
        is_active=True
    ).select_related('user')
    
    # Calculate attendance for each student
    student_stats = []
    
    for student in students:
        total = Attendance.objects.filter(student=student).count()
        present = Attendance.objects.filter(student=student, is_present=True).count()
        percentage = student.get_attendance_percentage()
        
        student_stats.append({
            'student': student,
            'total': total,
            'present': present,
            'absent': total - present,
            'percentage': percentage
        })
    
    # Sort by percentage (lowest first)
    student_stats.sort(key=lambda x: x['percentage'])
    
    context = {
        'section': section,
        'student_stats': student_stats,
    }
    
    return render(request, 'attendance/section_report.html', context)


@management_required
def subject_report(request, subject_id):
    """
    Detailed report for a specific subject.
    """
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Get all sessions for this subject
    sessions = ClassSession.objects.filter(
        subject=subject,
        attendance_marked=True
    ).select_related('section', 'teacher', 'teacher__user').order_by('-date')
    
    # Calculate stats
    session_stats = []
    
    for session in sessions:
        session_stats.append({
            'session': session,
            'present': session.get_present_count(),
            'absent': session.get_absent_count(),
            'total': session.get_total_students(),
            'percentage': session.get_attendance_percentage()
        })
    
    context = {
        'subject': subject,
        'session_stats': session_stats,
    }
    
    return render(request, 'attendance/subject_report.html', context)