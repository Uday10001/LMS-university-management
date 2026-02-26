from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .forms import RemedialClassForm
from apps.accounts.decorators import teacher_required, student_required, management_required
from apps.accounts.models import Student, Teacher
from apps.academic.models import Subject, Section
from .models import ClassSession, Attendance
from .forms import ClassSessionForm, AttendanceMarkingForm, AttendanceFilterForm


# ============================================================================
# TEACHER VIEWS - Attendance Marking
# ============================================================================


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


# ============================================================================
# MANAGEMENT VIEWS - Analytics & Reports
# ============================================================================

@management_required
def section_report(request, section_id):
    """
    Detailed attendance report for a specific section.
    Shows per-student stats, subject breakdown, and trend data.
    """
    section = get_object_or_404(Section, id=section_id)

    students = Student.objects.filter(
        section=section,
        is_active=True
    ).select_related('user').order_by('roll_number')

    # Get all subjects taught in this section
    subjects_in_section = Subject.objects.filter(
        class_sessions__section=section
    ).distinct()

    # ── Per-student stats ──────────────────────────────────
    student_stats = []

    for student in students:
        total = Attendance.objects.filter(
            student=student
        ).count()

        present = Attendance.objects.filter(
            student=student,
            is_present=True
        ).count()

        absent = total - present
        percentage = round((present / total * 100), 2) if total > 0 else 0

        # Status flag
        if percentage >= 75:
            status = 'good'
        elif percentage >= 50:
            status = 'warning'
        else:
            status = 'danger'

        # Subject-wise breakdown for this student
        subject_breakdown = []
        for subject in subjects_in_section:
            s_total = Attendance.objects.filter(
                student=student,
                class_session__subject=subject
            ).count()

            if s_total > 0:
                s_present = Attendance.objects.filter(
                    student=student,
                    class_session__subject=subject,
                    is_present=True
                ).count()
                s_pct = round((s_present / s_total * 100), 1)
            else:
                s_present = 0
                s_pct = 0

            subject_breakdown.append({
                'subject': subject,
                'present': s_present,
                'total': s_total,
                'percentage': s_pct,
            })

        student_stats.append({
            'student': student,
            'total': total,
            'present': present,
            'absent': absent,
            'percentage': percentage,
            'status': status,
            'subject_breakdown': subject_breakdown,
        })

    # Sort: lowest attendance first by default
    sort_by = request.GET.get('sort', 'percentage_asc')
    if sort_by == 'percentage_desc':
        student_stats.sort(key=lambda x: x['percentage'], reverse=True)
    elif sort_by == 'name':
        student_stats.sort(key=lambda x: x['student'].user.get_full_name())
    elif sort_by == 'roll':
        student_stats.sort(key=lambda x: x['student'].roll_number)
    else:
        student_stats.sort(key=lambda x: x['percentage'])

    # ── Section-level summary ──────────────────────────────
    total_students = len(student_stats)
    good_count    = sum(1 for s in student_stats if s['status'] == 'good')
    warning_count = sum(1 for s in student_stats if s['status'] == 'warning')
    danger_count  = sum(1 for s in student_stats if s['status'] == 'danger')

    avg_percentage = round(
        sum(s['percentage'] for s in student_stats) / total_students, 2
    ) if total_students > 0 else 0

    total_sessions = ClassSession.objects.filter(
        section=section,
        attendance_marked=True
    ).count()

    # ── Subject-level summary ──────────────────────────────
    subject_stats = []
    for subject in subjects_in_section:
        sessions = ClassSession.objects.filter(
            section=section,
            subject=subject,
            attendance_marked=True
        ).count()

        s_total   = Attendance.objects.filter(
            student__section=section,
            class_session__subject=subject
        ).count()

        s_present = Attendance.objects.filter(
            student__section=section,
            class_session__subject=subject,
            is_present=True
        ).count()

        s_pct = round((s_present / s_total * 100), 1) if s_total > 0 else 0

        subject_stats.append({
            'subject': subject,
            'sessions': sessions,
            'present': s_present,
            'total': s_total,
            'percentage': s_pct,
        })

    subject_stats.sort(key=lambda x: x['percentage'])

    # ── All sections for sidebar navigation ───────────────
    all_sections = Section.objects.all().order_by('semester', 'code')

    context = {
        'section': section,
        'student_stats': student_stats,
        'subject_stats': subject_stats,
        'subjects_in_section': subjects_in_section,
        'total_students': total_students,
        'good_count': good_count,
        'warning_count': warning_count,
        'danger_count': danger_count,
        'avg_percentage': avg_percentage,
        'total_sessions': total_sessions,
        'sort_by': sort_by,
        'all_sections': all_sections,
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

@student_required
def student_attendance_detail(request):
    """
    Detailed attendance view with filters and statistics.
    """
    student = request.user.student_profile

    # Base queryset - optimized with select_related
    attendance_records = Attendance.objects.filter(
        student=student
    ).select_related(
        'class_session',
        'class_session__subject',
        'class_session__section',
        'class_session__teacher',
        'class_session__teacher__user'
    ).order_by('-class_session__date', '-class_session__start_time')

    # Apply filters
    subject_id = request.GET.get('subject')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if subject_id:
        attendance_records = attendance_records.filter(
            class_session__subject__id=subject_id
        )
    if status == 'present':
        attendance_records = attendance_records.filter(is_present=True)
    elif status == 'absent':
        attendance_records = attendance_records.filter(is_present=False)
    if date_from:
        attendance_records = attendance_records.filter(
            class_session__date__gte=date_from
        )
    if date_to:
        attendance_records = attendance_records.filter(
            class_session__date__lte=date_to
        )

    # Overall stats
    all_records = Attendance.objects.filter(student=student)
    total = all_records.count()
    present = all_records.filter(is_present=True).count()
    absent = total - present
    overall_percentage = round((present / total * 100), 2) if total > 0 else 0

    # Calculate classes needed or can miss
    if overall_percentage < 75:
        # Formula: (present + x) / (total + x) = 0.75
        # Solving: x = (0.75 * total - present) / 0.25
        classes_needed = max(0, int((0.75 * total - present) / 0.25) + 1)
    else:
        classes_needed = 0

    # Formula: (present) / (total + x) = 0.75
    # Solving: x = present/0.75 - total
    can_miss = max(0, int(present / 0.75) - total)

    overall_stats = {
        'total': total,
        'present': present,
        'absent': absent,
        'overall_percentage': overall_percentage,
        'classes_needed': classes_needed,
        'can_miss': can_miss,
    }

    # Subject-wise attendance
    subjects_attendance = []
    class_sessions = ClassSession.objects.filter(
        section=student.section
    ).values('subject').distinct()

    for session_data in class_sessions:
        from apps.academic.models import Subject
        subject = Subject.objects.get(id=session_data['subject'])

        subject_total = Attendance.objects.filter(
            student=student,
            class_session__subject=subject
        ).count()

        if subject_total > 0:
            subject_present = Attendance.objects.filter(
                student=student,
                class_session__subject=subject,
                is_present=True
            ).count()
            percentage = round((subject_present / subject_total) * 100, 2)

            subjects_attendance.append({
                'subject': subject,
                'present': subject_present,
                'absent': subject_total - subject_present,
                'total': subject_total,
                'percentage': percentage
            })

    # Sort by percentage ascending (worst first)
    subjects_attendance.sort(key=lambda x: x['percentage'])

    context = {
        'student': student,
        'attendance_records': attendance_records,
        'subjects_attendance': subjects_attendance,
        'overall_stats': overall_stats,
    }

    return render(request, 'attendance/student_attendance_detail.html', context)

from datetime import timedelta, date
from django.utils import timezone
from collections import defaultdict



@student_required
def student_schedule(request):
    """
    Weekly schedule view showing all class sessions for the student's section.
    """
    student = request.user.student_profile
    today = timezone.now().date()
    week_offset = int(request.GET.get('week', 0))

    # Find Monday of the target week
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=4)  # Friday

    week_days = [week_start + timedelta(days=i) for i in range(5)]

    # Fetch all sessions for this section in this week
    sessions = ClassSession.objects.filter(
        section=student.section,
        date__range=[week_start, week_end]
    ).select_related(
        'subject',
        'teacher',
        'teacher__user',
        'section'
    ).order_by('date', 'start_time')

    # Build attendance lookup: {session_id: Attendance record}
    attendance_map = {}
    if sessions.exists():
        attendance_records = Attendance.objects.filter(
            student=student,
            class_session__in=sessions
        ).select_related('class_session')

        for record in attendance_records:
            attendance_map[record.class_session.id] = record

    # ----------------------------------------------------------------
    # Pre-compute status for each session IN THE VIEW (not template)
    # status choices: 'present', 'absent', 'pending', 'future'
    # ----------------------------------------------------------------
    sessions_by_day = defaultdict(list)

    for session in sessions:
        attendance = attendance_map.get(session.id)
        is_past = session.date < today

        if attendance:
            if attendance.is_present:
                status = 'present'
                status_text = 'Present'
            else:
                status = 'absent'
                status_text = 'Absent'
        elif is_past:
            status = 'pending'
            status_text = 'Pending'
        else:
            status = 'future'
            status_text = 'Scheduled'

        sessions_by_day[session.date].append({
            'session': session,
            'attendance': attendance,
            'status': status,
            'status_text': status_text,
        })

    # Build week data list
    week_data = []
    for day in week_days:
        day_sessions = sessions_by_day.get(day, [])
        week_data.append({
            'date': day,
            'day_name': day.strftime('%A'),
            'short_day': day.strftime('%a'),
            'day_num': day.strftime('%d'),
            'month': day.strftime('%b'),
            'is_today': day == today,
            'is_past': day < today,
            'sessions': day_sessions,
            'session_count': len(day_sessions),
        })

    # Upcoming sessions (today onwards, next 7 days)
    upcoming = ClassSession.objects.filter(
        section=student.section,
        date__gte=today,
        date__lte=today + timedelta(days=7)
    ).select_related(
        'subject', 'teacher', 'teacher__user'
    ).order_by('date', 'start_time')[:5]

    # Tag upcoming sessions with is_today
    upcoming_list = []
    for session in upcoming:
        upcoming_list.append({
            'session': session,
            'is_today': session.date == today,
        })

    context = {
        'student': student,
        'week_data': week_data,
        'week_start': week_start,
        'week_end': week_end,
        'week_offset': week_offset,
        'today': today,
        'upcoming_list': upcoming_list,
        'prev_week': week_offset - 1,
        'next_week': week_offset + 1,
    }

    return render(request, 'attendance/student_schedule.html', context)
