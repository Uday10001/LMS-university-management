from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse


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