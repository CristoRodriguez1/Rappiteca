from django import forms

from .models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'isbn',
            'category',
            'location',
            'description',
            'image',
            'total_copies',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Cien años de soledad'}),
            'author': forms.TextInput(attrs={'placeholder': 'Gabriel García Márquez'}),
            'isbn': forms.TextInput(attrs={'placeholder': '978-3-16-148410-0'}),
            'category': forms.TextInput(attrs={'placeholder': 'Novela'}),
            'location': forms.TextInput(attrs={'placeholder': 'Estante B3 — Sala 2'}),
            'description': forms.Textarea(attrs={
                'placeholder': 'Breve reseña del libro…',
                'rows': 3,
            }),
            'total_copies': forms.NumberInput(attrs={'min': 1}),
        }
        labels = {
            'title': 'Título',
            'author': 'Autor',
            'isbn': 'ISBN',
            'category': 'Categoría',
            'location': 'Ubicación',
            'description': 'Descripción',
            'image': 'Portada',
            'total_copies': 'Copias totales',
        }

    def clean_total_copies(self):
        total_copies = self.cleaned_data['total_copies']
        if total_copies < 1:
            raise forms.ValidationError('El libro debe tener al menos una copia.')
        return total_copies

    def clean_isbn(self):
        # Un ISBN vacío se guarda como NULL, no como '' — así `unique=True`
        # no choca cuando se agregan varios libros sin ISBN.
        isbn = self.cleaned_data.get('isbn')
        return isbn or None

    def save(self, commit=True):
        book = super().save(commit=False)
        # Un libro recién agregado no tiene copias prestadas ni reservadas.
        book.available_copies = book.total_copies
        if commit:
            book.save()
        return book
