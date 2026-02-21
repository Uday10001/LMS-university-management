from django.shortcuts import render

# Create your views here.
from apps.academic.models import TimetableSlot
from django.db import models as django_models


# ── MANAGEMENT: Full timetable overview ──────────────────────

@management_required
def management_timetable(request):
    """
    Management sees the full timetable for all sections.
    Can filter by section.
    """
    sections = Section.objects.all().order_by('semester', 'code')
    selected_section_id = request.GET.get('section')
    selected_section = None

    slots = TimetableSlot.objects.filter(
        is_active=True
    ).select_related(
        'subject', 'section', 'teacher', 'teacher__user'
    ).order_by('day_of_week', 'start_time')

    if selected_section_id:
        slots = slots.filter(section__id=selected_section_id)
        selected_section = Section.objects.filter(
            id=selected_section_id
        ).first()

    # Group by day
    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    timetable_by_day = {day: [] for day in days}

    for slot in slots:
        day_name = slot.get_day_of_week_display()
        timetable_by_day[day_name].append(slot)

    context = {
        'sections': sections,
        'selected_section': selected_section,
        'timetable_by_day': timetable_by_day,
        'days': days,
    }
    return render(request, 'attendance/management_timetable.html', context)


# ── TEACHER: Personal timetable + today's sessions ───────────

@teacher_required
def teacher_timetable(request):
    """
    Teacher sees their own weekly timetable and today's sessions.
    """
    teacher = request.user.teacher_profile
    today   = timezone.now().date()
    today_weekday = today.weekday()

    # Weekly timetable slots for this teacher
    slots = TimetableSlot.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related(
        'subject', 'section'
    ).order_by('day_of_week', 'start_time')

    days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
    timetable_by_day = {day: [] for day in days}
    for slot in slots:
        timetable_by_day[slot.get_day_of_week_display()].append(slot)

    # Today's actual sessions (generated ClassSessions)
    today_sessions = ClassSession.objects.filter(
        teacher=teacher,
        date=today
    ).select_related('subject', 'section').order_by('start_time')

    # Tag each with attendance status
    today_sessions_data = []
    for session in today_sessions:
        today_sessions_data.append({
            'session': session,
            'can_mark': not session.attendance_marked and not session.is_cancelled,
        })

    # Upcoming week (next 5 working days)
    upcoming_sessions = ClassSession.objects.filter(
        teacher=teacher,
        date__gt=today,
        date__lte=today + timezone.timedelta(days=7)
    ).select_related('subject', 'section').order_by('date', 'start_time')

    context = {
        'teacher': teacher,
        'timetable_by_day': timetable_by_day,
        'days': days,
        'today': today,
        'today_weekday': today_weekday,
        'today_sessions_data': today_sessions_data,
        'upcoming_sessions': upcoming_sessions,
    }
    return render(request, 'attendance/teacher_timetable.html', context)


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

def _ensure_sessions_exist(teacher, days_back=30):
    """
    Lazily generate ClassSessions for past N days for a teacher.
    """
    from django.db.models import Q           # ✅ import Q here

    today = timezone.now().date()
    start = today - timedelta(days=days_back)

    for offset in range(days_back + 1):
        target  = start + timedelta(days=offset)
        weekday = target.weekday()
        if weekday == 6:                     # skip Sunday
            continue

        slots = TimetableSlot.objects.filter(
            teacher=teacher,
            day_of_week=weekday,
            is_active=True,
            effective_from__lte=target,
        ).filter(
            Q(effective_to__isnull=True) |   # ✅ clean Q usage
            Q(effective_to__gte=target)
        )

        for slot in slots:
            ClassSession.objects.get_or_create(
                date=target,
                subject=slot.subject,
                section=slot.section,
                start_time=slot.start_time,
                defaults={
                    'timetable_slot': slot,
                    'teacher':        slot.teacher,
                    'end_time':       slot.end_time,
                    'room':           slot.room,
                }
            )


def _ensure_sessions_for_section(section, days_back=30):
    """
    Lazily generate ClassSessions for past N days for a section.
    """
    from django.db.models import Q           # ✅ import Q here

    today = timezone.now().date()
    start = today - timedelta(days=days_back)

    for offset in range(days_back + 1):
        target  = start + timedelta(days=offset)
        weekday = target.weekday()
        if weekday == 6:
            continue

        slots = TimetableSlot.objects.filter(
            section=section,
            day_of_week=weekday,
            is_active=True,
            effective_from__lte=target,
        ).filter(
            Q(effective_to__isnull=True) |   # ✅ clean Q usage
            Q(effective_to__gte=target)
        )

        for slot in slots:
            ClassSession.objects.get_or_create(
                date=target,
                subject=slot.subject,
                section=slot.section,
                start_time=slot.start_time,
                defaults={
                    'timetable_slot': slot,
                    'teacher':        slot.teacher,
                    'end_time':       slot.end_time,
                    'room':           slot.room,
                }
            )