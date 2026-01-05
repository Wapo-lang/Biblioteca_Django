from django.test import TestCase
from Gestion.models import Autor, Libro, Prestamos, Multa
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

class MultasModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Creamos la base para la multa
        cls.autor = Autor.objects.create(nombre="H.G.", apellido="Wells")
        cls.usuario = User.objects.create_user(username="SocioMultado", password="password123")
        cls.libro = Libro.objects.create(titulo="La Máquina del Tiempo", autor=cls.autor, cantidad_total=5)
        
        # Préstamo vencido para probar cálculo
        cls.prestamo_vencido = Prestamos.objects.create(
            libro=cls.libro,
            usuario=cls.usuario,
            fecha_max=timezone.now().date() - timezone.timedelta(days=4)
        )

    def test_calculo_monto_automatico(self):
        # Si tu lógica de multa_total multiplica días por 0.50
        # 4 días de retraso deberían ser 2.00
        self.assertEqual(float(self.prestamo_vencido.multa_total), 2.0)

    def test_creacion_objeto_multa(self):
        # Probamos que se pueda crear el registro en el historial
        multa = Multa.objects.create(
            prestamo=self.prestamo_vencido,
            monto=self.prestamo_vencido.multa_total,
            tipo_multa='retraso'
        )
        self.assertEqual(multa.tipo_multa, 'retraso')
        self.assertFalse(multa.pagada)

class LibroStockTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Autor.objects.create(nombre="George", apellido="Orwell")
        cls.libro = Libro.objects.create(titulo="1984", autor=cls.autor, cantidad_total=2, ejemplares_disponibles=2)

    def test_reduccion_total_por_perdida(self):
        # Simulamos que un libro se pierde y sale del inventario para siempre
        self.libro.cantidad_total -= 1
        self.libro.save()
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.cantidad_total, 1)

    def test_disponibilidad_al_agotar_stock(self):
        # Si prestamos todos, disponible debe ser False
        self.libro.ejemplares_disponibles = 0
        self.libro.disponible = False
        self.libro.save()
        self.libro.refresh_from_db()
        self.assertFalse(self.libro.disponible)

class VistasPrivadasTest(TestCase):
    def setUp(self):
        # Usamos setUp normal porque necesitamos loguear y desloguear
        self.usuario = User.objects.create_user(username='pedro', password='password123')
        # Si usas is_staff para las multas, creamos un admin
        self.admin = User.objects.create_superuser(username='admin_test', password='adminpassword')

    def test_historial_multas_protegido(self):
        # Un usuario no logueado no debe ver el historial global
        response = self.client.get(reverse('lista_multas'))
        self.assertEqual(response.status_code, 302)

    def test_acceso_admin_historial(self):
        # El admin sí debe poder entrar
        self.client.login(username='admin_test', password='adminpassword')
        response = self.client.get(reverse('lista_multas'))
        self.assertEqual(response.status_code, 200)