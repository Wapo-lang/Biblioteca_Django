from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from Gestion.models import Autor, Libro

class ListaLibroViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='password123')
        
        autor = Autor.objects.create(nombre="autor", apellido="libro", bibliografia="biografia del autor")
        for i in range(3):
            Libro.objects.create(titulo=f"Libro {i}", autor=autor, disponible=True)

    def test_url_existencias(self):
        self.client.login(username='testuser', password='password123')
        resp = self.client.get(reverse('lista_libros'))    
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'gestion/templates/libros.html')
        self.assertEqual(len(resp.context['libros']), 3)