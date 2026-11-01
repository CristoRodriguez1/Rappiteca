"""
FR-23/FR-24/FR-25: admin and user pages that list fines and their payment status.
"""

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone

from .models import Fine
from .services import apply_overdue_fines


def _is_admin(request):
    return request.session.get('user_role') == 'adm'


def _get_current_user(request):
    from accounts.models import User
    user_id = request.session.get('user_id')
    if user_id:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    return None


def admin_fine_list(request):
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    # Bring fines of books that are still out up to date before showing them,
    # so the page is correct even if the daily command has not run yet.
    apply_overdue_fines()

    # FR-25: Optimize query with select_related to load within 3 seconds
    fines = Fine.objects.select_related(
        'user',
        'loan',
        'loan__book',
        'confirmed_by'
    ).order_by('status', '-amount')
    
    pending_total = fines.filter(status=Fine.STATUS_PENDING).aggregate(total=Sum('amount'))['total']
    payment_requested_total = fines.filter(status=Fine.STATUS_PAYMENT_REQUESTED).aggregate(total=Sum('amount'))['total']

    return render(request, 'fines_admin_list.html', {
        'fines': fines,
        'pending_total': pending_total or 0,
        'payment_requested_total': payment_requested_total or 0,
    })


def user_fine_list(request):
    """FR-25: User view to see their own fines and payment status."""
    current_user = _get_current_user(request)
    if not current_user:
        messages.error(request, 'You must be logged in to view your fines.')
        return redirect('login')

    # Bring fines of books that are still out up to date before showing them
    apply_overdue_fines()

    # FR-25: Optimize query with select_related to load within 3 seconds
    fines = Fine.objects.filter(
        user=current_user
    ).select_related(
        'loan',
        'loan__book',
        'confirmed_by'
    ).order_by('status', '-applied_at')
    
    pending_total = fines.filter(status=Fine.STATUS_PENDING).aggregate(total=Sum('amount'))['total']
    payment_requested_total = fines.filter(status=Fine.STATUS_PAYMENT_REQUESTED).aggregate(total=Sum('amount'))['total']
    paid_total = fines.filter(status=Fine.STATUS_PAID).aggregate(total=Sum('amount'))['total']

    return render(request, 'fines_user_list.html', {
        'fines': fines,
        'pending_total': pending_total or 0,
        'payment_requested_total': payment_requested_total or 0,
        'paid_total': paid_total or 0,
        'current_user': current_user,
    })


def request_payment(request, fine_id):
    """User requests to mark a fine as paid (pending admin confirmation)."""
    current_user = _get_current_user(request)
    if not current_user:
        messages.error(request, 'You must be logged in to request payment.')
        return redirect('login')

    fine = get_object_or_404(Fine, id=fine_id, user=current_user)
    
    if fine.status != Fine.STATUS_PENDING:
        messages.warning(request, 'This fine is not in a state that allows payment request.')
        return redirect('fines_user_list')

    fine.status = Fine.STATUS_PAYMENT_REQUESTED
    fine.payment_requested_at = timezone.now()
    fine.save()
    
    messages.success(request, f'Payment requested for "${fine.amount}". Waiting for admin confirmation.')
    return redirect('fines_user_list')


def confirm_payment(request, fine_id):
    """Admin confirms a user's payment request."""
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to confirm payments.')
        return redirect('home')

    admin_user = _get_current_user(request)
    fine = get_object_or_404(Fine, id=fine_id)
    
    if fine.status != Fine.STATUS_PAYMENT_REQUESTED:
        messages.warning(request, 'This fine is not awaiting payment confirmation.')
        return redirect('fines_admin_list')

    fine.status = Fine.STATUS_PAID
    fine.payment_confirmed_at = timezone.now()
    fine.payment_method = 'online'
    fine.confirmed_by = admin_user
    fine.save()
    
    messages.success(request, f'Payment confirmed for user {fine.user.email}.')
    return redirect('fines_admin_list')


def confirm_in_person_payment(request, fine_id):
    """Admin registers an in-person payment directly."""
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to register payments.')
        return redirect('home')

    admin_user = _get_current_user(request)
    fine = get_object_or_404(Fine, id=fine_id)
    
    if fine.status == Fine.STATUS_PAID:
        messages.warning(request, 'This fine has already been paid.')
        return redirect('fines_admin_list')

    fine.status = Fine.STATUS_PAID
    fine.payment_confirmed_at = timezone.now()
    fine.payment_method = 'in_person'
    fine.confirmed_by = admin_user
    fine.save()
    
    messages.success(request, f'In-person payment registered for user {fine.user.email}.')
    return redirect('fines_admin_list')
