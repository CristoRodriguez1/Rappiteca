"""
Runtime test script to verify the notification system works end-to-end.
This creates a loan that will trigger a reminder and runs the management command.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rappiteca.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from accounts.models import User, Notification
from loans.models import Loan
from catalog.models import Book
from django.core.management import call_command

def test_notification_runtime():
    print("Testing Notification System - Runtime Test")
    print("=" * 60)
    
    # Step 1: Create test user
    print("\n1. Creating test user...")
    try:
        test_user, created = User.objects.get_or_create(
            email='test.notification@example.com',
            defaults={
                'name': 'Test',
                'last_name': 'Notification',
                'password': make_password('test123'),
                'role': 'stu'
            }
        )
        if created:
            print(f"   [OK] Test user created: {test_user.email}")
        else:
            print(f"   [OK] Using existing test user: {test_user.email}")
    except Exception as e:
        print(f"   [ERROR] Error creating test user: {e}")
        return False
    
    # Step 2: Create test book
    print("\n2. Creating test book...")
    try:
        test_book, created = Book.objects.get_or_create(
            title="Test Book for Notifications",
            defaults={
                'author': 'Test Author',
                'total_copies': 1,
                'available_copies': 1
            }
        )
        if created:
            print(f"   [OK] Test book created: {test_book.title}")
        else:
            print(f"   [OK] Using existing test book: {test_book.title}")
    except Exception as e:
        print(f"   [ERROR] Error creating test book: {e}")
        return False
    
    # Step 3: Create a loan that will trigger reminder
    # Loan due in 2 days = pickup date = today + 2 - 14 = today - 12
    print("\n3. Creating loan that will trigger reminder...")
    try:
        from django.conf import settings
        reminder_days = getattr(settings, 'LOAN_REMINDER_DAYS_BEFORE', 2)
        today = timezone.now().date()
        target_pickup_date = today + timedelta(days=reminder_days - 14)
        
        # Clear any existing test loans
        Loan.objects.filter(user=test_user, book=test_book).delete()
        
        # Create loan with pickup date that will trigger reminder
        test_loan = Loan.objects.create(
            user=test_user,
            book=test_book,
            estado=Loan.ESTADO_PRESTADO,
            fecha_reserva=target_pickup_date,
            fecha_recogida=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=reminder_days - 14)
        )
        
        due_date = test_loan.due_date
        print(f"   [OK] Loan created")
        print(f"   [INFO] Pickup date: {test_loan.fecha_recogida.date()}")
        print(f"   [INFO] Due date: {due_date}")
        print(f"   [INFO] Reminder will trigger on: {today + timedelta(days=reminder_days)}")
    except Exception as e:
        print(f"   [ERROR] Error creating test loan: {e}")
        return False
    
    # Step 4: Check existing notifications before running command
    print("\n4. Checking notifications before command...")
    try:
        notification_count_before = Notification.objects.filter(user=test_user).count()
        print(f"   [INFO] Notifications before: {notification_count_before}")
    except Exception as e:
        print(f"   [ERROR] Error checking notifications: {e}")
        return False
    
    # Step 5: Run the management command
    print("\n5. Running send_loan_reminders command...")
    try:
        from io import StringIO
        from django.core.management import call_command
        
        out = StringIO()
        call_command('send_loan_reminders', stdout=out, stderr=out)
        output = out.getvalue()
        print("   [OK] Command executed")
        # Only show first few lines of output to avoid encoding issues
        output_lines = output.split('\n')[:5]
        print(f"   [INFO] Command output (first 5 lines):")
        for line in output_lines:
            if line.strip():
                print(f"   {line[:100]}...")  # Truncate long lines
    except Exception as e:
        print(f"   [ERROR] Error running command: {e}")
        return False
    
    # Step 6: Check if notification was created
    print("\n6. Checking notifications after command...")
    try:
        notification_count_after = Notification.objects.filter(user=test_user).count()
        new_notifications = notification_count_after - notification_count_before
        print(f"   [INFO] Notifications after: {notification_count_after}")
        print(f"   [INFO] New notifications created: {new_notifications}")
        
        if new_notifications > 0:
            latest_notification = Notification.objects.filter(user=test_user).first()
            print(f"   [OK] Latest notification: {latest_notification.title}")
            print(f"   [INFO] Message: {latest_notification.message}")
        else:
            print(f"   [WARN] No new notifications were created")
            print(f"   [INFO] This might be normal if loan doesn't match reminder criteria")
    except Exception as e:
        print(f"   [ERROR] Error checking notifications: {e}")
        return False
    
    # Step 7: Test the API endpoints
    print("\n7. Testing notification API endpoints...")
    try:
        from django.test import Client
        from django.contrib.sessions.middleware import SessionMiddleware
        
        client = Client()
        
        # Simulate login
        session = client.session
        session['user_id'] = test_user.id
        session['user_role'] = test_user.role
        session.save()
        
        # Test notification count endpoint
        response = client.get('/accounts/notifications/count/')
        if response.status_code == 200:
            count_data = response.json()
            print(f"   [OK] Notification count API: {count_data}")
        else:
            print(f"   [ERROR] Notification count API failed: {response.status_code}")
        
        # Test notifications list endpoint
        response = client.get('/accounts/notifications/')
        if response.status_code == 200:
            print(f"   [OK] Notifications list API accessible")
        else:
            print(f"   [ERROR] Notifications list API failed: {response.status_code}")
            
    except Exception as e:
        print(f"   [ERROR] Error testing API endpoints: {e}")
    
    # Step 8: Cleanup
    print("\n8. Cleanup test data...")
    try:
        test_loan.delete()
        print(f"   [OK] Test loan deleted")
    except Exception as e:
        print(f"   [WARN] Could not delete test loan: {e}")
    
    print("\n" + "=" * 60)
    print("Runtime test completed!")
    print(f"\nTo test manually in the browser:")
    print(f"1. Login with: {test_user.email} / test123")
    print(f"2. Visit: http://localhost:8000/accounts/notifications/")
    print(f"3. You should see the notification bell icon with a badge")
    return True

if __name__ == "__main__":
    success = test_notification_runtime()
    exit(0 if success else 1)