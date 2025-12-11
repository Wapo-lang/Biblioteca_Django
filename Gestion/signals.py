from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Permission

@receiver(post_save, sender=User)
def asignar_permisos_prestamos(sender, instance, created, **kwargs):
    if created:
        permisos = Permission.objects.filter(codename__in=[
            'Ver_prestamos',
            'Gestionar_prestamos',
        ])
        instance.user_permissions.add(*permisos)
