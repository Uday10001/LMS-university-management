from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import ClassSession, Attendance


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for Class Sessions.
    """
    list_display = [
        'get_session_info',
        'date',
        'get_time_range',
        'teacher',
        'attendance_marked',
        'get_attendance_stats'
    ]
    list_filter = ['date', 'subject', 'section', 'teacher', 'attendance_marked']
    search_fields = ['subject__name', 'subject__code', 'section__name', 'teacher__user__first_name', 'topic']
    ordering = ['-date', '-start_time']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Session Details', {
            'fields': ('subject', 'section', 'teacher', 'date')
        }),
        ('Time', {
            'fields': ('start_time', 'end_time')
        }),
        ('Additional Info', {
            'fields': ('topic', 'attendance_marked'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    # Optimize queries
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'subject', 'section', 'teacher', 'teacher__user'
        ).annotate(
            attendance_count=Count('attendance_records')
        )
    
    def get_session_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.subject.code,
            obj.section.code
        )
    get_session_info.short_description = 'Session'
    
    def get_time_range(self, obj):
        return f"{obj.start_time.strftime('%I:%M %p')} - {obj.end_time.strftime('%I:%M %p')}"
    get_time_range.short_description = 'Time'
    
    def get_attendance_stats(self, obj):
        if not obj.attendance_marked:
            return format_html(
                '<span style="color: gray;">Not marked</span>'
            )
        
        present = obj.get_present_count()
        total = obj.get_total_students()
        percentage = obj.get_attendance_percentage()
        
        # Color coding
        if percentage >= 75:
            color = 'green'
        elif percentage >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{}/{} ({:.1f}%)</span>',
            color,
            present,
            total,
            percentage
        )
    get_attendance_stats.short_description = 'Attendance'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """
    Admin interface for Attendance records.
    """
    list_display = [
        'get_student_info',
        'get_session_info',
        'get_attendance_status',
        'marked_at',
        'remarks'
    ]
    list_filter = [
        'is_present',
        'class_session__date',
        'class_session__subject',
        'class_session__section',
        'student__section'
    ]
    search_fields = [
        'student__roll_number',
        'student__user__first_name',
        'student__user__last_name',
        'class_session__subject__name',
        'remarks'
    ]
    ordering = ['-marked_at']
    date_hierarchy = 'class_session__date'
    
    fieldsets = (
        ('Attendance Record', {
            'fields': ('class_session', 'student', 'is_present')
        }),
        ('Additional Info', {
            'fields': ('remarks',)
        }),
    )
    
    readonly_fields = ['marked_at']
    
    # Optimize queries
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'student',
            'student__user',
            'student__section',
            'class_session',
            'class_session__subject',
            'class_session__section'
        )
    
    def get_student_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.student.roll_number,
            obj.student.user.get_full_name()
        )
    get_student_info.short_description = 'Student'
    
    def get_session_info(self, obj):
        return format_html(
            '{} - {}<br><small>{}</small>',
            obj.class_session.subject.code,
            obj.class_session.section.code,
            obj.class_session.date.strftime('%d %b %Y')
        )
    get_session_info.short_description = 'Session'
    
    def get_attendance_status(self, obj):
        if obj.is_present:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">✓ PRESENT</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">✗ ABSENT</span>'
            )
    get_attendance_status.short_description = 'Status'