from apps.academic.models import TimetableSlot
from django.db import models as django_models


# ── STUDENT: Personal timetable (read-only) ──────────────────

@student_required
def student_timetable(request):
    """
    Student sees their section's fixed weekly timetable.
    """
    student = request.user.student_profile
    today   = timezone.now().date()

    slots = TimetableSlot.objects.filter(
        section=student.section,
        is_active=True
    ).select_related(
        'subject', 'teacher', 'teacher__user'
    ).order_by('day_of_week', 'start_time')

    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    timetable_by_day = {day: [] for day in days}
    for slot in slots:
        timetable_by_day[slot.get_day_of_week_display()].append(slot)

    # Today's sessions for quick view
    today_sessions = ClassSession.objects.filter(
        section=student.section,
        date=today
    ).select_related('subject', 'teacher', 'teacher__user').order_by('start_time')

    context = {
        'student': student,
        'timetable_by_day': timetable_by_day,
        'days': days,
        'today': today,
        'today_sessions': today_sessions,
    }
    return render(request, 'attendance/student_timetable.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date
from collections import defaultdict

from apps.accounts.decorators import (
    teacher_required, student_required, management_required
)
from apps.accounts.models import Student, Teacher
from apps.academic.models import Section, Subject, TimetableSlot, TimetableChangeRequest
from .models import ClassSession, Attendance
from .forms import AttendanceMarkingForm, AttendanceFilterForm


# ─────────────────────────────────────────────────────────────
# SHARED HELPER
# ─────────────────────────────────────────────────────────────

from django.db.models import Q

def _ensure_sessions_exist(teacher, days_back=30):
    """
    Lazily generate ClassSessions for the past N days and today
    so teachers can always find unmarked sessions.
    Called on teacher dashboard load.
    """
    today = timezone.now().date()
    start = today - timedelta(days=days_back)

    for offset in range(days_back + 1):
        target = start + timedelta(days=offset)
        weekday = target.weekday()  # 0=Monday, 6=Sunday
        
        # Skip Sundays (not in DAY_CHOICES)
        if weekday == 6:
            continue

        # Get all active slots for this teacher on this day of week
        slots = TimetableSlot.objects.filter(
            teacher=teacher,
            day_of_week=weekday,
            is_active=True,
            effective_from__lte=target,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=target)
        )

        # Create session for each slot
        for slot in slots:
            ClassSession.objects.get_or_create(
                date=target,
                subject=slot.subject,
                section=slot.section,
                start_time=slot.start_time,
                defaults={
                    'timetable_slot': slot,
                    'teacher': slot.teacher,
                    'end_time': slot.end_time,
                    'room': slot.room,
                }
            )


