from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Libro, Autor
from .serializers import LibroSerializer, AutorSerializer
import requests

class AutorViewSet(viewsets.ModelViewSet):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer
    permission_classes = [IsAuthenticated]

class LibroViewSet(viewsets.ModelViewSet):
    queryset = Libro.objects.all()
    serializer_class = LibroSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'isbn'

    def retrieve(self, request, *args, **kwargs):
        isbn = kwargs.get('isbn')
        instance = Libro.objects.filter(isbn=isbn).first()
        
        if instance:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        ol_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        try:
            res = requests.get(ol_url, timeout=10)
            data = res.json()
            key = f"ISBN:{isbn}"

            if key in data:
                info = data[key]
                author_name = "Autor Desconocido"
                bio_texto = ""
                
                if info.get('authors'):
                    auth_data = info['authors'][0]
                    author_name = auth_data.get('name')
                    ol_auth_id = auth_data.get('url', '').split('/')[-2] if 'url' in auth_data else None
                    if ol_auth_id:
                        res_bio = requests.get(f"https://openlibrary.org/authors/{ol_auth_id}.json", timeout=5)
                        if res_bio.status_code == 200:
                            raw_bio = res_bio.json().get('bio', '')
                            bio_texto = raw_bio.get('value', raw_bio) if isinstance(raw_bio, dict) else raw_bio

                parts = author_name.split(' ', 1)
                nom = parts[0]
                ape = parts[1] if len(parts) > 1 else '.'
                
                autor_obj, created = Autor.objects.get_or_create(
                    nombre=nom, 
                    apellido=ape,
                    defaults={'bibliografia': bio_texto}
                )

                nuevo_libro = Libro.objects.create(
                    titulo=info.get('title', 'Sin Título'),
                    isbn=isbn,
                    descripcion=str(info.get('description', info.get('notes', ''))),
                    autor=autor_obj,
                    cantidad_total=1,
                    ejemplares_disponibles=1
                )
                
                serializer = self.get_serializer(nuevo_libro)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Error en el servidor: {str(e)}"}, status=500)

        return Response({"error": "No encontrado"}, status=404)