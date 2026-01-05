from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from Gestion.models import Autor, Libro

class ListaAutorViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='user_autor', password='password123')
        # Creamos 5 autores de prueba
        for i in range(5):
            Autor.objects.create(nombre=f"Nombre {i}", apellido=f"Apellido {i}")

    def test_url_autores_existencias(self):
        self.client.login(username='user_autor', password='password123')
        resp = self.client.get(reverse('lista_autores')) # Asegúrate que este sea el nombre en tu urls.py
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'gestion/templates/autores.html')
        self.assertEqual(len(resp.context['autores']), 5)


