from django.contrib import admin
from django.utils.html import format_html
from .models import Section, Subject


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    """
    Admin interface for Sections.
    """
    list_display = ['code', 'name', 'semester', 'academic_year', 'get_student_count', 'capacity', 'get_capacity_status']
    list_filter = ['semester', 'academic_year']
    search_fields = ['name', 'code']
    ordering = ['semester', 'code']
    
    fieldsets = (
        ('Section Details', {
            'fields': ('name', 'code', 'semester', 'academic_year')
        }),
        ('Capacity', {
            'fields': ('capacity',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_student_count(self, obj):
        count = obj.get_student_count()
        return format_html(
            '<strong>{}</strong> / {}',
            count,
            obj.capacity
        )
    get_student_count.short_description = 'Students'
    
    def get_capacity_status(self, obj):
        if obj.is_full():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 3px;">FULL</span>'
            )
        else:
            remaining = obj.capacity - obj.get_student_count()
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 3px;">{} slots left</span>',
                remaining
            )
    get_capacity_status.short_description = 'Status'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """
    Admin interface for Subjects.
    """
    list_display = ['code', 'name', 'credits', 'semester', 'get_teachers_count', 'is_active']
    list_filter = ['semester', 'credits', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['semester', 'code']
    
    fieldsets = (
        ('Subject Information', {
            'fields': ('name', 'code', 'credits', 'semester')
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_teachers_count(self, obj):
        count = obj.teachers.filter(is_active=True).count()
        if count == 0:
            return format_html(
                '<span style="color: red;">No teachers assigned</span>'
            )
        return format_html(
            '<span style="color: green;">{} teacher(s)</span>',
            count
        )
    get_teachers_count.short_description = 'Teachers'

from .models import Section, Subject, TimetableSlot


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display  = [
        'get_day', 'get_time_range', 'section',
        'subject', 'teacher', 'room', 'is_active'
    ]
    list_filter   = ['day_of_week', 'section', 'subject', 'is_active']
    search_fields = [
        'section__code', 'subject__code',
        'teacher__user__first_name', 'room'
    ]
    ordering      = ['day_of_week', 'start_time']

    fieldsets = (
        ('Schedule', {
            'fields': ('day_of_week', 'start_time', 'end_time', 'room')
        }),
        ('Assignment', {
            'fields': ('section', 'subject', 'teacher')
        }),
        ('Validity', {
            'fields': ('effective_from', 'effective_to', 'is_active')
        }),
    )

    def get_day(self, obj):
        return obj.get_day_of_week_display()
    get_day.short_description = 'Day'
    get_day.admin_order_field = 'day_of_week'

    def get_time_range(self, obj):
        return f"{obj.start_time:%H:%M} – {obj.end_time:%H:%M}"
    get_time_range.short_description = 'Time'