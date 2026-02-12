from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps


def user_type_required(user_types):
    """
    Decorator to restrict access based on user type.
    Usage: @user_type_required(['teacher', 'management'])
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.user_type not in user_types:
                raise PermissionDenied("You don't have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def student_required(view_func):
    """Decorator for student-only views"""
    return user_type_required(['student'])(view_func)


def teacher_required(view_func):
    """Decorator for teacher-only views"""
    return user_type_required(['teacher'])(view_func)


def management_required(view_func):
    """Decorator for management-only views"""
    return user_type_required(['management'])(view_func)


def teacher_or_management_required(view_func):
    """Decorator for teacher or management views"""
    return user_type_required(['teacher', 'management'])(view_func)