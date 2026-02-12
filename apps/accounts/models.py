from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator


class CustomUserManager(BaseUserManager):
    """
    Custom user manager to handle user creation with email as username.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'management')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with role-based user_type.
    """
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('management', 'Management'),
    )

    email = models.EmailField(unique=True, verbose_name='Email Address')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    user_type = models.CharField(max_length=15, choices=USER_TYPE_CHOICES)
    profile_pic = models.ImageField(
        upload_to='profile_pics/', 
        blank=True, 
        null=True,
        verbose_name='Profile Picture'
    )
    
    # Required for Django admin
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'user_type']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_user_type_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name


class Student(models.Model):
    """
    Student profile extending CustomUser.
    Linked to a Section (class group).
    """
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='student_profile'
    )
    
    roll_number = models.CharField(
        max_length=20, 
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9]+$',
                message='Roll number must be alphanumeric uppercase'
            )
        ]
    )
    
    section = models.ForeignKey(
        'academic.Section',  # Forward reference (academic app)
        on_delete=models.SET_NULL,
        null=True,
        related_name='students'
    )
    
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['roll_number']

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name()}"

    def get_attendance_percentage(self):
        """
        Calculate overall attendance percentage for this student.
        """
        from apps.attendance.models import Attendance
        
        total_sessions = Attendance.objects.filter(
            student=self
        ).count()
        
        if total_sessions == 0:
            return 0
        
        present_count = Attendance.objects.filter(
            student=self,
            is_present=True
        ).count()
        
        return round((present_count / total_sessions) * 100, 2)


class Teacher(models.Model):
    """
    Teacher profile extending CustomUser.
    Teachers can be assigned multiple subjects and sections.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^EMP[0-9]{4,}$',
                message='Employee ID must start with EMP followed by numbers'
            )
        ]
    )
    
    subjects = models.ManyToManyField(
        'academic.Subject',
        related_name='teachers',
        blank=True
    )
    
    sections = models.ManyToManyField(
        'academic.Section',
        related_name='teachers',
        blank=True
    )
    
    department = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'
        ordering = ['employee_id']

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"

    def get_assigned_subjects(self):
        """
        Returns list of subject names assigned to this teacher.
        """
        return [subject.name for subject in self.subjects.all()]