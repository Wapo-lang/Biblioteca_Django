from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.
class Autor(models.Model):
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    bibliografia = models.CharField(max_length=200, blank=True, null=True)
    

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Libro(models.Model):
    titulo = models.CharField(max_length=50)
    autor = models.ForeignKey(Autor, related_name="libros", on_delete=models.PROTECT)
    disponible = models.BooleanField(default=True)
    fecha_publicacion = models.DateField(blank=True, null=True)
    image = models.ImageField(upload_to='libros/', blank=True, null=True)


    def __str__(self):
        return f"{self.titulo} - {self.autor}"
    
class Prestamos(models.Model):
    libro = models.ForeignKey(Libro, related_name="prestamos", on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="prestamos", on_delete=models.PROTECT)
    fecha_prestamo = models.DateField(default=timezone.now)
    fecha_max = models.DateField()
    fecha_devolucion = models.DateField(null=True, blank=True) #permite registros nulos y en blanco

    class Meta:
        permissions = (
            ("Ver_prestamos", "Puede ves prstamos"),
            ("Gestionar_prestamos", "Puede gestionar préstamos"),
            
        )

    def __str__(self):
        return f"Préstamo de {self.libro} a {self.usuario}"

    @property
    def dias_retraso(self):
        hoy = timezone.now().date()
        fecha_ref = self.fecha_devolucion or hoy
        if fecha_ref > self.fecha_max:
            return (fecha_ref - self.fecha_devolucion).days
        
    @property
    def multa_retraso(self):
        tarifa_diaria = 0.50  # Tarifa fija por día de retraso
        return self.dias_retraso * tarifa_diaria 
    
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