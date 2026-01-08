from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from Gestion.models import Libro, Autor, Prestamos, Multa

class Command(BaseCommand):
    help = 'Configura los 4 grupos de usuarios con sus permisos exactos'

    def handle(self, *args, **kwargs):
        # 1. Definir Grupos
        grupos = {
            'Administrador': [], # Heredará todo
            'Bibliotecario': [],
            'Bodega': [],
            'Cliente': []
        }

        # Crear los grupos en la BD
        for nombre in grupos:
            Group.objects.get_or_create(name=nombre)
            self.stdout.write(f'Grupo "{nombre}" verificado.')

        # 2. Obtener ContentTypes (Identificadores de tus tablas)
        ct_libro = ContentType.objects.get_for_model(Libro)
        ct_autor = ContentType.objects.get_for_model(Autor)
        ct_prestamo = ContentType.objects.get_for_model(Prestamos) # Ojo con la 's' final
        ct_multa = ContentType.objects.get_for_model(Multa)

        # 3. Asignar Permisos a BODEGA
        # Solo tocan Libros y Autores (Crear, Editar, Borrar, Ver)
        perms_bodega = Permission.objects.filter(
            content_type__in=[ct_libro, ct_autor],
            codename__in=[
                'add_libro', 'change_libro', 'delete_libro', 'view_libro',
                'add_autor', 'change_autor', 'delete_autor', 'view_autor'
            ]
        )
        Group.objects.get(name='Bodega').permissions.set(perms_bodega)

        # 4. Asignar Permisos a BIBLIOTECARIO
        perms_biblio = Permission.objects.filter(
            content_type__in=[ct_libro, ct_prestamo, ct_multa, ct_autor],
            codename__in=[
                'view_libro', 'view_autor',
                'add_prestamos', 'change_prestamos', 'view_prestamos', 'Gestionar_prestamos',
                'add_multa', 'change_multa', 'view_multa'
            ]
        )
        Group.objects.get(name='Bibliotecario').permissions.set(perms_biblio)

        # 5. Asignar Permisos a CLIENTE
        # Solo ver libros y "pedir" préstamos (add_prestamos)
        perms_cliente = Permission.objects.filter(
            content_type__in=[ct_libro, ct_prestamo],
            codename__in=['view_libro', 'add_prestamos'] 
        )
        Group.objects.get(name='Cliente').permissions.set(perms_cliente)

        # 6. ADMINISTRADOR
        # Le damos permisos sobre todos los modelos de la app 'gestion'
        perms_admin = Permission.objects.filter(content_type__in=[ct_libro, ct_autor, ct_prestamo, ct_multa])
        Group.objects.get(name='Administrador').permissions.set(perms_admin)

        self.stdout.write(self.style.SUCCESS('¡Roles y Permisos configurados correctamente!'))