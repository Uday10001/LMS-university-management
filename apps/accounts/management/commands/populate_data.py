from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta, time
import random

from apps.accounts.models import CustomUser, Student, Teacher
from apps.academic.models import Section, Subject
from apps.attendance.models import ClassSession, Attendance


class Command(BaseCommand):
    help = 'Populate database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Starting data population...'))

        with transaction.atomic():
            # Create in order of dependencies
            sections = self.create_sections()
            subjects = self.create_subjects()
            management_users = self.create_management_users()
            teachers = self.create_teachers(subjects, sections)
            students = self.create_students(sections)
            class_sessions = self.create_class_sessions(subjects, sections, teachers)
            self.create_attendance_records(class_sessions, students)

        self.stdout.write(self.style.SUCCESS('✅ Data population completed successfully!'))
        self.print_summary()

    def clear_data(self):
        """Clear all existing data"""
        Attendance.objects.all().delete()
        ClassSession.objects.all().delete()
        Student.objects.all().delete()
        Teacher.objects.all().delete()
        Subject.objects.all().delete()
        Section.objects.all().delete()
        CustomUser.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('✅ Existing data cleared'))

    def create_sections(self):
        """Create sections for different semesters"""
        self.stdout.write('Creating sections...')
        
        sections_data = [
            # Semester 1
            {'name': 'Computer Science A', 'code': 'CSE-A', 'semester': 1, 'capacity': 60},
            {'name': 'Computer Science B', 'code': 'CSE-B', 'semester': 1, 'capacity': 60},
            {'name': 'Electronics A', 'code': 'ECE-A', 'semester': 1, 'capacity': 50},
            
            # Semester 3
            {'name': 'Computer Science C', 'code': 'CSE-C', 'semester': 3, 'capacity': 55},
            {'name': 'Information Technology A', 'code': 'IT-A', 'semester': 3, 'capacity': 50},
            
            # Semester 5
            {'name': 'Computer Science D', 'code': 'CSE-D', 'semester': 5, 'capacity': 45},
            {'name': 'Mechanical A', 'code': 'ME-A', 'semester': 5, 'capacity': 40},
        ]

        sections = []
        for data in sections_data:
            section = Section.objects.create(
                name=data['name'],
                code=data['code'],
                semester=data['semester'],
                academic_year='2024-25',
                capacity=data['capacity']
            )
            sections.append(section)
            self.stdout.write(f'  ✓ Created section: {section.code}')

        return sections

    def create_subjects(self):
        """Create subjects for different semesters"""
        self.stdout.write('Creating subjects...')
        
        subjects_data = [
            # Semester 1
            {'name': 'Programming Fundamentals', 'code': 'CSE101', 'credits': 4, 'semester': 1},
            {'name': 'Mathematics I', 'code': 'MATH101', 'credits': 4, 'semester': 1},
            {'name': 'Physics', 'code': 'PHY101', 'credits': 3, 'semester': 1},
            {'name': 'English Communication', 'code': 'ENG101', 'credits': 2, 'semester': 1},
            
            # Semester 3
            {'name': 'Data Structures', 'code': 'CSE201', 'credits': 4, 'semester': 3},
            {'name': 'Database Management Systems', 'code': 'CSE202', 'credits': 4, 'semester': 3},
            {'name': 'Computer Networks', 'code': 'CSE203', 'credits': 3, 'semester': 3},
            {'name': 'Mathematics III', 'code': 'MATH201', 'credits': 3, 'semester': 3},
            
            # Semester 5
            {'name': 'Machine Learning', 'code': 'CSE301', 'credits': 4, 'semester': 5},
            {'name': 'Web Technologies', 'code': 'CSE302', 'credits': 3, 'semester': 5},
            {'name': 'Software Engineering', 'code': 'CSE303', 'credits': 3, 'semester': 5},
            {'name': 'Cloud Computing', 'code': 'CSE304', 'credits': 3, 'semester': 5},
        ]

        subjects = []
        for data in subjects_data:
            subject = Subject.objects.create(
                name=data['name'],
                code=data['code'],
                credits=data['credits'],
                semester=data['semester'],
                description=f"Course covering {data['name'].lower()} concepts and applications.",
                is_active=True
            )
            subjects.append(subject)
            self.stdout.write(f'  ✓ Created subject: {subject.code}')

        return subjects

    def create_management_users(self):
        """Create management users"""
        self.stdout.write('Creating management users...')
        
        management_data = [
            {'email': 'admin@university.edu', 'first_name': 'Admin', 'last_name': 'User'},
            {'email': 'hod.cse@university.edu', 'first_name': 'Rajesh', 'last_name': 'Kumar'},
            {'email': 'dean@university.edu', 'first_name': 'Priya', 'last_name': 'Sharma'},
        ]

        users = []
        for data in management_data:
            user = CustomUser.objects.create_user(
                email=data['email'],
                password='password123',  # Default password for testing
                first_name=data['first_name'],
                last_name=data['last_name'],
                user_type='management'
            )
            users.append(user)
            self.stdout.write(f'  ✓ Created management user: {user.email}')

        return users

    def create_teachers(self, subjects, sections):
        """Create teachers and assign subjects/sections"""
        self.stdout.write('Creating teachers...')
        
        teachers_data = [
            {'email': 'amit.verma@university.edu', 'first_name': 'Amit', 'last_name': 'Verma', 'emp_id': 'EMP1001', 'dept': 'Computer Science'},
            {'email': 'neha.singh@university.edu', 'first_name': 'Neha', 'last_name': 'Singh', 'emp_id': 'EMP1002', 'dept': 'Computer Science'},
            {'email': 'rahul.gupta@university.edu', 'first_name': 'Rahul', 'last_name': 'Gupta', 'emp_id': 'EMP1003', 'dept': 'Mathematics'},
            {'email': 'priya.patel@university.edu', 'first_name': 'Priya', 'last_name': 'Patel', 'emp_id': 'EMP1004', 'dept': 'Computer Science'},
            {'email': 'vikram.reddy@university.edu', 'first_name': 'Vikram', 'last_name': 'Reddy', 'emp_id': 'EMP1005', 'dept': 'Electronics'},
            {'email': 'anita.desai@university.edu', 'first_name': 'Anita', 'last_name': 'Desai', 'emp_id': 'EMP1006', 'dept': 'English'},
        ]

        teachers = []
        for data in teachers_data:
            user = CustomUser.objects.create_user(
                email=data['email'],
                password='password123',
                first_name=data['first_name'],
                last_name=data['last_name'],
                user_type='teacher'
            )
            
            teacher = Teacher.objects.create(
                user=user,
                employee_id=data['emp_id'],
                department=data['dept']
            )
            
            # Assign random subjects (2-4 subjects per teacher)
            teacher_subjects = random.sample(subjects, random.randint(2, 4))
            teacher.subjects.set(teacher_subjects)
            
            # Assign random sections (2-3 sections per teacher)
            teacher_sections = random.sample(sections, random.randint(2, 3))
            teacher.sections.set(teacher_sections)
            
            teachers.append(teacher)
            self.stdout.write(f'  ✓ Created teacher: {teacher.employee_id} - {user.get_full_name()}')

        return teachers

    def create_students(self, sections):
        """Create students and assign to sections"""
        self.stdout.write('Creating students...')
        
        first_names = ['Aarav', 'Vivaan', 'Aditya', 'Arjun', 'Sai', 'Reyansh', 'Ayaan', 'Krishna',
                       'Ishaan', 'Shaurya', 'Aadhya', 'Ananya', 'Diya', 'Ira', 'Kiara', 'Kavya',
                       'Myra', 'Navya', 'Saanvi', 'Sara', 'Aarush', 'Advait', 'Arnav', 'Dhruv']
        
        last_names = ['Kumar', 'Sharma', 'Patel', 'Singh', 'Reddy', 'Gupta', 'Verma', 'Iyer',
                     'Rao', 'Nair', 'Mehta', 'Joshi', 'Desai', 'Agarwal', 'Mishra', 'Chopra']

        students = []
        roll_counter = 1

        for section in sections:
            # Create 30-40 students per section
            num_students = random.randint(30, min(40, section.capacity))
            
            for i in range(num_students):
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                
                # Generate email
                email = f'{first_name.lower()}.{last_name.lower()}{roll_counter}@student.university.edu'
                
                # Generate roll number
                roll_number = f'{section.code}-{roll_counter:03d}'
                
                user = CustomUser.objects.create_user(
                    email=email,
                    password='password123',
                    first_name=first_name,
                    last_name=last_name,
                    user_type='student'
                )
                
                student = Student.objects.create(
                    user=user,
                    roll_number=roll_number,
                    section=section
                )
                
                students.append(student)
                roll_counter += 1

            self.stdout.write(f'  ✓ Created {num_students} students for section: {section.code}')

        return students

    def create_class_sessions(self, subjects, sections, teachers):
        """Create class sessions for the past 30 days"""
        self.stdout.write('Creating class sessions...')
        
        class_sessions = []
        
        # Time slots for classes
        time_slots = [
            (time(9, 0), time(10, 0)),
            (time(10, 0), time(11, 0)),
            (time(11, 0), time(12, 0)),
            (time(12, 0), time(13, 0)),
            (time(14, 0), time(15, 0)),
            (time(15, 0), time(16, 0)),
            (time(16, 0), time(17, 0)),
        ]

        # Create sessions for last 30 days (excluding weekends)
        start_date = timezone.now().date() - timedelta(days=30)
        
        for day_offset in range(31):
            current_date = start_date + timedelta(days=day_offset)
            
            # Skip weekends
            if current_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                continue

            # Create 3-5 random sessions per day
            num_sessions = random.randint(3, 5)
            
            for _ in range(num_sessions):
                # Pick random subject, section, and teacher
                subject = random.choice(subjects)
                section = random.choice(sections)
                
                # Find a teacher who teaches both this subject and section
                valid_teachers = [
                    t for t in teachers
                    if subject in t.subjects.all() and section in t.sections.all()
                ]
                
                if not valid_teachers:
                    continue
                
                teacher = random.choice(valid_teachers)
                start_time, end_time = random.choice(time_slots)
                
                # Check if session already exists (avoid duplicates)
                existing = ClassSession.objects.filter(
                    date=current_date,
                    subject=subject,
                    section=section,
                    start_time=start_time
                ).exists()
                
                if existing:
                    continue

                session = ClassSession.objects.create(
                    subject=subject,
                    section=section,
                    teacher=teacher,
                    date=current_date,
                    start_time=start_time,
                    end_time=end_time,
                    topic=f'{subject.name} - Lecture {random.randint(1, 20)}',
                    attendance_marked=True  # Mark as completed
                )
                
                class_sessions.append(session)

        self.stdout.write(f'  ✓ Created {len(class_sessions)} class sessions')
        return class_sessions

    def create_attendance_records(self, class_sessions, students):
        """Create attendance records for class sessions"""
        self.stdout.write('Creating attendance records...')
        
        attendance_records = []
        
        for session in class_sessions:
            # Get students from this session's section
            section_students = [s for s in students if s.section == session.section]
            
            for student in section_students:
                # 80% chance of being present (realistic attendance)
                is_present = random.random() < 0.80
                
                # Some absent students might have remarks
                remarks = ''
                if not is_present and random.random() < 0.3:
                    remarks = random.choice(['Medical Leave', 'Late', 'Family Emergency', 'Sick'])
                
                attendance = Attendance.objects.create(
                    class_session=session,
                    student=student,
                    is_present=is_present,
                    remarks=remarks
                )
                
                attendance_records.append(attendance)

        self.stdout.write(f'  ✓ Created {len(attendance_records)} attendance records')

    def print_summary(self):
        """Print summary of created data"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 DATA SUMMARY'))
        self.stdout.write('='*50)
        
        self.stdout.write(f'Sections: {Section.objects.count()}')
        self.stdout.write(f'Subjects: {Subject.objects.count()}')
        self.stdout.write(f'Management Users: {CustomUser.objects.filter(user_type="management").count()}')
        self.stdout.write(f'Teachers: {Teacher.objects.count()}')
        self.stdout.write(f'Students: {Student.objects.count()}')
        self.stdout.write(f'Class Sessions: {ClassSession.objects.count()}')
        self.stdout.write(f'Attendance Records: {Attendance.objects.count()}')
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('🔑 DEFAULT LOGIN CREDENTIALS'))
        self.stdout.write('='*50)
        self.stdout.write('Password for all users: password123')
        self.stdout.write('')
        self.stdout.write('Management: admin@university.edu')
        self.stdout.write('Teacher: amit.verma@university.edu')
        self.stdout.write('Student: (check student emails in admin panel)')
        self.stdout.write('='*50 + '\n')