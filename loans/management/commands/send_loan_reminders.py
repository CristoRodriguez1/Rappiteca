"""
Management command to check for loans approaching due date and send reminders.

This command should be run periodically (e.g., daily via cron) to check for loans
that are approaching their due date and send both in-app notifications and email
reminders to users.

Reminders are sent at:
- 1 week before due date (7 days)
- 3 days before due date
- On the due date (0 days)

Usage:
    python manage.py send_loan_reminders
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from loans.models import Loan
from accounts.models import Notification


class Command(BaseCommand):
    help = 'Check for loans approaching due date and send reminders'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Define reminder periods: (days_before, notification_type, description)
        reminder_periods = [
            (7, Notification.TYPE_LOAN_DUE_WEEK, '1 week before'),
            (3, Notification.TYPE_LOAN_DUE_3_DAYS, '3 days before'),
            (0, Notification.TYPE_LOAN_DUE_SAME_DAY, 'same day'),
        ]
        
        total_sent = 0
        total_skipped = 0
        period_results = {}
        
        for days_before, period_type, description in reminder_periods:
            due_date = today + timedelta(days=days_before)
            
            # Find loans that are due in days_before days
            # Due date = pickup date + 14 days, so pickup date = due date - 14 days
            target_pickup_date = due_date - timedelta(days=14)
            
            loans_due = Loan.objects.filter(
                status=Loan.STATUS_BORROWED,
                pickup_date__date=target_pickup_date
            ).select_related('user', 'book')
            
            sent_count = 0
            skipped_count = 0
            
            for loan in loans_due:
                # Check if we already sent a reminder for this loan for this period
                existing_notification = Notification.objects.filter(
                    user=loan.user,
                    notification_type=period_type,
                    related_loan_id=loan.id
                ).exists()
                
                if existing_notification:
                    skipped_count += 1
                    self.stdout.write(f'  Already sent reminder ({description}): {loan.book.title} -> {loan.user.email}')
                    continue
                
                # Create appropriate message based on timing
                if days_before == 7:
                    title = f'Weekly reminder: "{loan.book.title}"'
                    message = f'Your loan of "{loan.book.title}" is due in 1 week ({due_date}). '
                elif days_before == 3:
                    title = f'Reminder: "{loan.book.title}" due soon'
                    message = f'Your loan of "{loan.book.title}" is due in 3 days ({due_date}). '
                else:  # same day
                    title = f'Due today: "{loan.book.title}"'
                    message = f'Your loan of "{loan.book.title}" is due today ({due_date}). '
                
                message += f'Please return it before the due date.'
                
                # Create in-app notification
                notification = Notification.objects.create(
                    user=loan.user,
                    notification_type=period_type,
                    title=title,
                    message=message,
                    related_loan_id=loan.id
                )
                
                # Send email reminder
                try:
                    email_subject = title
                    email_message = f'Hello {loan.user.name},\n\n'
                    email_message += message + '\n\n'
                    email_message += 'If you have already returned the book, you can ignore this message.\n\n'
                    email_message += 'Best regards,\n'
                    email_message += 'Rappiteca Team'
                    
                    send_mail(
                        subject=email_subject,
                        message=email_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[loan.user.email],
                        fail_silently=False,
                    )
                    sent_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Reminder sent ({description}): {loan.book.title} -> {loan.user.email}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Error sending email to {loan.user.email}: {str(e)}'))
                    # Still keep the in-app notification even if email fails
            
            period_results[description] = {'sent': sent_count, 'skipped': skipped_count}
            total_sent += sent_count
            total_skipped += skipped_count
        
        # Check for overdue loans
        overdue_loans = Loan.objects.filter(
            status=Loan.STATUS_BORROWED,
            pickup_date__date__lt=today - timedelta(days=14)
        ).select_related('user', 'book')
        
        overdue_count = 0
        overdue_email_count = 0
        for loan in overdue_loans:
            # Check if we already sent an overdue notification
            existing_notification = Notification.objects.filter(
                user=loan.user,
                notification_type=Notification.TYPE_LOAN_OVERDUE,
                related_loan_id=loan.id
            ).exists()
            
            if existing_notification:
                continue
            
            # Calculate how many days overdue
            days_overdue = (today - loan.pickup_date.date()).days - 14
            
            # Create overdue notification
            notification = Notification.objects.create(
                user=loan.user,
                notification_type=Notification.TYPE_LOAN_OVERDUE,
                title=f'Overdue: "{loan.book.title}"',
                message=f'Your loan of "{loan.book.title}" is overdue by {days_overdue} day(s). '
                        f'Please return it as soon as possible to avoid fines.',
                related_loan_id=loan.id
            )
            
            # Send email for overdue loan
            try:
                email_subject = f'URGENT: Overdue Loan - "{loan.book.title}"'
                email_message = f'Hello {loan.user.name},\n\n'
                email_message += f'Your loan of "{loan.book.title}" is overdue by {days_overdue} day(s).\n\n'
                email_message += f'Original due date: {loan.pickup_date.date() + timedelta(days=14)}\n'
                email_message += f'Days overdue: {days_overdue}\n\n'
                email_message += 'Please return the book to the library as soon as possible to avoid fines.\n\n'
                email_message += 'If you have already returned the book, please disregard this message.\n\n'
                email_message += 'Best regards,\n'
                email_message += 'Rappiteca Team'
                
                send_mail(
                    subject=email_subject,
                    message=email_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[loan.user.email],
                    fail_silently=False,
                )
                overdue_email_count += 1
                self.stdout.write(self.style.WARNING(f'  [WARN] Overdue alert sent ({days_overdue} days): {loan.book.title} -> {loan.user.email}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Error sending overdue email to {loan.user.email}: {str(e)}'))
                # Still keep the in-app notification even if email fails
            
            overdue_count += 1
        
        # Print summary
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('REMINDER SUMMARY')
        self.stdout.write('=' * 60)
        
        for description, results in period_results.items():
            if results['sent'] > 0:
                self.stdout.write(self.style.SUCCESS(f'{description}: {results["sent"]} sent'))
            if results['skipped'] > 0:
                self.stdout.write(f'{description}: {results["skipped"]} already notified')
        
        if overdue_count > 0:
            self.stdout.write(self.style.WARNING(f'Overdue: {overdue_count} notifications ({overdue_email_count} emails sent)'))
        
        if total_sent == 0 and total_skipped == 0 and overdue_count == 0:
            self.stdout.write(self.style.SUCCESS('No loans require reminders today.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Total reminders sent: {total_sent}'))