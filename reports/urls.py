from django.urls import path

from . import views

urlpatterns = [
    path('admin-reports/', views.reports_index, name='reports_index'),
    # FR-31 Most borrowed books
    path('admin-reports/most-borrowed/', views.most_borrowed_report, name='reports_most_borrowed'),
    # FR-32 Overdue fines report
    path('admin-reports/overdue-fines/', views.overdue_fines_report, name='reports_overdue_fines'),
]
