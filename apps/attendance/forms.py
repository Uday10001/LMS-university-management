from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, time
from .models import *
from apps.accounts.models import Student
from apps.academic.models import Subject, Section
from django.db import models


class ClassSessionForm(forms.ModelForm):
    """
    Form for creating a new class session.
    """
    class Meta:
        model = ClassSession
        fields = ['subject', 'section', 'date', 'start_time', 'end_time', 'topic']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'section': forms.Select(attrs={'class': 'form-control'}),
            'topic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lecture topic'}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter subjects and sections based on teacher's assignments
        if teacher:
            self.fields['subject'].queryset = teacher.subjects.filter(is_active=True)
            self.fields['section'].queryset = teacher.sections.all()

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValidationError('End time must be after start time.')
        
        return cleaned_data


class RemedialClassForm(forms.Form):
    """
    Form for teachers to schedule a remedial/makeup class.
    """
    original_session = forms.ModelChoiceField(
        queryset=ClassSession.objects.none(),  # ✅
        required=True,
    )
    
    remedial_date = forms.DateField(
        required=True,
        label='Remedial Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': timezone.now().date().isoformat(),
        }),
        help_text='When will the makeup class be held?'
    )
    
    remedial_start_time = forms.TimeField(
        required=True,
        label='Start Time',
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        })
    )
    
    remedial_end_time = forms.TimeField(
        required=True,
        label='End Time',
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        })
    )
    
    room = forms.CharField(
        required=False,
        max_length=50,
        label='Room/Location',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. A-101 or Online'
        }),
        help_text='Where will the remedial class be held?'
    )
    
    reason = forms.CharField(
        required=True,
        max_length=200,
        label='Reason for Remedial Class',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Original class cancelled due to...'
        })
    )

    def __init__(self, teacher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show sessions that need makeup:
        # - Past sessions that are cancelled OR unmarked
        # - Belonging to this teacher
        # - Don't already have a remedial class scheduled
        today = timezone.now().date()
        
        eligible_sessions = ClassSession.objects.filter(
            teacher=teacher,
            date__lt=today,
        ).filter(
            models.Q(is_cancelled=True) | 
            models.Q(attendance_marked=False)
        ).exclude(
            remedial_classes__isnull=False  # exclude if remedial already exists
        ).select_related(
            'subject', 'section'
        ).order_by('-date')
        
        self.fields['original_session'].queryset = eligible_sessions

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('remedial_start_time')
        end   = cleaned_data.get('remedial_end_time')
        date_ = cleaned_data.get('remedial_date')
        
        if start and end and start >= end:
            raise ValidationError('End time must be after start time.')
        
        if date_ and date_ < timezone.now().date():
            raise ValidationError('Remedial class cannot be scheduled in the past.')
        
        return cleaned_data


class AttendanceMarkingForm(forms.Form):
    """
    Dynamically generates attendance checkboxes for all students in a section.
    """
    def __init__(self, *args, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if students:
            for student in students:
                # Checkbox for present/absent
                self.fields[f'student_{student.id}'] = forms.BooleanField(
                    required=False,
                    initial=True,
                    label=f'{student.roll_number} — {student.user.get_full_name()}'
                )
                # Remarks field
                self.fields[f'remarks_{student.id}'] = forms.CharField(
                    required=False,
                    max_length=100,
                    widget=forms.TextInput(attrs={
                        'placeholder': 'Remarks (optional)',
                        'class': 'form-control form-control-sm'
                    })
                )


class AttendanceFilterForm(forms.Form):
    """
    Filter form for teacher's session list.
    """
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, teacher=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher:
            self.fields['subject'].queryset = teacher.subjects.all()
            self.fields['section'].queryset = teacher.sections.all()