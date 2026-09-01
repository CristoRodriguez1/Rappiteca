from django.urls import path

from . import fr16_borrower

urlpatterns = [
    path('admin-book-borrowers/', fr16_borrower.admin_book_borrower_list, name='fr16_book_borrower_list'),
    path(
        'admin-book-borrowers/<int:book_id>/',
        fr16_borrower.admin_book_borrower_detail,
        name='fr16_book_borrower_detail',
    ),
]
