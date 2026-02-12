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