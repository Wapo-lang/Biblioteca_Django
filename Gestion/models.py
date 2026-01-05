from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import datetime
from django.core.exceptions import ValidationError

# Create your models here.
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
    disponible = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Al crear el libro, igualamos disponibles al total
        if not self.pk:
            self.ejemplares_disponibles = self.cantidad_total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} ({self.ejemplares_disponibles}/{self.cantidad_total})"
    
from decimal import Decimal # Importante para dinero

class Prestamos(models.Model):
    # ... tus campos actuales (libro, usuario, fechas) ...
    libro = models.ForeignKey(Libro, related_name="prestamos", on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="prestamos", on_delete=models.PROTECT)
    fecha_prestamo = models.DateField(default=timezone.now)
    fecha_max = models.DateField(null=True, blank=True) 
    fecha_devolucion = models.DateField(null=True, blank=True)

    ESTADOS = [('p', 'Prestado'), ('m', 'Multa'), ('d', 'Devuelto')]
    TIPOS_MULTA = [
        ('retraso', 'Retraso'),
        ('perdida', 'Pérdida'),
        ('danio', 'Daño'),
        ('robo', 'Robo'),
        ('otros', 'Otros')
    ]

    estado = models.CharField(max_length=1, choices=ESTADOS, default='p')
    tipo_multa = models.CharField(max_length=10, choices=TIPOS_MULTA, default='retraso')
    multa_fija = models.DecimalField(max_digits=6, decimal_places=2, default=0.00) # Odoo: multa

    class Meta:
        permissions = (
            ("Ver_prestamos", "Puede ver préstamos"),
            ("Gestionar_prestamos", "Puede gestionar préstamos"),
        )

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
    @property
    def estado_real(self):
        if self.fecha_devolucion:
            return "Devuelto"
        if self.fecha_max and timezone.now().date() > self.fecha_max:
            return "En Mora / Multa"
        return "A tiempo"

    def save(self, *args, **kwargs):
        referencia = self.fecha_prestamo or timezone.now().date()
        
        if isinstance(referencia, str):
            referencia = datetime.datetime.strptime(referencia, '%Y-%m-%d').date()
            self.fecha_prestamo = referencia 
        
        # Autocalcular fecha máxima
        if not self.fecha_max:
            self.fecha_max = referencia + timedelta(days=2)

        if not self.pk:  # Si es un préstamo nuevo
            if self.libro.ejemplares_disponibles > 0:
                self.libro.ejemplares_disponibles -= 1
                
                if self.libro.ejemplares_disponibles == 0:
                    self.libro.disponible = False
                
                self.libro.save() # Guardamos los cambios en el libro
            else:
                raise ValidationError("Este libro no tiene ejemplares disponibles en stock.")

        if self.fecha_max and not self.fecha_devolucion:
            if timezone.now().date() > self.fecha_max:
                self.estado = 'm' 

        super().save(*args, **kwargs)

class Multa(models.Model):
    prestamo = models.ForeignKey(Prestamos, related_name="multas", on_delete=models.PROTECT)
    tipo_multa = models.CharField(max_length=50, choices=[('retraso', 'Retraso'), ('perdida', 'Pérdida del libro'), ('deterioro', 'Deterioro del libro')])
    monto = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    pagada = models.BooleanField(default=False)
    fecha = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Multa {self.tipo_multa} - {self.monto} - {self.prestamo}"
    
    def save(self, *args, **kwargs):
        if self.tipo_multa == 'retraso' and self.monto == 0:
            self.monto = self.prestamo.multa_retraso
        super().save(*args, **kwargs)