def _ensure_sessions_for_section(section, days_back=30):
    """Same as above but for a whole section (used by student views)."""
    today = timezone.now().date()
    start = today - timedelta(days=days_back)

    for offset in range(days_back + 1):
        target = start + timedelta(days=offset)
        weekday = target.weekday()  # 0=Monday, 6=Sunday
        
        # Skip Sundays
        if weekday == 6:
            continue

        slots = TimetableSlot.objects.filter(
            section=section,
            day_of_week=weekday,
            is_active=True,
            effective_from__lte=target,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=target)
        )

        for slot in slots:
            ClassSession.objects.get_or_create(
                date=target,
                subject=slot.subject,
                section=slot.section,
                start_time=slot.start_time,
                defaults={
                    'timetable_slot': slot,
                    'teacher': slot.teacher,
                    'end_time': slot.end_time,
                    'room': slot.room,
                }
            )


# ─────────────────────────────────────────────────────────────
# TEACHER VIEWS
# ─────────────────────────────────────────────────────────────

@teacher_required
def teacher_dashboard(request):
    """
    Teacher dashboard — shows today's sessions + ALL past unmarked sessions.
    Sessions are lazily generated from TimetableSlot.
    """
    teacher = request.user.teacher_profile
    today   = timezone.now().date()

    # Generate sessions for past 30 days so nothing is missed
    _ensure_sessions_exist(teacher, days_back=30)

    # Today's sessions
    today_sessions = ClassSession.objects.filter(
        teacher=teacher,
        date=today,
        is_cancelled=False
    ).select_related('subject', 'section').order_by('start_time')

    # Today's unmarked sessions only
    pending_sessions = ClassSession.objects.filter(
        teacher=teacher,
        attendance_marked=False,
        is_cancelled=False,
        date=today
    ).select_related('subject', 'section').order_by('start_time')

    # Stats
    total_sessions  = ClassSession.objects.filter(teacher=teacher).count()
    marked_sessions = ClassSession.objects.filter(
        teacher=teacher, attendance_marked=True
    ).count()

    pending_count = pending_sessions.count()

    # Pending change requests
    pending_requests = TimetableChangeRequest.objects.filter(
        teacher=teacher, status='pending'
    ).count()

    context = {
        'teacher':          teacher,
        'today':            today,
        'today_sessions':   today_sessions,
        'pending_sessions': pending_sessions,
        'pending_count':    pending_count,
        'total_sessions':   total_sessions,
        'marked_sessions':  marked_sessions,
        'pending_requests': pending_requests,
    }
    return render(request, 'attendance/teacher_dashboard.html', context)


