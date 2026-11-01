import time

from django.test import Client, TestCase

from .models import Book


class FR27FilterSearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dune = Book.objects.create(
            title='Dune', author='Frank Herbert', category='Science Fiction',
            total_copies=3, available_copies=3,
        )
        self.foundation = Book.objects.create(
            title='Foundation', author='Isaac Asimov', category='Science Fiction',
            total_copies=2, available_copies=0,
        )
        self.cien_anos = Book.objects.create(
            title='Cien años de soledad', author='Gabriel García Márquez', category='Novel',
            total_copies=1, available_copies=1,
        )

    def _titles(self, response):
        return [item['book'].title for item in response.context['resultados']]

    def test_fr27_filter_by_category(self):
        response = self.client.get('/', {'category': 'Science Fiction'})
        self.assertCountEqual(self._titles(response), ['Dune', 'Foundation'])

    def test_fr27_category_filter_is_case_insensitive(self):
        response = self.client.get('/', {'category': 'novel'})
        self.assertEqual(self._titles(response), ['Cien años de soledad'])

    def test_fr27_filter_available_only(self):
        response = self.client.get('/', {'availability': 'available'})
        self.assertCountEqual(self._titles(response), ['Dune', 'Cien años de soledad'])

    def test_fr27_filter_unavailable_only(self):
        response = self.client.get('/', {'availability': 'unavailable'})
        self.assertEqual(self._titles(response), ['Foundation'])

    def test_fr27_filters_combine_with_search_term(self):
        response = self.client.get('/', {
            'q': 'science', 'availability': 'available',
        })
        self.assertEqual(self._titles(response), ['Dune'])

    def test_fr27_sort_by_title_ascending_and_descending(self):
        response = self.client.get('/', {'sort': 'title'})
        self.assertEqual(self._titles(response), ['Cien años de soledad', 'Dune', 'Foundation'])

        response = self.client.get('/', {'sort': '-title'})
        self.assertEqual(self._titles(response), ['Foundation', 'Dune', 'Cien años de soledad'])

    def test_fr27_sort_by_author(self):
        response = self.client.get('/', {'sort': 'author'})
        self.assertEqual(self._titles(response), ['Dune', 'Cien años de soledad', 'Foundation'])

    def test_fr27_sort_by_most_available(self):
        response = self.client.get('/', {'sort': 'available'})
        self.assertEqual(self._titles(response), ['Dune', 'Cien años de soledad', 'Foundation'])

    def test_fr27_invalid_params_are_ignored(self):
        response = self.client.get('/', {
            'q': 'dune', 'availability': 'bogus', 'sort': 'DROP TABLE',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._titles(response), ['Dune'])
        self.assertEqual(response.context['filtros']['availability'], '')
        self.assertEqual(response.context['filtros']['sort'], '')

    def test_fr27_no_results_message(self):
        response = self.client.get('/', {'category': 'Poetry'})
        self.assertTrue(response.context['busqueda_vacia'])
        self.assertContains(response, 'No results with the selected filters.')

    def test_fr27_category_options_listed(self):
        response = self.client.get('/')
        self.assertEqual(response.context['categorias'], ['Novel', 'Science Fiction'])
        self.assertContains(response, '<option value="Novel"')

    def test_fr27_selected_filters_stay_selected(self):
        response = self.client.get('/', {'availability': 'available', 'sort': 'author'})
        self.assertContains(response, '<option value="available" selected>')
        self.assertContains(response, '<option value="author" selected>')
        self.assertContains(response, 'Clear filters')

    def test_fr27_without_filters_nothing_is_listed(self):
        response = self.client.get('/')
        self.assertFalse(response.context['busqueda_activa'])
        self.assertNotContains(response, 'Clear filters')

    def test_fr27_responds_within_3_seconds(self):
        start = time.perf_counter()
        response = self.client.get('/', {
            'q': 'a', 'category': 'Science Fiction', 'availability': 'available', 'sort': 'title',
        })
        self.assertEqual(response.status_code, 200)
        self.assertLess(time.perf_counter() - start, 3)
