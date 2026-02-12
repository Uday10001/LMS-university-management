from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import CustomUser, Student, Teacher


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom admin for CustomUser with role-based filtering.
    """
    list_display = ['email', 'get_full_name', 'user_type', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Login Credentials', {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'profile_pic')
        }),
        ('Role & Permissions', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)  # Collapsible section
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'user_type', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """
    Admin interface for Student profiles.
    """
    list_display = ['roll_number', 'get_student_name', 'section', 'get_attendance_percentage', 'is_active', 'enrollment_date']
    list_filter = ['section', 'is_active', 'enrollment_date']
    search_fields = ['roll_number', 'user__first_name', 'user__last_name', 'user__email']
    ordering = ['roll_number']
    
    fieldsets = (
        ('Student Information', {
            'fields': ('user', 'roll_number', 'section')
        }),
        ('Status', {
            'fields': ('is_active', 'enrollment_date')
        }),
    )
    
    readonly_fields = ['enrollment_date']
    
    # Optimize queries to avoid N+1 problem
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'section')
    
    def get_student_name(self, obj):
        return obj.user.get_full_name()
    get_student_name.short_description = 'Name'
    get_student_name.admin_order_field = 'user__first_name'
    
    def get_attendance_percentage(self, obj):
        percentage = obj.get_attendance_percentage()
        
        # Color coding based on percentage
        if percentage >= 75:
            color = 'green'
        elif percentage >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
            color,
            percentage
        )
    get_attendance_percentage.short_description = 'Attendance %'


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    """
    Admin interface for Teacher profiles.
    """
    list_display = ['employee_id', 'get_teacher_name', 'department', 'get_subjects_count', 'is_active', 'joining_date']
    list_filter = ['department', 'is_active', 'joining_date', 'subjects']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name', 'user__email', 'department']
    filter_horizontal = ['subjects', 'sections']  # Better UI for ManyToMany
    ordering = ['employee_id']
    
    fieldsets = (
        ('Teacher Information', {
            'fields': ('user', 'employee_id', 'department')
        }),
        ('Assignments', {
            'fields': ('subjects', 'sections'),
            'description': 'Assign subjects and sections to this teacher'
        }),
        ('Status', {
            'fields': ('is_active', 'joining_date')
        }),
    )
    
    readonly_fields = ['joining_date']
    
    # Optimize queries
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user').prefetch_related('subjects', 'sections')
    
    def get_teacher_name(self, obj):
        return obj.user.get_full_name()
    get_teacher_name.short_description = 'Name'
    get_teacher_name.admin_order_field = 'user__first_name'
    
    def get_subjects_count(self, obj):
        count = obj.subjects.count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            count
        )
    get_subjects_count.short_description = 'Subjects'