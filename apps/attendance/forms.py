from django import forms
from django.core.exceptions import ValidationError
from .models import ClassSession, Attendance
from apps.academic.models import Subject, Section


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


class AttendanceMarkingForm(forms.Form):
    """
    Dynamic form for marking attendance.
    Generates checkboxes for each student.
    """
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Optional remarks about this session'
        })
    )

    def __init__(self, *args, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if students:
            for student in students:
                # Create a checkbox for each student
                self.fields[f'student_{student.id}'] = forms.BooleanField(
                    required=False,
                    initial=True,  # Default to present
                    label=f'{student.roll_number} - {student.user.get_full_name()}'
                )
                
                # Optional remarks per student
                self.fields[f'remarks_{student.id}'] = forms.CharField(
                    required=False,
                    max_length=200,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control form-control-sm',
                        'placeholder': 'Remarks (optional)'
                    })
                )


class AttendanceFilterForm(forms.Form):
    """
    Form for filtering attendance records.
    """
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )