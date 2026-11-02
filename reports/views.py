"""
FR-31 / FR-32: Reports tab of the admin panel.
"""

import csv
import time

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from fines.services import apply_overdue_fines

from . import services


def _is_admin(request):
    return request.session.get('user_role') == 'adm'


def _deny(request):
    messages.error(request, 'You do not have permission to view this page.')
    return redirect('home')


def _period_context(period):
    return {
        'period': period,
        'period_label': services.PERIODS[period][0],
        'periods': [(key, label) for key, (label, _) in services.PERIODS.items()],
    }


def reports_index(request):
    if not _is_admin(request):
        return _deny(request)
    return redirect('reports_most_borrowed')


def most_borrowed_report(request):
    """FR-31: most borrowed books, generated on request."""
    if not _is_admin(request):
        return _deny(request)

    period = services.clean_period(request.GET.get('period'))
    started = time.perf_counter()
    report = services.most_borrowed_books(period=period)
    elapsed_ms = (time.perf_counter() - started) * 1000

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="most_borrowed_books_{period}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Rank', 'Title', 'Author', 'Category', 'Times borrowed', 'Different users', 'Currently out', 'Share %'])
        for row in report['rows']:
            book = row['book']
            writer.writerow([row['rank'], book.title, book.author, book.category,
                             row['times_borrowed'], row['borrowers'], row['currently_out'], row['share']])
        return response

    context = {'report': report, 'elapsed_ms': elapsed_ms, 'active_report': 'most_borrowed'}
    context.update(_period_context(period))
    return render(request, 'reports_most_borrowed.html', context)


def overdue_fines_report(request):
    """FR-32: overdue rate of loans and state of the fines, generated on request."""
    if not _is_admin(request):
        return _deny(request)

    period = services.clean_period(request.GET.get('period'))
    started = time.perf_counter()
    # Same as the Fines tab: bring fines of books that are still out up to date
    # first, so the amounts are correct even if the daily command did not run.
    apply_overdue_fines()
    report = services.overdue_fines_report(period=period)
    elapsed_ms = (time.perf_counter() - started) * 1000

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="overdue_fines_{period}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Loans picked up', report['total_loans']])
        writer.writerow(['Overdue loans', report['overdue_loans']])
        writer.writerow(['Overdue rate %', report['overdue_rate']])
        writer.writerow(['Total fined', report['fined_total']])
        writer.writerow(['Pending', report['pending_total']])
        writer.writerow(['Awaiting confirmation', report['requested_total']])
        writer.writerow(['Paid', report['paid_total']])
        writer.writerow(['Collection rate %', report['collection_rate']])
        writer.writerow([])
        writer.writerow(['Category', 'Loans', 'Overdue', 'Overdue rate %'])
        for row in report['categories']:
            writer.writerow([row['name'], row['loans'], row['overdue'], row['rate']])
        return response

    context = {'report': report, 'elapsed_ms': elapsed_ms, 'active_report': 'overdue_fines'}
    context.update(_period_context(period))
    return render(request, 'reports_overdue_fines.html', context)
