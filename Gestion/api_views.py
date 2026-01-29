from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import Libro, Autor
from .serializers import LibroSerializer, AutorSerializer

class AutorViewSet(viewsets.ModelViewSet):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer
    permission_classes = [IsAuthenticated] # Requiere Token

class LibroViewSet(viewsets.ModelViewSet):
    queryset = Libro.objects.all()
    serializer_class = LibroSerializer
    permission_classes = [IsAuthenticated] 
    lookup_field = 'isbn'

    def get_queryset(self):
        queryset = Libro.objects.all()
        isbn = self.request.query_params.get('isbn')
        if isbn is not None:
            queryset = queryset.filter(isbn=isbn)
        return queryset