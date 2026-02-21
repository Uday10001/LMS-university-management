from django import forms
from django.contrib.auth import get_user_model
from .models import Student, Teacher

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    """
    Form for updating basic user info (shared by all roles).
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'profile_pic']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'profile_pic': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }


class StudentProfileForm(forms.ModelForm):
    """
    Form for updating student-specific profile info.
    """
    class Meta:
        model = Student
        fields = ['roll_number']
        widgets = {
            'roll_number': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True  # Roll number should not be editable
            }),
        }


class TeacherProfileForm(forms.ModelForm):
    """
    Form for updating teacher-specific profile info.
    """
    class Meta:
        model = Teacher
        fields = ['department']
        widgets = {
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter department name'
            }),
        }


class ChangePasswordForm(forms.Form):
    """
    Form for changing password (all users).
    """
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        }),
        label='Current Password'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        label='New Password',
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm New Password'
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('New passwords do not match.')

        return cleaned_data