@teacher_required
def mark_attendance(request, session_id):
    """
    Mark attendance for ANY past or present unmarked session.
    Teacher can mark attendance for any unmarked slot — not just today's.
    """
    teacher = request.user.teacher_profile
    session = get_object_or_404(
        ClassSession,
        id=session_id,
        teacher=teacher,
        is_cancelled=False
    )

    if session.attendance_marked:
        messages.warning(
            request,
            'Attendance already marked for this session.'
        )
        return redirect(
            'attendance:view_session_attendance',
            session_id=session.id
        )

    students = Student.objects.filter(
        section=session.section,
        is_active=True
    ).select_related('user').order_by('roll_number')

    if request.method == 'POST':
        form = AttendanceMarkingForm(request.POST, students=students)

        if form.is_valid():
            topic = request.POST.get('topic', '').strip()

            with transaction.atomic():
                for student in students:
                    is_present = form.cleaned_data.get(
                        f'student_{student.id}', False
                    )
                    remarks = form.cleaned_data.get(
                        f'remarks_{student.id}', ''
                    )
                    Attendance.objects.create(
                        class_session=session,
                        student=student,
                        is_present=is_present,
                        remarks=remarks.strip()
                    )

                session.attendance_marked = True
                if topic:
                    session.topic = topic
                session.save()

            present_count = session.get_present_count()
            total_count   = session.get_total_students()
            messages.success(
                request,
                f'Attendance marked! {present_count}/{total_count} present.'
            )
            return redirect('attendance:teacher_dashboard')
    else:
        form = AttendanceMarkingForm(students=students)

    context = {
        'form':           form,
        'session':        session,
        'students':       students,
        'total_students': students.count(),
        'is_past':        session.date < timezone.now().date(),
    }
    return render(request, 'attendance/mark_attendance.html', context)


