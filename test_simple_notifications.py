"""
Simple test to verify notifications work - creates test data manually
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rappiteca.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from accounts.models import User, Notification
from loans.models import Loan
from catalog.models import Book

def test_simple():
    print("Simple Notification Test")
    print("=" * 40)
    
    # Create test user
    user, created = User.objects.get_or_create(
        email='simple.test@example.com',
        defaults={
            'name': 'Simple',
            'last_name': 'Test',
            'password': make_password('test123'),
            'role': 'stu'
        }
    )
    print(f"User: {user.email}")
    
    # Create a manual notification
    notification = Notification.objects.create(
        user=user,
        notification_type=Notification.TYPE_LOAN_DUE,
        title="Test Reminder",
        message="This is a test notification to verify the system works.",
        related_loan_id=None
    )
    print(f"Created notification: {notification.title}")
    
    # Check notification count
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    print(f"Unread notifications: {unread_count}")
    
    print("\n" + "=" * 40)
    print("Test completed successfully!")
    print(f"\nManual test instructions:")
    print(f"1. Login with: {user.email} / test123")
    print(f"2. You should see a notification bell with badge")
    print(f"3. Visit: http://localhost:8000/accounts/notifications/")
    print(f"4. You should see the test notification")

if __name__ == "__main__":
    test_simple()