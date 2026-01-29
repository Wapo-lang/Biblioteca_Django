from rest_framework import serializers
from .models import Libro, Autor
import re

class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = '__all__'

    def validate(self, data):
        # Normalizamos a mayúsculas/minúsculas para evitar "Cervantes" vs "cervantes"
        nombre = data.get('nombre', self.instance.nombre if self.instance else '').strip()
        apellido = data.get('apellido', self.instance.apellido if self.instance else '').strip()

        # Buscamos si existe otro autor con ese nombre (excluyendo al actual)
        qs = Autor.objects.filter(nombre__iexact=nombre, apellido__iexact=apellido)
        
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                f"Ya existe un autor llamado {nombre} {apellido}."
            )

        data['nombre'] = nombre
        data['apellido'] = apellido
        return data

class LibroSerializer(serializers.ModelSerializer):
    # 'autor' recibe el ID (para crear/editar)
    # 'autor_detalle' devuelve el objeto completo (para mostrar en la web)
    autor_detalle = AutorSerializer(source='autor', read_only=True)
    
    class Meta:
        model = Libro
        fields = [
            'id', 'titulo', 'isbn', 'descripcion', 
            'autor', 'autor_detalle', 'cantidad_total', 
            'ejemplares_disponibles', 'disponible'
        ]
        # IMPORTANTE: Esto permite que Odoo envíe el ISBN en un PUT 
        # sin que Django diga "este ISBN ya existe"
        extra_kwargs = {
            'isbn': {'validators': []} 
        }

    def validate_isbn(self, value):
        if value:
            clean_value = re.sub(r'[-\s]', '', value)
            if len(clean_value) not in [10, 13]:
                raise serializers.ValidationError("El ISBN debe tener 10 o 13 dígitos.")
            if not clean_value.isdigit():
                raise serializers.ValidationError("El ISBN debe contener únicamente números.")
            
            # Validar unicidad manualmente (excepto para el mismo libro que estamos editando)
            instance = getattr(self, 'instance', None)
            if Libro.objects.filter(isbn=clean_value).exclude(pk=instance.pk if instance else None).exists():
                raise serializers.ValidationError("Este ISBN ya está registrado en otro libro.")
                
            return clean_value
        return value