@teacher_required
def teacher_timetable(request):
    teacher     = request.user.teacher_profile
    today       = timezone.now().date()
    today_weekday = today.weekday()

    slots = TimetableSlot.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('subject', 'section').order_by('day_of_week', 'start_time')

    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    timetable_by_day = {day: [] for day in days}
    for slot in slots:
        timetable_by_day[slot.get_day_of_week_display()].append(slot)

    # Ensure sessions exist so today's sessions show up
    _ensure_sessions_exist(teacher, days_back=1)

    today_sessions = ClassSession.objects.filter(
        teacher=teacher,
        date=today,
        is_cancelled=False
    ).select_related('subject', 'section').order_by('start_time')

    today_sessions_data = [{
        'session':  s,
        'can_mark': not s.attendance_marked,
    } for s in today_sessions]

    # My pending change requests
    my_requests = TimetableChangeRequest.objects.filter(
        teacher=teacher
    ).select_related('timetable_slot').order_by('-created_at')[:5]

    context = {
        'teacher':             teacher,
        'timetable_by_day':    timetable_by_day,
        'days':                days,
        'today':               today,
        'today_weekday':       today_weekday,
        'today_sessions_data': today_sessions_data,
        'my_requests':         my_requests,
    }
    return render(request, 'attendance/teacher_timetable.html', context)


@teacher_required
def request_timetable_change(request):
    """
    Teacher submits a change request for one of their timetable slots.
    """
    teacher = request.user.teacher_profile

    my_slots = TimetableSlot.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('subject', 'section').order_by('day_of_week', 'start_time')

    if request.method == 'POST':
        slot_id      = request.POST.get('timetable_slot')
        request_type = request.POST.get('request_type')
        reason       = request.POST.get('reason', '').strip()
        req_date     = request.POST.get('requested_date') or None
        prop_time    = request.POST.get('proposed_time') or None
        prop_room    = request.POST.get('proposed_room', '').strip()

        if not slot_id or not request_type or not reason:
            messages.error(request, 'Please fill in all required fields.')
        else:
            slot = get_object_or_404(TimetableSlot, id=slot_id, teacher=teacher)
            TimetableChangeRequest.objects.create(
                teacher=teacher,
                timetable_slot=slot,
                request_type=request_type,
                reason=reason,
                requested_date=req_date,
                proposed_time=prop_time,
                proposed_room=prop_room,
            )
            messages.success(
                request,
                'Change request submitted! Management will review it shortly.'
            )
            return redirect('attendance:teacher_timetable')

    context = {
        'teacher':  teacher,
        'my_slots': my_slots,
        'request_types': TimetableChangeRequest.REQUEST_TYPE_CHOICES,
    }
    return render(request, 'attendance/request_timetable_change.html', context)


@teacher_required
def view_session_attendance(request, session_id):
    teacher = request.user.teacher_profile
    session = get_object_or_404(ClassSession, id=session_id, teacher=teacher)

    attendance_records = Attendance.objects.filter(
        class_session=session
    ).select_related('student', 'student__user').order_by('student__roll_number')

    context = {
        'session':            session,
        'attendance_records': attendance_records,
        'present_count':      session.get_present_count(),
        'absent_count':       session.get_absent_count(),
        'total_students':     session.get_total_students(),
        'attendance_pct':     session.get_attendance_percentage(),
    }
    return render(request, 'attendance/view_session_attendance.html', context)


