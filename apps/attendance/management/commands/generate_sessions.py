from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q                    # ✅ import Q directly
from apps.academic.models import TimetableSlot
from apps.attendance.models import ClassSession


class Command(BaseCommand):
    help = 'Generate ClassSession records for today from active TimetableSlots'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Generate for a specific date (YYYY-MM-DD). Defaults to today.'
        )

    def handle(self, *args, **options):
        from datetime import datetime

        if options['date']:
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        weekday = target_date.weekday()   # 0=Mon … 5=Sat, 6=Sun

        if weekday == 6:
            self.stdout.write(
                self.style.WARNING('Sunday — no sessions generated.')
            )
            return

        slots = TimetableSlot.objects.filter(
            day_of_week=weekday,
            is_active=True,
            effective_from__lte=target_date,
        ).filter(
            Q(effective_to__isnull=True) |    # ✅ Q used directly
            Q(effective_to__gte=target_date)
        ).select_related('subject', 'section', 'teacher')

        created = 0
        skipped = 0

        for slot in slots:
            session, was_created = ClassSession.objects.get_or_create(
                date=target_date,
                subject=slot.subject,
                section=slot.section,
                start_time=slot.start_time,
                defaults={
                    'timetable_slot': slot,
                    'teacher':        slot.teacher,
                    'end_time':       slot.end_time,
                    'room':           slot.room,
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'{target_date} — ✅ Created: {created}, '
                f'Already existed: {skipped}'
            )
        )