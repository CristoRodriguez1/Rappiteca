"""
Test script to verify the notification system works correctly.
Run this with: python test_notifications.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rappiteca.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from accounts.models import User, Notification
from loans.models import Loan
from catalog.models import Book

def test_notification_system():
    print("Testing Notification System...")
    print("=" * 50)
    
    # Test 1: Create a test notification
    print("\n1. Creating test notification...")
    try:
        # Get a user to test with
        user = User.objects.first()
        if not user:
            print("   [WARN] No users found. Creating test user...")
            user = User.objects.create(
                name="Test",
                last_name="User",
                email="test@example.com",
                password="test123",
                role="stu"
            )
        
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.TYPE_LOAN_DUE,
            title="Test Notification",
            message="This is a test notification for the loan reminder system.",
            related_loan_id=None
        )
        print(f"   [OK] Notification created: {notification.title}")
    except Exception as e:
        print(f"   [ERROR] Error creating notification: {e}")
        return False
    
    # Test 2: Check notification count
    print("\n2. Testing notification count...")
    try:
        unread_count = Notification.objects.filter(user=user, is_read=False).count()
        print(f"   [OK] Unread notifications for {user.email}: {unread_count}")
    except Exception as e:
        print(f"   [ERROR] Error counting notifications: {e}")
        return False
    
    # Test 3: Mark notification as read
    print("\n3. Testing mark as read...")
    try:
        notification.is_read = True
        notification.save()
        unread_count_after = Notification.objects.filter(user=user, is_read=False).count()
        print(f"   [OK] Notification marked as read. Unread count: {unread_count_after}")
    except Exception as e:
        print(f"   [ERROR] Error marking notification as read: {e}")
        return False
    
    # Test 4: Test loan due date calculation
    print("\n4. Testing loan due date calculation...")
    try:
        # Create a test book if needed
        book = Book.objects.first()
        if not book:
            print("   [WARN] No books found. Creating test book...")
            book = Book.objects.create(
                title="Test Book",
                author="Test Author",
                total_copies=1,
                available_copies=1
            )
        
        # Create a test loan
        from django.contrib.auth.hashers import make_password
        loan = Loan.objects.create(
            user=user,
            book=book,
            estado=Loan.ESTADO_PRESTADO,
            fecha_reserva=timezone.now() - timedelta(days=1),
            fecha_recogida=timezone.now() - timedelta(days=1)
        )
        
        due_date = loan.due_date
        print(f"   [OK] Loan created with pickup date: {loan.fecha_recogida.date()}")
        print(f"   [OK] Calculated due date: {due_date}")
        
        # Clean up test loan
        loan.delete()
    except Exception as e:
        print(f"   [ERROR] Error testing loan due date: {e}")
        return False
    
    # Test 5: Check management command
    print("\n5. Testing management command availability...")
    try:
        from loans.management.commands.send_loan_reminders import Command
        print("   [OK] Management command is available")
    except Exception as e:
        print(f"   [ERROR] Error loading management command: {e}")
        return False
    
    # Clean up test notification
    print("\n6. Cleaning up test data...")
    try:
        notification.delete()
        print("   [OK] Test notification deleted")
    except Exception as e:
        print(f"   [WARN] Could not delete test notification: {e}")
    
    print("\n" + "=" * 50)
    print("[OK] All notification system tests passed!")
    return True

if __name__ == "__main__":
    success = test_notification_system()
    exit(0 if success else 1)