@teacher_required
def teacher_sessions_list(request):
    teacher  = request.user.teacher_profile
    sessions = ClassSession.objects.filter(
        teacher=teacher
    ).select_related('subject', 'section').order_by('-date', '-start_time')

    filter_form = AttendanceFilterForm(teacher=teacher, data=request.GET or None)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('subject'):
            sessions = sessions.filter(
                subject=filter_form.cleaned_data['subject']
            )
        if filter_form.cleaned_data.get('section'):
            sessions = sessions.filter(
                section=filter_form.cleaned_data['section']
            )
        if filter_form.cleaned_data.get('date_from'):
            sessions = sessions.filter(
                date__gte=filter_form.cleaned_data['date_from']
            )
        if filter_form.cleaned_data.get('date_to'):
            sessions = sessions.filter(
                date__lte=filter_form.cleaned_data['date_to']
            )

    context = {
        'sessions':    sessions,
        'filter_form': filter_form,
    }
    return render(request, 'attendance/teacher_sessions_list.html', context)


# ─────────────────────────────────────────────────────────────
# MANAGEMENT VIEWS
# ─────────────────────────────────────────────────────────────

@management_required
def management_timetable(request):
    sections           = Section.objects.all().order_by('semester', 'code')
    selected_section_id = request.GET.get('section')
    selected_section   = None

    slots = TimetableSlot.objects.filter(
        is_active=True
    ).select_related('subject', 'section', 'teacher', 'teacher__user'
    ).order_by('day_of_week', 'start_time')

    if selected_section_id:
        slots            = slots.filter(section__id=selected_section_id)
        selected_section = Section.objects.filter(
            id=selected_section_id
        ).first()

    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    timetable_by_day = {day: [] for day in days}
    for slot in slots:
        timetable_by_day[slot.get_day_of_week_display()].append(slot)

    # Pending change requests
    pending_requests = TimetableChangeRequest.objects.filter(
        status='pending'
    ).select_related(
        'teacher', 'teacher__user', 'timetable_slot',
        'timetable_slot__subject', 'timetable_slot__section'
    ).order_by('-created_at')

    context = {
        'sections':          sections,
        'selected_section':  selected_section,
        'timetable_by_day':  timetable_by_day,
        'days':              days,
        'pending_requests':  pending_requests,
    }
    return render(request, 'attendance/management_timetable.html', context)


