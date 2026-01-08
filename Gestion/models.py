from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError

class Autor(models.Model):
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    bibliografia = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Libro(models.Model):
    titulo = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13, unique=True, null=True, blank=True)
    descripcion = models.TextField(blank=True, null=True)
    autor = models.ForeignKey(Autor, related_name="libros", on_delete=models.PROTECT)
    cantidad_total = models.PositiveIntegerField(default=1)
    ejemplares_disponibles = models.IntegerField(default=1)
    portada = models.ImageField(upload_to='portadas/', blank=True, null=True)
    disponible = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.ejemplares_disponibles = self.cantidad_total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} ({self.ejemplares_disponibles}/{self.cantidad_total})"

class Prestamos(models.Model):
    libro = models.ForeignKey(Libro, related_name="prestamos", on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="prestamos", on_delete=models.PROTECT)
    fecha_prestamo = models.DateField(default=timezone.now)
    fecha_max = models.DateField(null=True, blank=True)
    fecha_devolucion = models.DateField(null=True, blank=True)

    ESTADOS = [('p', 'Prestado'), ('m', 'Multa'), ('d', 'Devuelto')]

    estado = models.CharField(max_length=1, choices=ESTADOS, default='p')
    multa_fija = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    @property
    def dias_retraso(self):
        hoy = timezone.now().date()
        fecha_ref = self.fecha_devolucion or hoy
        if self.fecha_max and fecha_ref > self.fecha_max:
            return (fecha_ref - self.fecha_max).days
        return 0

    @property
    def multa_total(self):
        tarifa_retraso = Decimal('0.50')
        total_retraso = Decimal(self.dias_retraso) * tarifa_retraso
        return total_retraso + Decimal(self.multa_fija)

    def save(self, *args, **kwargs):
            referencia = self.fecha_prestamo or timezone.now().date()
            if isinstance(referencia, str):
                referencia = datetime.strptime(referencia, '%Y-%m-%d').date()
                self.fecha_prestamo = referencia

            if not self.fecha_max:
                # Puedes dejar esto o manejarlo en la vista, pero aquí está bien
                self.fecha_max = referencia + timedelta(days=14) 

            # --- ELIMINAMOS EL BLOQUE QUE HACIA: if not self.pk: self.libro.ejemplares_disponibles -= 1 ---
            # Ahora el modelo solo se encarga de guardar datos, no de mover stock.

            if self.fecha_max and not self.fecha_devolucion:
                if timezone.now().date() > self.fecha_max:
                    self.estado = 'm'

            super().save(*args, **kwargs)

class Multa(models.Model):
    prestamo = models.ForeignKey(Prestamos, related_name="multas", on_delete=models.PROTECT)
    tipo_multa = models.CharField(max_length=50, choices=[('retraso', 'Retraso'), ('perdida', 'Pérdida del libro'), ('deterioro', 'Deterioro del libro')])
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pagada = models.BooleanField(default=False)
    fecha = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Multa {self.tipo_multa} - {self.monto} - {self.prestamo}"

    def save(self, *args, **kwargs):
        if self.tipo_multa == 'retraso' and (self.monto == 0 or self.monto is None):
            self.monto = self.prestamo.multa_total
        super().save(*args, **kwargs)