"""
Management command to calculate and apply fines for overdue loans.

This command should be run periodically (e.g., daily via cron), like
check_overdue_loans, so the fine of each overdue loan grows with every day late.

FR-23: Calculate fine - IF a loan becomes overdue THEN THE Rappiteca system
SHOULD automatically calculate the corresponding fine based on the number of overdue days.

FR-24: Apply fine - IF a fine has been calculated for a user THEN THE Rappiteca
system SHOULD apply the fine to the user's account within 3 seconds.

Usage:
    python manage.py calculate_fines
"""

from django.core.management.base import BaseCommand

from fines.services import apply_overdue_fines, get_daily_rate


class Command(BaseCommand):
    help = 'Calculate and apply fines for overdue loans'

    def handle(self, *args, **options):
        fines = apply_overdue_fines()

        for fine in fines:
            self.stdout.write(self.style.WARNING(
                f'  [FINE] {fine.loan.book.title} -> {fine.user.email}: '
                f'{fine.days_overdue} day(s) x {fine.daily_rate} = {fine.amount}'
            ))

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('FINES SUMMARY')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Daily rate: {get_daily_rate()}')

        if fines:
            self.stdout.write(self.style.SUCCESS(f'Fines applied or updated: {len(fines)}'))
        else:
            self.stdout.write(self.style.SUCCESS('No overdue loans found.'))
