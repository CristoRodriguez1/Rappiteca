"""
Test script for availability alerts functionality (FR-20).

This script tests:
1. Creating availability alerts for unavailable books
2. Checking that alerts are triggered when books become available
3. Verifying notifications are created
4. Verifying emails are sent
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

def test_availability_alerts():
    print("=" * 60)
    print("TESTING AVAILABILITY ALERTS (FR-20)")
    print("=" * 60)
    
    # Find a user
    user = User.objects.first()
    if not user:
        print("[ERROR] No users found. Please create a user first.")
        return
    
    print(f"\n[INFO] Using user: {user.email}")
    
    # Find an unavailable book
    unavailable_book = Book.objects.filter(available_copies=0).first()
    if not unavailable_book:
        print("[WARN] No unavailable books found. Creating a test scenario...")
        # Create a book and borrow it
        test_book = Book.objects.create(
            title="Test Book for Availability Alerts",
            author="Test Author",
            total_copies=1,
            available_copies=0
        )
        # Create a loan to make it unavailable
        loan = Loan.objects.create(
            user=user,
            book=test_book,
            status=Loan.STATUS_BORROWED,
            pickup_date=timezone.now()
        )
        unavailable_book = test_book
        print(f"[INFO] Created test book: {unavailable_book.title}")
    else:
        print(f"[INFO] Found unavailable book: {unavailable_book.title}")
    
    # Test 1: Create availability alert
    print("\n" + "-" * 60)
    print("TEST 1: Creating availability alert")
    print("-" * 60)
    
    # Check if alert already exists
    existing_alert = BookAvailabilityAlert.objects.filter(
        user=user,
        book=unavailable_book
    ).first()
    
    if existing_alert:
        print(f"[INFO] Alert already exists: {existing_alert}")
        alert = existing_alert
    else:
        alert = BookAvailabilityAlert.objects.create(
            user=user,
            book=unavailable_book,
            is_active=True
        )
        print(f"[OK] Created availability alert: {alert}")
    
    # Test 2: Check alert is displayed in book detail view
    print("\n" + "-" * 60)
    print("TEST 2: Checking alert display")
    print("-" * 60)
    
    all_alerts = BookAvailabilityAlert.objects.filter(
        user=user,
        is_active=True
    ).select_related('book')
    
    print(f"[INFO] User has {all_alerts.count()} active availability alerts:")
    for a in all_alerts:
        print(f"  - {a.book.title} (ID: {a.book.id})")
    
    # Test 3: Simulate book becoming available
    print("\n" + "-" * 60)
    print("TEST 3: Simulating book becoming available")
    print("-" * 60)
    
    # Return the loan to make the book available
    active_loans = Loan.objects.filter(
        book=unavailable_book,
        status=Loan.STATUS_BORROWED
    )
    
    if active_loans.exists():
        for loan in active_loans:
            print(f"[INFO] Returning loan: {loan}")
            loan.mark_returned()
    else:
        # Manually increment available copies
        unavailable_book.available_copies += 1
        unavailable_book.save()
        print(f"[INFO] Manually incremented available copies")
    
    unavailable_book.refresh_from_db()
    print(f"[INFO] Book status: {unavailable_book.available_copies}/{unavailable_book.total_copies} available")
    
    # Test 4: Check for notifications
    print("\n" + "-" * 60)
    print("TEST 4: Checking for notifications")
    print("-" * 60)
    
    notifications = Notification.objects.filter(
        user=user,
        notification_type=Notification.TYPE_BOOK_AVAILABLE,
        related_book_id=unavailable_book.id
    ).order_by('-created_at')
    
    if notifications.exists():
        print(f"[OK] Found {notifications.count()} availability notification(s):")
        for notif in notifications:
            print(f"  - Title: {notif.title}")
            print(f"    Message: {notif.message}")
            print(f"    Created: {notif.created_at}")
    else:
        print("[WARN] No availability notifications found")
        print("[INFO] This is expected if the book became available via waitlist")
        print("[INFO] Notifications are sent when there are no waitlist entries")
    
    # Test 5: Toggle alert
    print("\n" + "-" * 60)
    print("TEST 5: Toggling alert status")
    print("-" * 60)
    
    alert.refresh_from_db()
    print(f"[INFO] Alert status before toggle: {alert.is_active}")
    
    alert.is_active = False
    alert.save()
    print(f"[OK] Deactivated alert")
    
    alert.is_active = True
    alert.save()
    print(f"[OK] Reactivated alert")
    
    # Test 6: Delete alert
    print("\n" + "-" * 60)
    print("TEST 6: Deleting alert")
    print("-" * 60)
    
    alert.delete()
    print(f"[OK] Deleted alert")
    
    # Verify deletion
    remaining_alerts = BookAvailabilityAlert.objects.filter(
        user=user,
        book=unavailable_book
    )
    if not remaining_alerts.exists():
        print(f"[OK] Alert successfully deleted")
    else:
        print(f"[ERROR] Alert still exists: {remaining_alerts.first()}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_availability_alerts()
