from django.test import TestCase
from Gestion.models import Autor, Libro, Prestamos
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class LibroModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        autor = Autor.objects.create(nombre="Isaac", apellido="Asimov", bibliografia="Científico y escritor de ciencia ficción.")
        Libro.objects.create(titulo="Fundación", autor=autor, disponible=True)

    def test_str_devuelve_libro(self):
        libro = Libro.objects.get(id=1)
        self.assertEqual(str(libro), "Fundación - Isaac Asimov")

class PrestamosModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        autor = Autor.objects.create(nombre="Isaac", apellido="Asimov", bibliografia="Científico y escritor de ciencia ficción.")
        usuario = User.objects.create(username="Juan", password="#123Uyqwe")
        libro = Libro.objects.create(titulo="I Robot", autor_id=1, disponible=False)
        cls.prestamo = Prestamos.objects.create(
            libro=libro,
            usuario=usuario,
            fecha_max='2025-12-25'
        )

    def test_libro_no_disponible(self):
        self.prestamo.refresh_from_db()
        self.assertFalse(self.prestamo.libro.disponible)
        self.assertEqual(self.prestamo.dias_retraso, None)

class PrestamoUsuarioTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='test12345')
        self.user2 = User.objects.create_user(username='user2', password='test12345')

    def test_redirige_no_login(self):
        resp = self.client.get(reverse('crear_autor'))
        self.assertEqual(resp.status_code, 302)

    def test_carga_login(self):
        resp = self.client.login(username='user1', password='test12345')
        #self.assertEqual(resp.status_code, 200)
        resp1 = self.client.get(reverse('crear_autor'))
        self.assertEqual(resp1.status_code, 200)