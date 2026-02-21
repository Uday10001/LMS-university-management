from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Section(models.Model):
    """
    Represents a class section (e.g., CSE-A, CSE-B, ECE-1).
    Students belong to one section.
    """
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(
        max_length=10, 
        unique=True,
        help_text='Short code like CSE-A, ECE-1'
    )
    
    semester = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text='Semester number (1-8)'
    )
    
    academic_year = models.CharField(
        max_length=10,
        help_text='e.g., 2024-25'
    )
    
    capacity = models.IntegerField(
        default=60,
        validators=[MinValueValidator(1)],
        help_text='Maximum number of students'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'
        ordering = ['semester', 'code']
        unique_together = ['code', 'academic_year']

    def __str__(self):
        return f"{self.name} (Sem {self.semester})"

    def get_student_count(self):
        """
        Returns number of students in this section.
        """
        return self.students.filter(is_active=True).count()

    def is_full(self):
        """
        Check if section has reached capacity.
        """
        return self.get_student_count() >= self.capacity


class Subject(models.Model):
    """
    Represents an academic subject.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text='Subject code like CSE101, MATH201'
    )
    
    credits = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        default=3
    )
    
    semester = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        ordering = ['semester', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_assigned_teachers(self):
        """
        Returns list of teachers teaching this subject.
        """
        return self.teachers.filter(is_active=True)
class TimetableSlot(models.Model):
    """
    Represents a recurring weekly timetable entry.
    Management creates these to define the fixed weekly schedule.
    A slot = one subject, one section, one teacher, one time block, one weekday.
    """
    DAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
    )

    section    = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='timetable_slots'
    )
    subject    = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='timetable_slots'
    )
    teacher    = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.CASCADE,
        related_name='timetable_slots'
    )
    day_of_week  = models.IntegerField(choices=DAY_CHOICES)
    start_time   = models.TimeField()
    end_time     = models.TimeField()
    room         = models.CharField(
        max_length=50,
        blank=True,
        help_text='Room or lab number e.g. A-101'
    )
    is_active    = models.BooleanField(default=True)
    effective_from = models.DateField(
        help_text='Date from which this slot is active'
    )
    effective_to   = models.DateField(
        null=True,
        blank=True,
        help_text='Leave blank if ongoing'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Timetable Slot'
        verbose_name_plural = 'Timetable Slots'
        ordering            = ['day_of_week', 'start_time']
        # Prevent clashes: same section cannot have two subjects
        # at the same time on the same day
        unique_together = ['section', 'day_of_week', 'start_time']

    def __str__(self):
        return (
            f"{self.get_day_of_week_display()} {self.start_time:%H:%M} — "
            f"{self.subject.code} ({self.section.code})"
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        # end must be after start
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError('End time must be after start time.')

        # Teacher clash: same teacher, same day, overlapping time, different section
        clashes = TimetableSlot.objects.filter(
            teacher=self.teacher,
            day_of_week=self.day_of_week,
            is_active=True,
        ).exclude(pk=self.pk)

        for slot in clashes:
            if self.start_time < slot.end_time and self.end_time > slot.start_time:
                raise ValidationError(
                    f"Teacher clash: {self.teacher} already has "
                    f"{slot.subject.code} ({slot.section.code}) "
                    f"at this time on {self.get_day_of_week_display()}."
                )

        # Section clash: same section, same day, overlapping time
        section_clashes = TimetableSlot.objects.filter(
            section=self.section,
            day_of_week=self.day_of_week,
            is_active=True,
        ).exclude(pk=self.pk)

        for slot in section_clashes:
            if self.start_time < slot.end_time and self.end_time > slot.start_time:
                raise ValidationError(
                    f"Section clash: {self.section.code} already has "
                    f"{slot.subject.code} at this time on "
                    f"{self.get_day_of_week_display()}."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class TimetableChangeRequest(models.Model):
    """
    Teachers can request changes to their timetable slots.
    Management reviews and approves/rejects these.
    """
    STATUS_CHOICES = (
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    REQUEST_TYPE_CHOICES = (
        ('reschedule', 'Reschedule Class'),
        ('substitute', 'Request Substitute'),
        ('cancel',     'Cancel Class'),
        ('room',       'Change Room'),
    )

    teacher          = models.ForeignKey(
        'accounts.Teacher',
        on_delete=models.CASCADE,
        related_name='change_requests'
    )
    timetable_slot   = models.ForeignKey(
        TimetableSlot,
        on_delete=models.CASCADE,
        related_name='change_requests'
    )
    request_type     = models.CharField(
        max_length=20,
        choices=REQUEST_TYPE_CHOICES
    )
    reason           = models.TextField(
        help_text='Explain why this change is needed'
    )
    requested_date   = models.DateField(
        null=True, blank=True,
        help_text='Which specific date needs the change'
    )
    proposed_time    = models.TimeField(
        null=True, blank=True,
        help_text='New proposed start time (for reschedule)'
    )
    proposed_room    = models.CharField(
        max_length=50, blank=True,
        help_text='New proposed room (for room change)'
    )
    status           = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    management_note  = models.TextField(
        blank=True,
        help_text='Management response or reason for rejection'
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    reviewed_at      = models.DateTimeField(null=True, blank=True)
    reviewed_by      = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_requests'
    )

    class Meta:
        verbose_name        = 'Timetable Change Request'
        verbose_name_plural = 'Timetable Change Requests'
        ordering            = ['-created_at']

    def __str__(self):
        return (
            f"{self.teacher.user.get_full_name()} — "
            f"{self.get_request_type_display()} — {self.status}"
        )