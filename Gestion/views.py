from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

from .models import Autor, Libro, Prestamos, Multa

def index(request):
    title = settings.TITLE
    return render(request, 'gestion/templates/home.html', {'titulo': title})

def lista_libros(request):
    libros = Libro.objects.all()
    return render(request, 'gestion/templates/libros.html', {'libros': libros})

def crear_libro(request):
    autores = Autor.objects.all()
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        autor_id = request.POST.get('autor')
        if titulo and autor_id:
            autor = get_object_or_404(Autor, id=autor_id)
            Libro.objects.create(titulo=titulo, autor=autor)
            return redirect('lista_libros')
    return render(request, 'gestion/templates/templates_crear/crear_libro.html', {'autores': autores})

def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'gestion/templates/autores.html', {'autores': autores})

def crear_autor(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        Autor.objects.create(nombre=nombre, apellido=apellido, bibliografia=bibliografia)
        return redirect('lista_autores')
    return render(request, 'gestion/templates/templates_crear/crear_autor.html')

def lista_prestamos(request):
    prestamos = Prestamos.objects.all()
    return render(request, 'gestion/templates/prestamos.html', {'prestamos': prestamos})

def crear_prestamo(request):
    pass

def detalle_prestamo(request):
    pass

def lista_multa(request):
    multas = Multa.objects.all()
    return render(request, 'gestion/templates/multas.html', {'multas': multas})

def crear_multa(request):
    pass
    

# Create your views here.
