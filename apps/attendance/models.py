from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.accounts.models import Student, Teacher
from apps.academic.models import Section, Subject

class ClassSession(models.Model):
    """
    Represents one actual occurrence of a timetable slot on a specific date.
    Auto-generated daily from TimetableSlot OR created manually as a remedial class.
    """
    timetable_slot = models.ForeignKey(
        'academic.TimetableSlot',
        on_delete=models.CASCADE,
        related_name='class_sessions',
        null=True,
        blank=True,
        help_text='The recurring slot this session was generated from (null for remedial classes)'
    )
    subject  = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='class_sessions'
    )
    section  = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='class_sessions'
    )
    teacher  = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='class_sessions'
    )
    date       = models.DateField()
    start_time = models.TimeField()
    end_time   = models.TimeField()
    room       = models.CharField(max_length=50, blank=True)
    topic      = models.CharField(
        max_length=200, blank=True,
        help_text='Topic covered — teacher fills this when marking attendance'
    )
    
    # ✅ NEW FIELDS FOR REMEDIAL CLASSES
    is_remedial        = models.BooleanField(
        default=False,
        help_text='True if this is a makeup/remedial class scheduled by teacher'
    )
    original_session   = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='remedial_classes',
        help_text='If remedial, which session is this making up for?'
    )
    remedial_reason    = models.CharField(
        max_length=200, blank=True,
        help_text='Why was this remedial class needed?'
    )
    
    is_cancelled       = models.BooleanField(default=False)
    cancellation_note  = models.CharField(max_length=200, blank=True)
    attendance_marked  = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Class Session'
        verbose_name_plural = 'Class Sessions'
        ordering            = ['-date', 'start_time']
        # Allow multiple sessions on same date/time if one is remedial
        # unique_together removed to allow remedial classes

    def __str__(self):
        prefix = '[REMEDIAL] ' if self.is_remedial else ''
        return f"{prefix}{self.subject.code} — {self.section.code} — {self.date}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.end_time and self.start_time:
            if self.end_time <= self.start_time:
                raise ValidationError('End time must be after start time.')
        
        # Check teacher clash (same teacher, same time, different section)
        # Only check if NOT remedial or if teacher wants strict checking
        if not self.is_remedial:
            clashing_sessions = ClassSession.objects.filter(
                teacher=self.teacher,
                date=self.date,
                is_cancelled=False,
            ).exclude(pk=self.pk)
            
            for session in clashing_sessions:
                if (self.start_time < session.end_time and 
                    self.end_time > session.start_time):
                    if session.section != self.section:
                        raise ValidationError(
                            f"Teacher clash: {self.teacher} already has "
                            f"{session.subject.code} ({session.section.code}) "
                            f"at this time on {self.date}."
                        )

    def save(self, *args, **kwargs):
        # Only validate if not explicitly skipping
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)

    def get_total_students(self):
        return self.section.students.filter(is_active=True).count()

    def get_present_count(self):
        return self.attendance_records.filter(is_present=True).count()

    def get_absent_count(self):
        return self.attendance_records.filter(is_present=False).count()

    def get_attendance_percentage(self):
        total = self.get_total_students()
        if total == 0:
            return 0
        return round((self.get_present_count() / total) * 100, 2)

class Attendance(models.Model):
    """
    Represents attendance record for a student in a specific class session.
    """
    class_session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    
    is_present = models.BooleanField(default=False)
    
    marked_at = models.DateTimeField(auto_now_add=True)
    
    remarks = models.CharField(
        max_length=200,
        blank=True,
        help_text='Optional remarks (e.g., Late, Medical Leave)'
    )

    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-marked_at']
        unique_together = ['class_session', 'student']

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student.roll_number} - {self.class_session.subject.code} - {status}"

    def clean(self):
        """
        Validation: Student must belong to the session's section.
        """
        if self.student.section != self.class_session.section:
            raise ValidationError(
                f'Student {self.student.roll_number} does not belong to section {self.class_session.section.code}'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)