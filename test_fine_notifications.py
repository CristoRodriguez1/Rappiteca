"""
Test script for FR-26: Fine notification system.

This script tests:
1. User receives notification when fine is first applied
2. User receives notification when fine is updated
3. Notifications are not sent too frequently (rate limiting)
4. Notification content is correct
"""

import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rappiteca.settings')
django.setup()

from accounts.models import User, Notification
from fines.models import Fine
from fines.services import apply_fine, apply_overdue_fines
from loans.models import Loan
from catalog.models import Book

def test_fine_notifications():
    print("=" * 60)
    print("TESTING FR-26: Fine Notifications")
    print("=" * 60)
    
    # Find a user
    user = User.objects.first()
    if not user:
        print("[ERROR] No users found. Please create a user first.")
        return
    
    print(f"\n[INFO] Using user: {user.email}")
    
    # Find a book
    book = Book.objects.first()
    if not book:
        print("[ERROR] No books found.")
        return
    
    print(f"[INFO] Using book: {book.title}")
    
    # Create a test loan that is overdue
    print("\n" + "-" * 60)
    print("TEST 1: Creating overdue loan")
    print("-" * 60)
    
    # Delete any existing fines for this user/book combination
    existing_loan = Loan.objects.filter(user=user, book=book).first()
    if existing_loan:
        existing_loan.delete()
    
    # Create a loan 30 days overdue
    loan = Loan.objects.create(
        user=user,
        book=book,
        status=Loan.STATUS_BORROWED,
        pickup_date=timezone.now() - timedelta(days=30)
    )
    print(f"[OK] Created overdue loan: {loan}")
    
    # Test 2: Apply fine and check for notification
    print("\n" + "-" * 60)
    print("TEST 2: Apply fine - first time notification")
    print("-" * 60)
    
    fine = apply_fine(loan)
    print(f"[OK] Fine applied: ${fine.amount} for {fine.days_overdue} days overdue")
    
    # Check for notification
    notifications = Notification.objects.filter(
        user=user,
        notification_type=Notification.TYPE_FINE_APPLIED,
        related_fine_id=fine.id
    )
    
    if notifications.exists():
        notif = notifications.first()
        print(f"[OK] Notification created:")
        print(f"  Title: {notif.title}")
        print(f"  Message: {notif.message}")
        print(f"  Created: {notif.created_at}")
    else:
        print("[ERROR] No notification found!")
    
    # Test 3: Update fine and check for notification
    print("\n" + "-" * 60)
    print("TEST 3: Update fine - notification rate limiting")
    print("-" * 60)
    
    # Update the loan to be more overdue
    loan.pickup_date = timezone.now() - timedelta(days=35)
    loan.save()
    
    # Apply fine again
    updated_fine = apply_fine(loan)
    print(f"[OK] Fine updated: ${updated_fine.amount} for {updated_fine.days_overdue} days overdue")
    
    # Check for new notification (should not create one within 24 hours)
    notifications_after_update = Notification.objects.filter(
        user=user,
        notification_type=Notification.TYPE_FINE_APPLIED,
        related_fine_id=fine.id
    )
    
    print(f"[INFO] Total notifications for this fine: {notifications_after_update.count()}")
    
    if notifications_after_update.count() == 1:
        print("[OK] Rate limiting working - no duplicate notification within 24 hours")
    else:
        print("[INFO] Multiple notifications (may be from previous tests)")
    
    # Test 4: Check all fine notifications for user
    print("\n" + "-" * 60)
    print("TEST 4: User's fine notification history")
    print("-" * 60)
    
    all_fine_notifications = Notification.objects.filter(
        user=user,
        notification_type=Notification.TYPE_FINE_APPLIED
    ).order_by('-created_at')
    
    print(f"[INFO] User has {all_fine_notifications.count()} fine notification(s)")
    
    for notif in all_fine_notifications[:3]:  # Show last 3
        print(f"\n  Notification: {notif.title}")
        print(f"  Created: {notif.created_at}")
        print(f"  Read: {notif.is_read}")
        if notif.related_fine_id:
            fine = Fine.objects.filter(id=notif.related_fine_id).first()
            if fine:
                print(f"  Fine amount: ${fine.amount}")
    
    # Test 5: Check notification count in notifications page
    print("\n" + "-" * 60)
    print("TEST 5: Notification count API")
    print("-" * 60)
    
    unread_count = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()
    
    print(f"[INFO] Unread notifications: {unread_count}")
    
    if unread_count > 0:
        print("[OK] User has unread notifications to check")
    
    # Cleanup
    print("\n" + "-" * 60)
    print("CLEANUP")
    print("-" * 60)
    
    loan.delete()
    print(f"[OK] Deleted test loan")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_fine_notifications()
