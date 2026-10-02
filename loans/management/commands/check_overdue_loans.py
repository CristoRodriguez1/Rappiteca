"""
Management command to check for overdue loans and send alerts.

This command should be run periodically (e.g., daily via cron) to check for loans
that have passed their due date and send both in-app notifications and email alerts to users.

FR-19: Overdue loan alert - IF a loan's due date has passed THEN THE Rappiteca system 
SHOULD send the user an overdue alert via email and/or in-app notification.

Usage:
    python manage.py check_overdue_loans
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from loans.models import Loan
from accounts.models import Notification


class Command(BaseCommand):
    help = 'Check for overdue loans and send alerts'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find all overdue loans (pickup date + 14 days < today)
        overdue_loans = Loan.objects.filter(
            status=Loan.STATUS_BORROWED,
            pickup_date__date__lt=today - timedelta(days=14)
        ).select_related('user', 'book')
        
        total_alerts = 0
        email_sent = 0
        email_failed = 0
        already_notified = 0
        
        for loan in overdue_loans:
            # Calculate how many days overdue
            original_due_date = loan.pickup_date.date() + timedelta(days=14)
            days_overdue = (today - original_due_date).days
            
            # Check if we already sent an overdue notification for this loan
            existing_notification = Notification.objects.filter(
                user=loan.user,
                notification_type=Notification.TYPE_LOAN_OVERDUE,
                related_loan_id=loan.id
            ).exists()
            
            if existing_notification:
                already_notified += 1
                self.stdout.write(f'  [SKIP] Already notified: {loan.book.title} -> {loan.user.email} ({days_overdue} days overdue)')
                continue
            
            # Create in-app notification
            notification = Notification.objects.create(
                user=loan.user,
                notification_type=Notification.TYPE_LOAN_OVERDUE,
                title=f'Overdue Loan: "{loan.book.title}"',
                message=f'Your loan of "{loan.book.title}" is overdue by {days_overdue} day(s). '
                        f'Original due date: {original_due_date}. '
                        f'Please return it as soon as possible to avoid fines.',
                related_loan_id=loan.id
            )
            
            # Send email alert
            try:
                email_subject = f'URGENT: Overdue Loan Alert - "{loan.book.title}"'
                email_message = f'Hello {loan.user.name},\n\n'
                email_message += f'This is an automated alert from Rappiteca.\n\n'
                email_message += f'Your loan of "{loan.book.title}" is overdue by {days_overdue} day(s).\n\n'
                email_message += f'Loan Details:\n'
                email_message += f'- Book: {loan.book.title}\n'
                email_message += f'- Author: {loan.book.author}\n'
                email_message += f'- Original due date: {original_due_date}\n'
                email_message += f'- Days overdue: {days_overdue}\n\n'
                email_message += f'Please return the book to the library as soon as possible to avoid fines.\n\n'
                email_message += f'If you have already returned this book, please disregard this message.\n\n'
                email_message += f'Best regards,\n'
                email_message += f'Rappiteca Library Team'
                
                send_mail(
                    subject=email_subject,
                    message=email_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[loan.user.email],
                    fail_silently=False,
                )
                email_sent += 1
                total_alerts += 1
                self.stdout.write(self.style.WARNING(f'  [ALERT] Overdue alert sent: {loan.book.title} -> {loan.user.email} ({days_overdue} days overdue)'))
            except Exception as e:
                email_failed += 1
                total_alerts += 1
                self.stdout.write(self.style.ERROR(f'  [ERROR] Email failed: {loan.user.email} - {str(e)}'))
                # Still count the alert as sent (in-app notification created)
        
        # Print summary
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('OVERDUE LOAN ALERT SUMMARY')
        self.stdout.write('=' * 60)
        
        if total_alerts > 0:
            self.stdout.write(self.style.SUCCESS(f'Total alerts sent: {total_alerts}'))
            self.stdout.write(self.style.SUCCESS(f'Emails sent: {email_sent}'))
            if email_failed > 0:
                self.stdout.write(self.style.ERROR(f'Emails failed: {email_failed}'))
        if already_notified > 0:
            self.stdout.write(f'Already notified: {already_notified}')
        
        if total_alerts == 0 and already_notified == 0:
            self.stdout.write(self.style.SUCCESS('No overdue loans found.'))
        else:
            self.stdout.write('')
            self.stdout.write('All users with overdue loans have been notified via in-app notification and email.')