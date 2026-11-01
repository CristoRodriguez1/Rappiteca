"""
Test script for FR-25: Fines payment status display.

This script tests:
1. User can view their own fines
2. Admin can view all fines
3. Payment status is displayed correctly
4. Page loads within 3 seconds
"""

import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rappiteca.settings')
django.setup()

from django.test import RequestFactory
from accounts.models import User
from fines.models import Fine
from fines.views import user_fine_list, admin_fine_list
from fines.services import apply_overdue_fines

def test_fines_performance():
    print("=" * 60)
    print("TESTING FR-25: Fines Payment Status Display")
    print("=" * 60)
    
    # Find a user
    user = User.objects.first()
    if not user:
        print("[ERROR] No users found. Please create a user first.")
        return
    
    print(f"\n[INFO] Using user: {user.email}")
    
    # Test 1: Apply overdue fines
    print("\n" + "-" * 60)
    print("TEST 1: Applying overdue fines")
    print("-" * 60)
    
    start_time = time.time()
    apply_overdue_fines()
    end_time = time.time()
    
    apply_time = end_time - start_time
    print(f"[OK] Fines applied in {apply_time:.2f} seconds")
    
    # Test 2: Check if user has fines
    print("\n" + "-" * 60)
    print("TEST 2: Checking user fines")
    print("-" * 60)
    
    user_fines = Fine.objects.filter(user=user).select_related('loan', 'loan__book')
    
    if user_fines.exists():
        print(f"[OK] User has {user_fines.count()} fine(s)")
        for fine in user_fines:
            print(f"  - {fine.loan.book.title}: ${fine.amount} [{fine.status}]")
    else:
        print("[INFO] User has no fines")
    
    # Test 3: Test user fine list view performance
    print("\n" + "-" * 60)
    print("TEST 3: User fine list view performance")
    print("-" * 60)
    
    factory = RequestFactory()
    request = factory.get('/fines/my-fines/')
    request.session = {
        'user_id': user.id,
        'user_role': user.role
    }
    
    start_time = time.time()
    response = user_fine_list(request)
    end_time = time.time()
    
    view_time = end_time - start_time
    print(f"[OK] User fine list rendered in {view_time:.2f} seconds")
    
    if view_time <= 3:
        print(f"[SUCCESS] View rendered within 3 seconds requirement")
    else:
        print(f"[WARN] View took longer than 3 seconds")
    
    # Test 4: Test admin fine list view performance
    print("\n" + "-" * 60)
    print("TEST 4: Admin fine list view performance")
    print("-" * 60)
    
    admin_user = User.objects.filter(role='adm').first()
    if admin_user:
        print(f"[INFO] Using admin: {admin_user.email}")
        
        request = factory.get('/fines/admin-fines/')
        request.session = {
            'user_id': admin_user.id,
            'user_role': admin_user.role
        }
        
        start_time = time.time()
        response = admin_fine_list(request)
        end_time = time.time()
        
        view_time = end_time - start_time
        print(f"[OK] Admin fine list rendered in {view_time:.2f} seconds")
        
        if view_time <= 3:
            print(f"[SUCCESS] View rendered within 3 seconds requirement")
        else:
            print(f"[WARN] View took longer than 3 seconds")
    else:
        print("[INFO] No admin user found")
    
    # Test 5: Verify payment status display
    print("\n" + "-" * 60)
    print("TEST 5: Payment status display")
    print("-" * 60)
    
    all_fines = Fine.objects.all()
    pending_count = all_fines.filter(status=Fine.STATUS_PENDING).count()
    paid_count = all_fines.filter(status=Fine.STATUS_PAID).count()
    
    print(f"[INFO] Total fines: {all_fines.count()}")
    print(f"[INFO] Pending fines: {pending_count}")
    print(f"[INFO] Paid fines: {paid_count}")
    
    if all_fines.exists():
        for fine in all_fines[:3]:  # Show first 3
            status_display = fine.get_status_display()
            print(f"  - {fine.loan.book.title}: {status_display}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    test_fines_performance()
