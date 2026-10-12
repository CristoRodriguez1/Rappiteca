"""
Test script for availability alerts with actual loan return (FR-20).

This script tests the full flow:
1. Create an availability alert for an unavailable book
2. Return a loan to make the book available
3. Verify notifications are created
4. Verify emails are sent
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rappiteca.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from accounts.models import User, Notification
from catalog.models import Book, BookAvailabilityAlert
from loans.models import Loan

def test_availability_alerts_with_loan_return():
    print("=" * 60)
    print("TESTING AVAILABILITY ALERTS WITH LOAN RETURN (FR-20)")
    print("=" * 60)
    
    # Find a user
    user = User.objects.first()
    if not user:
        print("[ERROR] No users found. Please create a user first.")
        return
    
    print(f"\n[INFO] Using user: {user.email}")
    
    # Find an active borrowed loan
    active_loan = Loan.objects.filter(
        status=Loan.STATUS_BORROWED
    ).select_related('book', 'user').first()
    
    if not active_loan:
        print("[WARN] No active borrowed loans found. Creating a test scenario...")
        # Create a book and borrow it
        test_book = Book.objects.create(
            title="Test Book for Runtime Alert Test",
            author="Test Author",
            total_copies=1,
            available_copies=0
        )
        # Create a loan to make it unavailable
        active_loan = Loan.objects.create(
            user=user,
            book=test_book,
            status=Loan.STATUS_BORROWED,
            pickup_date=timezone.now()
        )
        print(f"[INFO] Created test book and loan: {test_book.title}")
    else:
        print(f"[INFO] Found active loan: {active_loan.book.title}")
    
    book = active_loan.book
    print(f"[INFO] Book status: {book.available_copies}/{book.total_copies} available")
    
    # Test 1: Create availability alert for the book
    print("\n" + "-" * 60)
    print("TEST 1: Creating availability alert")
    print("-" * 60)
    
    # Delete any existing alerts for this book/user
    BookAvailabilityAlert.objects.filter(
        user=user,
        book=book
    ).delete()
    
    alert = BookAvailabilityAlert.objects.create(
        user=user,
        book=book,
        is_active=True
    )
    print(f"[OK] Created availability alert: {alert}")
    
    # Test 2: Check there are no waitlist entries (so alert should trigger)
    print("\n" + "-" * 60)
    print("TEST 2: Checking waitlist entries")
    print("-" * 60)
    
    from loans.models import WaitlistEntry
    waitlist_count = WaitlistEntry.objects.filter(
        book=book,
        status=WaitlistEntry.STATUS_WAITING
    ).count()
    
    print(f"[INFO] Waitlist entries: {waitlist_count}")
    
    if waitlist_count > 0:
        print("[WARN] Book has waitlist entries. Alert may not trigger immediately.")
        print("[INFO] Clearing waitlist for test...")
        WaitlistEntry.objects.filter(
            book=book,
            status=WaitlistEntry.STATUS_WAITING
        ).delete()
        print("[OK] Waitlist cleared")
    
    # Test 3: Return the loan to trigger availability notification
    print("\n" + "-" * 60)
    print("TEST 3: Returning loan to trigger notification")
    print("-" * 60)
    
    print(f"[INFO] Returning loan: {active_loan}")
    active_loan.mark_returned()
    
    # Refresh book status
    book.refresh_from_db()
    print(f"[INFO] Book status after return: {book.available_copies}/{book.total_copies} available")
    
    # Test 4: Check for notifications
    print("\n" + "-" * 60)
    print("TEST 4: Checking for availability notifications")
    print("-" * 60)
    
    notifications = Notification.objects.filter(
        user=user,
        notification_type=Notification.TYPE_BOOK_AVAILABLE,
        related_book_id=book.id
    ).order_by('-created_at')
    
    if notifications.exists():
        print(f"[OK] Found {notifications.count()} availability notification(s):")
        for notif in notifications:
            print(f"  - Title: {notif.title}")
            print(f"    Message: {notif.message}")
            print(f"    Created: {notif.created_at}")
            print(f"    Read: {notif.is_read}")
    else:
        print("[ERROR] No availability notifications found!")
        print("[INFO] This should have triggered a notification")
    
    # Test 5: Verify email would be sent (check console output above)
    print("\n" + "-" * 60)
    print("TEST 5: Email verification")
    print("-" * 60)
    
    print("[INFO] Check the console output above for email content")
    print("[INFO] Emails are printed to console in development mode")
    
    # Test 6: Clean up
    print("\n" + "-" * 60)
    print("TEST 6: Cleanup")
    print("-" * 60)
    
    # Delete the alert
    alert.delete()
    print(f"[OK] Deleted alert")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_availability_alerts_with_loan_return()
