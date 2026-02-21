from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.attendance.models import Attendance, ClassSession
from apps.academic.models import Subject
from .forms import UserProfileForm, StudentProfileForm, TeacherProfileForm, ChangePasswordForm


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html')


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    if user.user_type == 'student':
        return redirect('attendance:student_dashboard')
    elif user.user_type == 'teacher':
        return redirect('attendance:teacher_dashboard')
    elif user.user_type == 'management':
        return redirect('attendance:management_dashboard')
    return redirect('login')


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@login_required
def profile(request):
    """
    Unified profile view that handles all user types.
    """
    user = request.user
    user_form = UserProfileForm(instance=user)
    password_form = ChangePasswordForm()

    # Role-specific form
    role_form = None
    if user.user_type == 'student':
        role_form = StudentProfileForm(instance=user.student_profile)
    elif user.user_type == 'teacher':
        role_form = TeacherProfileForm(instance=user.teacher_profile)

    if request.method == 'POST':
        action = request.POST.get('action')

        # Handle profile info update
        if action == 'update_profile':
            user_form = UserProfileForm(request.POST, request.FILES, instance=user)

            if user.user_type == 'student':
                role_form = StudentProfileForm(request.POST, instance=user.student_profile)
            elif user.user_type == 'teacher':
                role_form = TeacherProfileForm(request.POST, instance=user.teacher_profile)

            user_form_valid = user_form.is_valid()
            role_form_valid = role_form.is_valid() if role_form else True

            if user_form_valid and role_form_valid:
                user_form.save()
                if role_form:
                    role_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('profile')
            else:
                messages.error(request, 'Please fix the errors below.')

        # Handle password change
        elif action == 'change_password':
            password_form = ChangePasswordForm(request.POST)

            if password_form.is_valid():
                current_password = password_form.cleaned_data['current_password']
                new_password = password_form.cleaned_data['new_password']

                if user.check_password(current_password):
                    user.set_password(new_password)
                    user.save()
                    # Keep user logged in after password change
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Password changed successfully!')
                    return redirect('profile')
                else:
                    messages.error(request, 'Current password is incorrect.')

    # Build context based on role
    context = build_profile_context(user, user_form, role_form, password_form)
    return render(request, 'accounts/profile.html', context)


def build_profile_context(user, user_form, role_form, password_form):
    """
    Helper to build profile context based on user type.
    """
    context = {
        'user_form': user_form,
        'role_form': role_form,
        'password_form': password_form,
    }

    if user.user_type == 'student':
        student = user.student_profile
        overall_percentage = student.get_attendance_percentage()

        # Subject-wise attendance
        subjects_attendance = []
        class_sessions = ClassSession.objects.filter(
            section=student.section
        ).values('subject').distinct()

        for session_data in class_sessions:
            subject = Subject.objects.get(id=session_data['subject'])
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
                    'present': present,
                    'absent': total - present,
                    'total': total,
                    'percentage': percentage
                })

        context.update({
            'student': student,
            'overall_percentage': overall_percentage,
            'subjects_attendance': subjects_attendance,
        })

    elif user.user_type == 'teacher':
        teacher = user.teacher_profile
        total_sessions = ClassSession.objects.filter(teacher=teacher).count()
        marked_sessions = ClassSession.objects.filter(
            teacher=teacher,
            attendance_marked=True
        ).count()

        context.update({
            'teacher': teacher,
            'total_sessions': total_sessions,
            'marked_sessions': marked_sessions,
            'subjects': teacher.subjects.all(),
            'sections': teacher.sections.all(),
        })

    return context

def user_login(request):
    """
    Login view for all user types.
    """
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'accounts/login.html')


@login_required
def user_logout(request):
    """
    Logout view for all users.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard(request):
    """
    Main dashboard that redirects based on user type.
    """
    user = request.user
    
    if user.user_type == 'student':
        return redirect('attendance:student_dashboard')
    elif user.user_type == 'teacher':
        return redirect('attendance:teacher_dashboard')
    elif user.user_type == 'management':
        return redirect('attendance:management_dashboard')
    else:
        messages.error(request, 'Invalid user type.')
        return redirect('login')


@login_required
def profile(request):
    """
    User profile view.
    """
    user = request.user
    
    context = {
        'user': user,
    }
    
    # Add role-specific data
    if user.user_type == 'student':
        context['student'] = user.student_profile
        context['attendance_percentage'] = user.student_profile.get_attendance_percentage()
    elif user.user_type == 'teacher':
        context['teacher'] = user.teacher_profile
    
    return render(request, 'accounts/profile.html', context)


def home(request):
    """
    Landing page - redirect to dashboard if logged in.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')
