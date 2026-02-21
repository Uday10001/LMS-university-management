from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta, time, date
from django.db.models import Q
import random

from apps.accounts.models import CustomUser, Student, Teacher
from apps.academic.models import Section, Subject, TimetableSlot
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
            sections  = self.create_sections()
            subjects  = self.create_subjects()
            self.create_management_users()
            teachers  = self.create_teachers(subjects, sections)
            students  = self.create_students(sections)
            slots     = self.create_timetable_slots(sections, subjects, teachers)
            # sessions  = self.create_sessions_from_slots(slots)
            # self.create_attendance_records(sessions, students)

        self.stdout.write(self.style.SUCCESS('✅ Data population completed!'))
        self.print_summary()

    # ── Clear ─────────────────────────────────────────────────

    def clear_data(self):
        Attendance.objects.all().delete()
        ClassSession.objects.all().delete()
        TimetableSlot.objects.all().delete()
        Student.objects.all().delete()
        Teacher.objects.all().delete()
        Subject.objects.all().delete()
        Section.objects.all().delete()
        CustomUser.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('✅ Existing data cleared'))

    # ── Sections ──────────────────────────────────────────────

    def create_sections(self):
        self.stdout.write('Creating sections...')
        sections_data = [
            {'name': 'Computer Science A', 'code': 'CSE-A', 'semester': 1, 'capacity': 60},
            {'name': 'Computer Science B', 'code': 'CSE-B', 'semester': 1, 'capacity': 60},
            {'name': 'Electronics A',      'code': 'ECE-A', 'semester': 1, 'capacity': 50},
            {'name': 'Computer Science C', 'code': 'CSE-C', 'semester': 3, 'capacity': 55},
            {'name': 'Information Tech A', 'code': 'IT-A',  'semester': 3, 'capacity': 50},
            {'name': 'Computer Science D', 'code': 'CSE-D', 'semester': 5, 'capacity': 45},
            {'name': 'Mechanical A',       'code': 'ME-A',  'semester': 5, 'capacity': 40},
        ]
        sections = []
        for data in sections_data:
            section = Section.objects.create(
                name=data['name'], code=data['code'],
                semester=data['semester'], academic_year='2024-25',
                capacity=data['capacity']
            )
            sections.append(section)
            self.stdout.write(f'  ✓ {section.code}')
        return sections

    # ── Subjects ──────────────────────────────────────────────

    def create_subjects(self):
        self.stdout.write('Creating subjects...')
        subjects_data = [
            # Semester 1
            {'name': 'Programming Fundamentals', 'code': 'CSE101', 'credits': 4, 'semester': 1},
            {'name': 'Mathematics I',            'code': 'MATH101','credits': 4, 'semester': 1},
            {'name': 'Physics',                  'code': 'PHY101', 'credits': 3, 'semester': 1},
            {'name': 'English Communication',    'code': 'ENG101', 'credits': 2, 'semester': 1},
            # Semester 3
            {'name': 'Data Structures',          'code': 'CSE201', 'credits': 4, 'semester': 3},
            {'name': 'Database Management',      'code': 'CSE202', 'credits': 4, 'semester': 3},
            {'name': 'Computer Networks',        'code': 'CSE203', 'credits': 3, 'semester': 3},
            {'name': 'Mathematics III',          'code': 'MATH201','credits': 3, 'semester': 3},
            # Semester 5
            {'name': 'Machine Learning',         'code': 'CSE301', 'credits': 4, 'semester': 5},
            {'name': 'Web Technologies',         'code': 'CSE302', 'credits': 3, 'semester': 5},
            {'name': 'Software Engineering',     'code': 'CSE303', 'credits': 3, 'semester': 5},
            {'name': 'Cloud Computing',          'code': 'CSE304', 'credits': 3, 'semester': 5},
        ]
        subjects = []
        for data in subjects_data:
            subject = Subject.objects.create(
                name=data['name'], code=data['code'],
                credits=data['credits'], semester=data['semester'],
                is_active=True
            )
            subjects.append(subject)
            self.stdout.write(f'  ✓ {subject.code}')
        return subjects

    # ── Management Users ──────────────────────────────────────

    def create_management_users(self):
        self.stdout.write('Creating management users...')
        for data in [
            {'email': 'admin@university.edu',   'first_name': 'Admin',  'last_name': 'User'},
            {'email': 'hod.cse@university.edu', 'first_name': 'Rajesh', 'last_name': 'Kumar'},
            {'email': 'dean@university.edu',    'first_name': 'Priya',  'last_name': 'Sharma'},
        ]:
            user = CustomUser.objects.create_user(
                email=data['email'], password='password123',
                first_name=data['first_name'], last_name=data['last_name'],
                user_type='management'
            )
            self.stdout.write(f'  ✓ {user.email}')

    # ── Teachers ──────────────────────────────────────────────

    def create_teachers(self, subjects, sections):
        self.stdout.write('Creating teachers...')

        # Define which subjects + sections each teacher handles
        # This is deliberate so timetable slots are consistent
        teachers_config = [
            {
                'email': 'amit.verma@university.edu',
                'first_name': 'Amit',   'last_name': 'Verma',
                'emp_id': 'EMP1001',    'dept': 'Computer Science',
                'subject_codes': ['CSE101', 'CSE201'],
                'section_codes': ['CSE-A', 'CSE-B'],
            },
            {
                'email': 'neha.singh@university.edu',
                'first_name': 'Neha',   'last_name': 'Singh',
                'emp_id': 'EMP1002',    'dept': 'Computer Science',
                'subject_codes': ['CSE202', 'CSE301'],
                'section_codes': ['CSE-C', 'CSE-D'],
            },
            {
                'email': 'rahul.gupta@university.edu',
                'first_name': 'Rahul',  'last_name': 'Gupta',
                'emp_id': 'EMP1003',    'dept': 'Mathematics',
                'subject_codes': ['MATH101', 'MATH201'],
                'section_codes': ['CSE-A', 'ECE-A', 'CSE-C'],
            },
            {
                'email': 'priya.patel@university.edu',
                'first_name': 'Priya',  'last_name': 'Patel',
                'emp_id': 'EMP1004',    'dept': 'Computer Science',
                'subject_codes': ['CSE203', 'CSE302'],
                'section_codes': ['IT-A', 'CSE-D'],
            },
            {
                'email': 'vikram.reddy@university.edu',
                'first_name': 'Vikram', 'last_name': 'Reddy',
                'emp_id': 'EMP1005',    'dept': 'Electronics',
                'subject_codes': ['PHY101'],
                'section_codes': ['ECE-A', 'ME-A'],
            },
            {
                'email': 'anita.desai@university.edu',
                'first_name': 'Anita',  'last_name': 'Desai',
                'emp_id': 'EMP1006',    'dept': 'English',
                'subject_codes': ['ENG101', 'CSE303', 'CSE304'],
                'section_codes': ['CSE-B', 'ME-A', 'IT-A'],
            },
        ]

        subject_map = {s.code: s for s in subjects}
        section_map = {s.code: s for s in Section.objects.all()}
        teachers    = []

        for config in teachers_config:
            user = CustomUser.objects.create_user(
                email=config['email'], password='password123',
                first_name=config['first_name'],
                last_name=config['last_name'],
                user_type='teacher'
            )
            teacher = Teacher.objects.create(
                user=user,
                employee_id=config['emp_id'],
                department=config['dept']
            )
            teacher.subjects.set([
                subject_map[c] for c in config['subject_codes']
                if c in subject_map
            ])
            teacher.sections.set([
                section_map[c] for c in config['section_codes']
                if c in section_map
            ])
            teachers.append((teacher, config))
            self.stdout.write(f'  ✓ {teacher.employee_id} — {user.get_full_name()}')

        return teachers

    # ── Students ──────────────────────────────────────────────

    def create_students(self, sections):
        self.stdout.write('Creating students...')
        first_names = [
            'Aarav','Vivaan','Aditya','Arjun','Sai','Reyansh','Ayaan',
            'Krishna','Ishaan','Shaurya','Aadhya','Ananya','Diya','Ira',
            'Kiara','Kavya','Myra','Navya','Saanvi','Sara','Aarush',
            'Advait','Arnav','Dhruv',
        ]
        last_names = [
            'Kumar','Sharma','Patel','Singh','Reddy','Gupta','Verma',
            'Iyer','Rao','Nair','Mehta','Joshi','Desai','Agarwal',
        ]
        students    = []
        roll_counter = 1

        for section in sections:
            num_students = random.randint(25, min(35, section.capacity))
            for _ in range(num_students):
                fn    = random.choice(first_names)
                ln    = random.choice(last_names)
                email = (
                    f'{fn.lower()}.{ln.lower()}'
                    f'{roll_counter}@student.university.edu'
                )
                roll  = f'{section.code}-{roll_counter:03d}'
                user  = CustomUser.objects.create_user(
                    email=email, password='password123',
                    first_name=fn, last_name=ln,
                    user_type='student'
                )
                student = Student.objects.create(
                    user=user, roll_number=roll, section=section
                )
                students.append(student)
                roll_counter += 1

            self.stdout.write(
                f'  ✓ {num_students} students → {section.code}'
            )

        return students

    # ── Timetable Slots ───────────────────────────────────────

    def create_timetable_slots(self, sections, subjects, teachers):
        """
        Create a clash-free weekly timetable.
        Two fixes applied vs previous version:
          - EMP1003/MATH101/CSE-A moved Mon 10:00→11:00 (was clashing with IT-A/MATH201)
          - EMP1006/ENG101/CSE-A moved Tue 09:00→14:00 (was clashing with CSE-D/CSE303)
        """
        self.stdout.write('Creating timetable slots...')

        subject_map    = {s.code: s for s in subjects}
        section_map    = {s.code: s for s in Section.objects.all()}
        teacher_map    = {t.employee_id: t for t, _ in teachers}
        effective_from = date.today() - timedelta(days=30)

        # (section, subject, teacher, day 0=Mon, start, end, room)
        timetable_data = [

            # ── CSE-A (Semester 1) ────────────────────────────────
            ('CSE-A', 'CSE101', 'EMP1001', 0, time(9,  0), time(10, 0), 'A-101'),
            ('CSE-A', 'MATH101','EMP1003', 0, time(11, 0), time(12, 0), 'A-101'), # ✅ was 10:00
            ('CSE-A', 'ENG101', 'EMP1006', 1, time(14, 0), time(15, 0), 'A-101'), # ✅ was 09:00
            ('CSE-A', 'PHY101', 'EMP1005', 1, time(10, 0), time(11, 0), 'A-101'),
            ('CSE-A', 'CSE101', 'EMP1001', 2, time(11, 0), time(12, 0), 'A-101'),
            ('CSE-A', 'MATH101','EMP1003', 3, time(9,  0), time(10, 0), 'A-101'),
            ('CSE-A', 'ENG101', 'EMP1006', 4, time(14, 0), time(15, 0), 'A-101'),

            # ── CSE-B (Semester 1) ────────────────────────────────
            ('CSE-B', 'CSE101', 'EMP1001', 0, time(11, 0), time(12, 0), 'A-102'),
            ('CSE-B', 'MATH101','EMP1003', 1, time(11, 0), time(12, 0), 'A-102'),
            ('CSE-B', 'ENG101', 'EMP1006', 2, time(9,  0), time(10, 0), 'A-102'),
            ('CSE-B', 'PHY101', 'EMP1005', 2, time(10, 0), time(11, 0), 'B-Lab'),
            ('CSE-B', 'CSE101', 'EMP1001', 3, time(11, 0), time(12, 0), 'A-102'),
            ('CSE-B', 'MATH101','EMP1003', 4, time(9,  0), time(10, 0), 'A-102'),

            # ── ECE-A (Semester 1) ────────────────────────────────
            ('ECE-A', 'PHY101', 'EMP1005', 0, time(14, 0), time(15, 0), 'C-201'),
            ('ECE-A', 'MATH101','EMP1003', 1, time(14, 0), time(15, 0), 'C-201'),
            ('ECE-A', 'ENG101', 'EMP1006', 2, time(14, 0), time(15, 0), 'C-201'),
            ('ECE-A', 'PHY101', 'EMP1005', 3, time(14, 0), time(15, 0), 'C-Lab'),
            ('ECE-A', 'MATH101','EMP1003', 4, time(11, 0), time(12, 0), 'C-201'),

            # ── CSE-C (Semester 3) ────────────────────────────────
            ('CSE-C', 'CSE201', 'EMP1001', 0, time(14, 0), time(15, 0), 'D-301'),
            ('CSE-C', 'CSE202', 'EMP1002', 0, time(15, 0), time(16, 0), 'D-301'),
            ('CSE-C', 'MATH201','EMP1003', 1, time(15, 0), time(16, 0), 'D-301'),
            ('CSE-C', 'CSE203', 'EMP1004', 2, time(15, 0), time(16, 0), 'D-301'),
            ('CSE-C', 'CSE201', 'EMP1001', 3, time(15, 0), time(16, 0), 'D-301'),
            ('CSE-C', 'CSE202', 'EMP1002', 4, time(15, 0), time(16, 0), 'D-301'),

            # ── IT-A (Semester 3) ─────────────────────────────────
            ('IT-A',  'CSE203', 'EMP1004', 0, time(9,  0), time(10, 0), 'E-101'),
            ('IT-A',  'MATH201','EMP1003', 0, time(10, 0), time(11, 0), 'E-101'),
            ('IT-A',  'CSE202', 'EMP1002', 1, time(9,  0), time(10, 0), 'E-101'),
            ('IT-A',  'ENG101', 'EMP1006', 1, time(11, 0), time(12, 0), 'E-101'),
            ('IT-A',  'CSE203', 'EMP1004', 3, time(9,  0), time(10, 0), 'E-101'),
            ('IT-A',  'MATH201','EMP1003', 4, time(14, 0), time(15, 0), 'E-101'),

            # ── CSE-D (Semester 5) ────────────────────────────────
            ('CSE-D', 'CSE301', 'EMP1002', 0, time(9,  0), time(10, 0), 'F-401'),
            ('CSE-D', 'CSE302', 'EMP1004', 0, time(10, 0), time(11, 0), 'F-401'),
            ('CSE-D', 'CSE303', 'EMP1006', 1, time(9,  0), time(10, 0), 'F-401'),
            ('CSE-D', 'CSE304', 'EMP1006', 1, time(10, 0), time(11, 0), 'F-401'),
            ('CSE-D', 'CSE301', 'EMP1002', 2, time(9,  0), time(10, 0), 'F-401'),
            ('CSE-D', 'CSE302', 'EMP1004', 3, time(10, 0), time(11, 0), 'F-Lab'),
            ('CSE-D', 'CSE303', 'EMP1006', 4, time(9,  0), time(10, 0), 'F-401'),

            # ── ME-A (Semester 5) ─────────────────────────────────
            ('ME-A',  'PHY101', 'EMP1005', 0, time(9,  0), time(10, 0), 'G-101'),
            ('ME-A',  'ENG101', 'EMP1006', 0, time(10, 0), time(11, 0), 'G-101'),
            ('ME-A',  'PHY101', 'EMP1005', 2, time(9,  0), time(10, 0), 'G-Lab'),
            ('ME-A',  'ENG101', 'EMP1006', 3, time(10, 0), time(11, 0), 'G-101'),
            ('ME-A',  'CSE304', 'EMP1006', 4, time(11, 0), time(12, 0), 'G-101'),
        ]

        slots   = []
        created = 0
        skipped = 0

        for row in timetable_data:
            sec_code, sub_code, emp_id, day, start, end, room = row

            section = section_map.get(sec_code)
            subject = subject_map.get(sub_code)
            teacher = teacher_map.get(emp_id)

            if not section or not subject or not teacher:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Skipping {sec_code}/{sub_code}/{emp_id} — not found'
                    )
                )
                continue

            try:
                slot, was_created = TimetableSlot.objects.get_or_create(
                    section=section,
                    day_of_week=day,
                    start_time=start,
                    defaults={
                        'subject':        subject,
                        'teacher':        teacher,
                        'end_time':       end,
                        'room':           room,
                        'is_active':      True,
                        'effective_from': effective_from,
                    }
                )
                slots.append(slot)
                if was_created:
                    created += 1
                else:
                    skipped += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed {sec_code}/{sub_code}/{emp_id}: {e}'
                    )
                )

        self.stdout.write(
            f'  ✓ Timetable slots — '
            f'Created: {created}, Already existed: {skipped}'
        )
        return slots

    # ── Summary ───────────────────────────────────────────────

    def print_summary(self):
        from apps.academic.models import TimetableSlot as TS
        self.stdout.write('\n' + '='*52)
        self.stdout.write(self.style.SUCCESS('📊  DATA SUMMARY'))
        self.stdout.write('='*52)
        self.stdout.write(f'  Sections          : {Section.objects.count()}')
        self.stdout.write(f'  Subjects          : {Subject.objects.count()}')
        self.stdout.write(f'  Timetable Slots   : {TS.objects.count()}')
        self.stdout.write(
            f'  Management Users  : '
            f'{CustomUser.objects.filter(user_type="management").count()}'
        )
        self.stdout.write(f'  Teachers          : {Teacher.objects.count()}')
        self.stdout.write(f'  Students          : {Student.objects.count()}')
        self.stdout.write(f'  Class Sessions    : {ClassSession.objects.count()}')
        self.stdout.write(f'  Attendance Records: {Attendance.objects.count()}')
        self.stdout.write('\n' + '='*52)
        self.stdout.write(self.style.SUCCESS('🔑  DEFAULT CREDENTIALS'))
        self.stdout.write('='*52)
        self.stdout.write('  Password (all)  : password123')
        self.stdout.write('  Management      : admin@university.edu')
        self.stdout.write('  Teacher         : amit.verma@university.edu')
        self.stdout.write('  Student         : check admin panel for emails')
        self.stdout.write('='*52 + '\n')