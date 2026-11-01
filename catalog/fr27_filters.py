"""
FR-27 Filter search.

IF a user performs a catalog search THEN THE Rappiteca system SHOULD allow the
user to filter and sort the results within 3 seconds.
"""

from .models import Book

AVAILABILITY_ALL = ''
AVAILABILITY_AVAILABLE = 'available'
AVAILABILITY_UNAVAILABLE = 'unavailable'

AVAILABILITY_OPTIONS = [
    (AVAILABILITY_ALL, 'All'),
    (AVAILABILITY_AVAILABLE, 'Available only'),
    (AVAILABILITY_UNAVAILABLE, 'Unavailable only'),
]

# Value sent in `?sort=` -> (label shown in the select, ORM ordering).
# Unknown values are ignored so a hand-edited URL never breaks the page.
SORT_OPTIONS = {
    'title': ('Title (A–Z)', ['title']),
    '-title': ('Title (Z–A)', ['-title']),
    'author': ('Author (A–Z)', ['author', 'title']),
    'available': ('Most copies available', ['-available_copies', 'title']),
}


def category_choices():
    """Distinct, non-empty categories currently in the catalog, sorted A–Z."""
    return list(
        Book.objects.exclude(category='')
        .order_by('category')
        .values_list('category', flat=True)
        .distinct()
    )


def read_filters(request):
    """Reads the filter/sort params from the query string, discarding invalid ones."""
    category = request.GET.get('category', '').strip()
    availability = request.GET.get('availability', AVAILABILITY_ALL)
    sort = request.GET.get('sort', '')

    if availability not in dict(AVAILABILITY_OPTIONS):
        availability = AVAILABILITY_ALL
    if sort not in SORT_OPTIONS:
        sort = ''

    return {'category': category, 'availability': availability, 'sort': sort}


def apply_filters(books, filters):
    """Narrows and orders an already-searched Book queryset."""
    if filters['category']:
        books = books.filter(category__iexact=filters['category'])

    if filters['availability'] == AVAILABILITY_AVAILABLE:
        books = books.filter(available_copies__gt=0)
    elif filters['availability'] == AVAILABILITY_UNAVAILABLE:
        books = books.filter(available_copies=0)

    if filters['sort']:
        books = books.order_by(*SORT_OPTIONS[filters['sort']][1])

    return books


def has_active_filters(filters):
    return any(filters.values())
