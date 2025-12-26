from django.test import TestCase
from Gestion.models import Autor, Libro, Prestamos
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

class LibroModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Autor.objects.create(nombre="Isaac", apellido="Asimov", bibliografia="Científico.")
        cls.libro = Libro.objects.create(titulo="Fundación", autor=cls.autor, cantidad_total=1)

    def test_str_devuelve_libro(self):
        self.assertEqual(str(self.libro), "Fundación (1/1)")

class PrestamosModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Autor.objects.create(nombre="Isaac", apellido="Asimov")
        cls.usuario = User.objects.create_user(username="Juan", password="password123")
        cls.libro = Libro.objects.create(titulo="I Robot", autor=cls.autor, disponible=True)
        
        cls.prestamo = Prestamos.objects.create(
            libro=cls.libro,
            usuario=cls.usuario,
            fecha_prestamo=timezone.now().date()
        )

    def test_libro_no_disponible(self):
        self.libro.refresh_from_db()
        self.assertFalse(self.libro.disponible)

class PrestamoUsuarioTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='test12345')

    def test_redirige_no_login(self):
        resp = self.client.get(reverse('crear_autor'))
        self.assertEqual(resp.status_code, 302)

    def test_acceso_con_login(self):
        self.client.login(username='user1', password='test12345')
        resp = self.client.get(reverse('crear_autor'))
        self.assertEqual(resp.status_code, 200)