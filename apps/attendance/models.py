from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.accounts.models import Student, Teacher
from apps.academic.models import Section, Subject


class ClassSession(models.Model):
    """
    Represents a single lecture/class session.
    Uniquely identified by date, subject, section, and teacher.
    """
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='class_sessions'
    )
    
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='class_sessions'
    )
    
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='class_sessions'
    )
    
    date = models.DateField(default=timezone.now)
    
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    topic = models.CharField(
        max_length=200,
        blank=True,
        help_text='Topic covered in this session'
    )
    
    attendance_marked = models.BooleanField(
        default=False,
        help_text='Has attendance been marked for this session?'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Class Session'
        verbose_name_plural = 'Class Sessions'
        ordering = ['-date', '-start_time']
        unique_together = ['date', 'subject', 'section', 'start_time']

    def __str__(self):
        return f"{self.subject.code} - {self.section.code} - {self.date}"

    def clean(self):
        """
        Validation: end_time must be after start_time.
        """
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError('End time must be after start time')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_total_students(self):
        """
        Returns total number of students in this session's section.
        """
        return self.section.students.filter(is_active=True).count()

    def get_present_count(self):
        """
        Returns number of students marked present.
        """
        return self.attendance_records.filter(is_present=True).count()

    def get_absent_count(self):
        """
        Returns number of students marked absent.
        """
        return self.attendance_records.filter(is_present=False).count()

    def get_attendance_percentage(self):
        """
        Calculate attendance percentage for this session.
        """
        total = self.get_total_students()
        if total == 0:
            return 0
        present = self.get_present_count()
        return round((present / total) * 100, 2)


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