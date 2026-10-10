from django.core.management.base import BaseCommand

from loans.models import Loan


class Command(BaseCommand):
    help = 'Cancels reservations not picked up in time and passes the copy to the queue.'

    def handle(self, *args, **options):
        expired = Loan.expire_stale_reservations()
        self.stdout.write(self.style.SUCCESS(f'Expired reservations: {expired}'))
