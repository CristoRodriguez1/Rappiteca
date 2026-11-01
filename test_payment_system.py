"""
Test script for the payment system.

This script tests:
1. User can request payment
2. Admin can confirm payment
3. Admin can register in-person payment
4. Payment history is visible
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rappiteca.settings')
django.setup()

from django.test import RequestFactory
from accounts.models import User
from fines.models import Fine
from fines.views import request_payment, confirm_payment, confirm_in_person_payment
from fines.services import apply_overdue_fines

def test_payment_system():
    print("=" * 60)
    print("TESTING PAYMENT SYSTEM")
    print("=" * 60)
    
    # Find a user with fines
    user = User.objects.first()
    if not user:
        print("[ERROR] No users found. Please create a user first.")
        return
    
    print(f"\n[INFO] Using user: {user.email}")
    
    # Apply fines to ensure we have some
    apply_overdue_fines()
    
    # Find or create a fine for testing
    fine = Fine.objects.filter(user=user).first()
    if not fine:
        print("[WARN] No fines found for user. Creating a test scenario...")
        from loans.models import Loan
        from catalog.models import Book
        from decimal import Decimal
        
        # Create a test scenario
        book = Book.objects.first()
        if not book:
            print("[ERROR] No books found.")
            return
        
        loan = Loan.objects.create(
            user=user,
            book=book,
            status=Loan.STATUS_BORROWED
        )
        
        from datetime import timedelta
        from django.utils import timezone
        loan.pickup_date = timezone.now() - timedelta(days=30)
        loan.save()
        
        # Calculate and apply fine
        from fines.services import apply_fine
        fine = apply_fine(loan)
        print(f"[OK] Created test fine: {fine}")
    
    factory = RequestFactory()
    from django.contrib.messages.storage.fallback import FallbackStorage
    
    # Test 1: User requests payment
    print("\n" + "-" * 60)
    print("TEST 1: User requests payment")
    print("-" * 60)
    
    request = factory.post(f'/fines/request-payment/{fine.id}/')
    request.session = {
        'user_id': user.id,
        'user_role': user.role
    }
    request._messages = FallbackStorage(request)
    
    print(f"[INFO] Fine status before: {fine.status}")
    
    if fine.status == Fine.STATUS_PENDING:
        response = request_payment(request, fine.id)
        fine.refresh_from_db()
        print(f"[OK] Payment requested. Status: {fine.status}")
        print(f"[INFO] Payment requested at: {fine.payment_requested_at}")
    else:
        print(f"[INFO] Fine is not pending (status: {fine.status})")
    
    # Test 2: Admin confirms payment
    print("\n" + "-" * 60)
    print("TEST 2: Admin confirms payment")
    print("-" * 60)
    
    admin_user = User.objects.filter(role='adm').first()
    if not admin_user:
        print("[WARN] No admin user found. Skipping admin test.")
    else:
        print(f"[INFO] Using admin: {admin_user.email}")
        
        request = factory.post(f'/fines/confirm-payment/{fine.id}/')
        request.session = {
            'user_id': admin_user.id,
            'user_role': admin_user.role
        }
        request._messages = FallbackStorage(request)
        
        if fine.status == Fine.STATUS_PAYMENT_REQUESTED:
            response = confirm_payment(request, fine.id)
            fine.refresh_from_db()
            print(f"[OK] Payment confirmed. Status: {fine.status}")
            print(f"[INFO] Payment method: {fine.payment_method}")
            print(f"[INFO] Confirmed by: {fine.confirmed_by}")
            print(f"[INFO] Confirmed at: {fine.payment_confirmed_at}")
        else:
            print(f"[INFO] Fine is not awaiting confirmation (status: {fine.status})")
    
    # Test 3: Admin registers in-person payment
    print("\n" + "-" * 60)
    print("TEST 3: Admin registers in-person payment")
    print("-" * 60)
    
    # Reset fine to pending for this test
    fine.status = Fine.STATUS_PENDING
    fine.payment_requested_at = None
    fine.payment_confirmed_at = None
    fine.payment_method = None
    fine.confirmed_by = None
    fine.save()
    
    if admin_user:
        request = factory.post(f'/fines/confirm-in-person/{fine.id}/')
        request.session = {
            'user_id': admin_user.id,
            'user_role': admin_user.role
        }
        request._messages = FallbackStorage(request)
        
        response = confirm_in_person_payment(request, fine.id)
        fine.refresh_from_db()
        print(f"[OK] In-person payment registered. Status: {fine.status}")
        print(f"[INFO] Payment method: {fine.payment_method}")
        print(f"[INFO] Confirmed by: {fine.confirmed_by}")
        print(f"[INFO] Confirmed at: {fine.payment_confirmed_at}")
    
    # Test 4: Verify payment history
    print("\n" + "-" * 60)
    print("TEST 4: Payment history")
    print("-" * 60)
    
    user_fines = Fine.objects.filter(user=user)
    print(f"[INFO] User has {user_fines.count()} fine(s)")
    
    for f in user_fines:
        print(f"\n  Fine: {f.loan.book.title}")
        print(f"  Status: {f.get_status_display()}")
        print(f"  Amount: ${f.amount}")
        if f.payment_requested_at:
            print(f"  Requested: {f.payment_requested_at}")
        if f.payment_confirmed_at:
            print(f"  Confirmed: {f.payment_confirmed_at}")
            print(f"  Method: {f.payment_method}")
            print(f"  Confirmed by: {f.confirmed_by}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_payment_system()