@management_required
def review_change_request(request, request_id):
    """
    Management approves or rejects a teacher's change request.
    """
    change_request = get_object_or_404(
        TimetableChangeRequest, id=request_id, status='pending'
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        note   = request.POST.get('management_note', '').strip()

        if action in ('approve', 'reject'):
            change_request.status         = 'approved' if action == 'approve' else 'rejected'
            change_request.management_note = note
            change_request.reviewed_at    = timezone.now()
            change_request.reviewed_by    = request.user
            change_request.save()

            # If approved — apply the change to the timetable slot
            if action == 'approve':
                slot = change_request.timetable_slot

                if change_request.request_type == 'cancel':
                    slot.is_active = False
                    slot.save()

                elif change_request.request_type == 'room':
                    if change_request.proposed_room:
                        slot.room = change_request.proposed_room
                        slot.save()

                elif change_request.request_type == 'reschedule':
                    if change_request.proposed_time:
                        slot.start_time = change_request.proposed_time
                        slot.save()

            messages.success(
                request,
                f'Request {change_request.status} successfully.'
            )

        return redirect('attendance:management_timetable')

    context = {'change_request': change_request}
    return render(request, 'attendance/review_change_request.html', context)


@management_required
def management_dashboard(request):
    total_students = Student.objects.filter(is_active=True).count()
    total_teachers = Teacher.objects.filter(is_active=True).count()
    total_sessions = ClassSession.objects.count()
    total_records  = Attendance.objects.count()

    avg_attendance = 0
    if total_records > 0:
        present = Attendance.objects.filter(is_present=True).count()
        avg_attendance = round(present / total_records * 100, 2)

    sections      = Section.objects.all()
    section_stats = []
    for section in sections:
        students     = Student.objects.filter(section=section, is_active=True)
        total_rec    = Attendance.objects.filter(student__in=students).count()
        present_rec  = Attendance.objects.filter(
            student__in=students, is_present=True
        ).count()
        pct = round(present_rec / total_rec * 100, 2) if total_rec > 0 else 0
        section_stats.append({
            'section':       section,
            'student_count': students.count(),
            'percentage':    pct,
        })

    # Low attendance students
    low_attendance = []
    for student in Student.objects.filter(is_active=True).select_related('user', 'section'):
        pct = student.get_attendance_percentage()
        if 0 < pct < 75:
            low_attendance.append({'student': student, 'percentage': pct})
    low_attendance.sort(key=lambda x: x['percentage'])

    # Pending change requests count
    pending_requests = TimetableChangeRequest.objects.filter(
        status='pending'
    ).count()

    context = {
        'total_students':    total_students,
        'total_teachers':    total_teachers,
        'total_sessions':    total_sessions,
        'avg_attendance':    avg_attendance,
        'section_stats':     section_stats,
        'low_attendance':    low_attendance[:20],
        'pending_requests':  pending_requests,
    }
    return render(request, 'attendance/management_dashboard.html', context)

from django.db import models as django_models




@teacher_required
def schedule_remedial_class(request):
    """
    Teacher schedules a remedial/makeup class for a missed session.
    Auto-generates a new ClassSession marked as remedial.
    No management approval needed.
    """
    teacher = request.user.teacher_profile

    if request.method == 'POST':
        form = RemedialClassForm(teacher, request.POST)
        
        if form.is_valid():
            original    = form.cleaned_data['original_session']
            date_       = form.cleaned_data['remedial_date']
            start       = form.cleaned_data['remedial_start_time']
            end         = form.cleaned_data['remedial_end_time']
            room        = form.cleaned_data.get('room', '')
            reason      = form.cleaned_data['reason']

            # Create the remedial session
            remedial_session = ClassSession.objects.create(
                timetable_slot=None,  # not from timetable
                subject=original.subject,
                section=original.section,
                teacher=teacher,
                date=date_,
                start_time=start,
                end_time=end,
                room=room or original.room,
                is_remedial=True,
                original_session=original,
                remedial_reason=reason,
            )

            messages.success(
                request,
                f'✅ Remedial class scheduled for {date_.strftime("%b %d, %Y")} '
                f'at {start.strftime("%I:%M %p")}!'
            )
            return redirect('attendance:teacher_dashboard')
    else:
        form = RemedialClassForm(teacher)

    # Show teacher's recent cancelled/missed sessions for context
    recent_missed = ClassSession.objects.filter(
        teacher=teacher,
        date__lt=timezone.now().date(),
    ).filter(
        django_models.Q(is_cancelled=True) | 
        django_models.Q(attendance_marked=False)
    ).select_related('subject', 'section').order_by('-date')[:10]

    context = {
        'form': form,
        'recent_missed': recent_missed,
        'teacher': teacher,
    }
    return render(request, 'attendance/schedule_remedial_class.html', context)


@teacher_required
def my_remedial_classes(request):
    """
    List all remedial classes scheduled by this teacher.
    """
    teacher = request.user.teacher_profile

    remedial_sessions = ClassSession.objects.filter(
        teacher=teacher,
        is_remedial=True
    ).select_related(
        'subject', 'section', 'original_session'
    ).order_by('-date', '-start_time')

    # Separate upcoming vs past
    today = timezone.now().date()
    upcoming = [s for s in remedial_sessions if s.date >= today]
    past     = [s for s in remedial_sessions if s.date < today]

    context = {
        'teacher': teacher,
        'upcoming_remedial': upcoming,
        'past_remedial': past,
    }
    return render(request, 'attendance/my_remedial_classes.html', context)


@teacher_required
def cancel_remedial_class(request, session_id):
    """
    Teacher can cancel a remedial class they scheduled.
    """
    teacher = request.user.teacher_profile
    session = get_object_or_404(
        ClassSession,
        id=session_id,
        teacher=teacher,
        is_remedial=True
    )

    if session.attendance_marked:
        messages.error(
            request,
            'Cannot cancel — attendance already marked.'
        )
    else:
        session.is_cancelled = True
        session.cancellation_note = 'Cancelled by teacher'
        session.save()
        messages.success(request, 'Remedial class cancelled.')

    return redirect('attendance:my_remedial_classes')