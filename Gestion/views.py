from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
import requests
from django.contrib import messages

from .models import Autor, Libro, Prestamos, Multa

def index(request):
    title = settings.TITLE
    return render(request, 'gestion/templates/home.html', {'titulo': title})

def lista_libros(request):
    libros = Libro.objects.all()
    return render(request, 'gestion/templates/libros.html', {'libros': libros})

def devolver_libro(request, prestamo_id):
    prestamo = get_object_or_404(Prestamos, id=prestamo_id)
    
    if prestamo.fecha_devolucion is None:
        libro = prestamo.libro
        # 1. Devolver stock (Igual que Odoo)
        libro.disponible = True
        libro.save()
        
        # 2. Registrar fecha
        prestamo.fecha_devolucion = timezone.now().date()
        
        # 3. LÓGICA DE MULTA: Si hay retraso, el estado cambia a 'm' (multa)
        # Esto usará la @property multa_retraso que definimos en el modelo
        if prestamo.dias_retraso > 0:
            prestamo.estado = 'm'
            messages.warning(request, f"Devolución con retraso. Multa generada: ${prestamo.multa_retraso}")
        else:
            prestamo.estado = 'd'
            messages.success(request, f"Libro '{libro.titulo}' devuelto con éxito.")
            
        prestamo.save()
    
    return redirect('lista_prestamos')

def crear_libro(request):
    autores = Autor.objects.all()
    datos_api = {}

    if request.method == 'POST':
        # --- ACCIÓN: BUSCAR EN OPEN LIBRARY ---
        if 'buscar_api' in request.POST:
            isbn = request.POST.get('isbn')
            url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
            
            try:
                response = requests.get(url)
                data = response.json()
                key = f"ISBN:{isbn}"

                if key in data:
                    libro_info = data[key]
                    autores_api = libro_info.get('authors', [])
                    
                    autor_id_final = None
                    
                    if autores_api:
                        nombre_completo = autores_api[0].get('name')
                        # Dividir nombre y apellido (Ej: "George Orwell" -> ["George", "Orwell"])
                        partes = nombre_completo.split(' ', 1)
                        nom = partes[0]
                        ape = partes[1] if len(partes) > 1 else " "

                        # MÁGIA AQUÍ: Si no existe, lo crea automáticamente
                        autor_obj, creado = Autor.objects.get_or_create(
                            nombre=nom, 
                            apellido=ape
                        )
                        autor_id_final = autor_obj.id
                        
                        if creado:
                            messages.info(request, f"Se ha registrado un nuevo autor: {nombre_completo}")

                    datos_api = {
                        'titulo': libro_info.get('title'),
                        'descripcion': libro_info.get('notes') or libro_info.get('description') or "Sin sinopsis.",
                        'isbn': isbn,
                        'autor_id': autor_id_final # Este ID se usará en el select del HTML
                    }
                else:
                    messages.error(request, "El ISBN no devolvió resultados.")
            except Exception as e:
                messages.error(request, f"Error de conexión: {e}")

        # --- ACCIÓN: GUARDAR LIBRO DEFINITIVAMENTE ---
        elif 'guardar_manual' in request.POST:
            titulo = request.POST.get('titulo')
            autor_id = request.POST.get('autor')
            isbn_final = request.POST.get('isbn_final')
            descripcion = request.POST.get('descripcion')
            cantidad = request.POST.get('cantidad', 1) # Añade un input de cantidad en tu HTML

            if titulo and autor_id:
                autor = Autor.objects.get(id=autor_id)
                Libro.objects.create(
                    titulo=titulo,
                    autor=autor,
                    isbn=isbn_final,
                    descripcion=descripcion,
                    cantidad_total=cantidad, # Nuevo campo de Odoo
                    disponible=True
                )
                messages.success(request, "¡Libro guardado exitosamente!")
                return redirect('lista_libros')

    # Actualizamos la lista de autores por si se creó uno nuevo en este request
    autores = Autor.objects.all()
    
    return render(request, 'gestion/templates/templates_crear/crear_libro.html', {
        'autores': autores,
        'datos_api': datos_api
    })

def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'gestion/templates/autores.html', {'autores': autores})

@login_required
def crear_autor(request, id = None):
    if id == None:
        autor = None
        nodo = 'Crear Autor'
    else:
        autor = get_object_or_404(Autor, id=id)
        nodo = 'Editar Autor'

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        
        if autor == None:
            Autor.objects.create(nombre=nombre, apellido=apellido, bibliografia=bibliografia)
        else:
            autor.nombre = nombre
            autor.apellido = apellido
            autor.bibliografia = bibliografia
            autor.save()
        return redirect('lista_autores')
    context = {
        'autor': autor,
        'titulo': 'Editar Autor' if nodo == 'Editar Autor' else 'Crear Autor',
        'texto_boton': 'Guardar Cambios' if nodo == 'Editar Autor' else 'Crear Autor'
    }
    return render(request, 'gestion/templates/templates_crear/crear_autor.html', context)


def lista_prestamos(request):
    prestamos = Prestamos.objects.all()
    return render(request, 'gestion/templates/prestamos.html', {'prestamos': prestamos})

def crear_prestamo(request):
    # 1. Verificación de permisos
    if not request.user.has_perm('gestion.Gestionar_prestamos'):
        return HttpResponseForbidden("No tienes permiso para realizar esta acción.")
    
    # 2. Datos para los selectores del formulario
    libros_disponibles = Libro.objects.filter(disponible=True)
    usuarios = User.objects.all()

    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        usuario_id = request.POST.get('usuario')
        fecha_p = request.POST.get('fecha_prestamo')

        if libro_id and usuario_id:
            libro_obj = get_object_or_404(Libro, id=libro_id)
            usuario_obj = get_object_or_404(User, id=usuario_id)
            
            try:
                # IMPORTANTE: Asegúrate de que el modelo se llame Prestamo
                Prestamos.objects.create(
                    libro=libro_obj, 
                    usuario=usuario_obj, 
                    fecha_prestamo=fecha_p or timezone.now().date()
                )
                
                messages.success(request, f"¡Préstamo de '{libro_obj.titulo}' registrado con éxito!")
                return redirect('lista_prestamos')
                
            except Exception as e:
                # Captura errores de validación del modelo (como stock agotado)
                messages.error(request, f"Error al procesar: {str(e)}")

    # 3. Fecha de hoy para el input date del HTML
    fecha_hoy = timezone.now().date().isoformat()
    
    # Revisa que la ruta del template sea correcta según tu estructura
    return render(request, 'templates_crear/crear_prestamo.html', {
        'libros': libros_disponibles, 
        'usuarios': usuarios, 
        'fecha': fecha_hoy
    })
def detalle_prestamo(request):
    pass

def lista_multa(request):
    multas = Multa.objects.all()
    return render(request, 'gestion/templates/multas.html', {'multas': multas})

def crear_multa(request, prestamo_id):
    prestamo = get_object_or_404(Prestamos, id=prestamo_id)
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo_multa') # Viene del select del HTML
        
        # 1. Definimos montos según tus opciones del modelo
        # Ajustados para que no excedan los 3 dígitos (max 9.99 si max_digits=3)
        montos = {
            'retraso': 1.00,
            'deterioro': 5.00,
            'perdida': 9.00, # Cuidado: tu max_digits=3 solo permite hasta 9.99
        }
        monto_sancion = montos.get(tipo, 2.00)

        # 2. Crear la multa con los nombres de campos REALES de tu modelo
        Multa.objects.create(
            prestamo=prestamo,
            tipo_multa=tipo,      # Campo correcto
            monto=monto_sancion,   # Campo correcto
            fecha=timezone.now()   # Campo correcto (en lugar de fecha_emision)
        )

        # 3. Lógica de Stock y Devolución
        if tipo == 'perdida':
            prestamo.libro.cantidad_total -= 1
            prestamo.libro.save()
        else:
            prestamo.libro.disponible = True
            prestamo.libro.save()

        # 4. Finalizar préstamo
        prestamo.fecha_devolucion = timezone.now().date()
        prestamo.save()

        messages.success(request, "Multa registrada y libro devuelto.")
        return redirect('lista_multas')

    return render(request, 'templates_crear/crear_multa.html', {'prestamo': prestamo})

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'gestion/templates/registration/registro.html', {'form': form})

# Create your views here.
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy

class LibroListView(LoginRequiredMixin, ListView):
    model = Libro
    template_name = 'gestion/templates/libro_view.html'
    context_object_name = 'libros'
    paginate_by = 10

class LibroDetalleView(LoginRequiredMixin, DetailView):
    model = Libro
    template_name = 'gestion/templates/detalle_libro.html'
    context_object_name = 'libro'

class LibroCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Libro
    fields = ['titulo', 'autor', 'disponible']
    template_name = 'gestion/templates/templates_crear/crear_libro.html'
    success_url = reverse_lazy('libro_list')
    permission_required = 'Gestion.add_libro'

class LibroUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Libro
    fields = ['titulo', 'autor']
    template_name = 'gestion/templates/editar_libro.html'
    success_url = reverse_lazy('libro_list')
    permission_required = 'Gestion.change_libro'

class LibroDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Libro
    template_name = 'gestion/templates/eliminar_libro.html'
    success_url = reverse_lazy('libro_list')
    permission_required = 'Gestion.delete_libro'