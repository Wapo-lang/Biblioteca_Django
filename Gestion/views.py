from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.views.generic import ListView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import ProtectedError
from .models import Autor, Libro, Prestamos, Multa
from .forms import CrearEmpleadoForm
import requests
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from datetime import timedelta, date

# --- FUNCIONES DE CHEQUEO DE GRUPOS ---
def es_admin_o_bodega(user):
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Bodega']).exists()

def es_gestion_prestamos(user):
    # Admin y Bibliotecario pueden gestionar préstamos y multas
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Bibliotecario']).exists()

def es_admin(user):
    return user.is_superuser or user.groups.filter(name='Administrador').exists()

# --- VISTAS ---

def index(request):
    return render(request, 'Gestion/templates/home.html')

@login_required
@user_passes_test(es_admin_o_bodega)
def crear_libro(request):
    autores = Autor.objects.all()
    datos_api = {}

    if request.method == 'POST':
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
                        partes = nombre_completo.split(' ', 1)
                        nom = partes[0]
                        ape = partes[1] if len(partes) > 1 else " "
                        autor_obj, creado = Autor.objects.get_or_create(nombre=nom, apellido=ape)
                        autor_id_final = autor_obj.id
                        if creado:
                            messages.info(request, f"Se ha registrado un nuevo autor: {nombre_completo}")
                    
                    portada_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
                    datos_api = {
                        'titulo': libro_info.get('title'),
                        'descripcion': libro_info.get('notes') or libro_info.get('description') or "Sin sinopsis.",
                        'isbn': isbn,
                        'autor_id': autor_id_final,
                        'portada_url': portada_url
                    }
                else:
                    messages.error(request, "El ISBN no devolvió resultados.")
            except Exception as e:
                messages.error(request, f"Error de conexión: {e}")

        elif 'guardar_manual' in request.POST:
            titulo = request.POST.get('titulo')
            autor_id = request.POST.get('autor')
            isbn_final = request.POST.get('isbn_final')
            descripcion = request.POST.get('descripcion')
            cantidad = request.POST.get('cantidad', 1)
            url_imagen = request.POST.get('portada_url_temp')

            if titulo and autor_id:
                autor = Autor.objects.get(id=autor_id)
                libro_instancia = Libro(
                    titulo=titulo,
                    autor=autor,
                    isbn=isbn_final,
                    descripcion=descripcion,
                    cantidad_total=cantidad,
                    disponible=True
                )
                if url_imagen:
                    try:
                        res = requests.get(url_imagen, timeout=10)
                        if res.status_code == 200:
                            img = Image.open(BytesIO(res.content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            buffer = BytesIO()
                            img.save(buffer, format='JPEG', quality=85)
                            nombre_foto = f"portada_{isbn_final}.jpg"
                            libro_instancia.portada.save(nombre_foto, ContentFile(buffer.getvalue()), save=False)
                    except Exception:
                        pass
                libro_instancia.save()
                messages.success(request, "¡Libro guardado con éxito!")
                return redirect('libro_list')

    return render(request, 'Gestion/templates/templates_crear/crear_libro.html', {'autores': autores, 'datos_api': datos_api})

def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'Gestion/templates/autores.html', {'autores': autores})

@login_required
@user_passes_test(es_admin_o_bodega)
def crear_autor(request, id=None):
    if id is None:
        autor = None
        nodo = 'Crear Autor'
    else:
        autor = get_object_or_404(Autor, id=id)
        nodo = 'Editar Autor'

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        if autor is None:
            Autor.objects.create(nombre=nombre, apellido=apellido, bibliografia=bibliografia)
        else:
            autor.nombre = nombre
            autor.apellido = apellido
            autor.bibliografia = bibliografia
            autor.save()
        return redirect('lista_autores')
    context = {
        'autor': autor,
        'titulo': nodo,
        'texto_boton': 'Guardar Cambios' if nodo == 'Editar Autor' else 'Crear Autor'
    }
    return render(request, 'Gestion/templates/templates_crear/crear_autor.html', context)

@login_required
def lista_prestamos(request):
    # Variable 'es_gestion' para usar en el HTML y mostrar botones
    es_gestion = request.user.is_superuser or request.user.groups.filter(name__in=['Administrador', 'Bibliotecario']).exists()
    
    if es_gestion:
        prestamos = Prestamos.objects.all().order_by('-fecha_prestamo')
    else:
        prestamos = Prestamos.objects.filter(usuario=request.user).order_by('-fecha_prestamo')
        
    return render(request, 'Gestion/templates/prestamos.html', {'prestamos': prestamos, 'es_gestion': es_gestion})

@login_required
def crear_prestamo(request):
    # Definimos quién es el usuario
    es_bibliotecario = request.user.is_superuser or request.user.groups.filter(name__in=['Administrador', 'Bibliotecario']).exists()
    es_cliente = request.user.groups.filter(name='Cliente').exists()
    
    if not (es_bibliotecario or es_cliente):
        return HttpResponseForbidden("No tienes permiso para solicitar préstamos.")
        
    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        libro_obj = get_object_or_404(Libro, id=libro_id)
        
        # 1. Validación de seguridad de stock (Incluso para solicitud, verificamos que haya algo que pedir)
        if libro_obj.ejemplares_disponibles <= 0:
            messages.error(request, f"Lo sentimos, el libro '{libro_obj.titulo}' no tiene stock disponible.")
            return redirect('libro_list')

        # 2. Definir lógica según rol
        if es_bibliotecario:
            usuario_id = request.POST.get('usuario')
            usuario_obj = get_object_or_404(User, id=usuario_id)
            estado_inicial = 'p'  # Prestado (Aprobado directo)
            fecha_p = request.POST.get('fecha_prestamo') or timezone.now().date()
        else:
            usuario_obj = request.user
            estado_inicial = 's'  # Solicitado (No resta stock todavía)
            fecha_p = timezone.now().date()

        try:
            # 3. Crear el objeto préstamo
            prestamo = Prestamos.objects.create(
                libro=libro_obj,
                usuario=usuario_obj,
                fecha_prestamo=fecha_p,
                estado=estado_inicial
            )
            
            # 4. Lógica de Stock: Solo si el bibliotecario lo crea (Estado 'p')
            if estado_inicial == 'p':
                # Restamos el ejemplar
                libro_obj.ejemplares_disponibles -= 1
                if libro_obj.ejemplares_disponibles == 0:
                    libro_obj.disponible = False
                libro_obj.save()
                
                # Calcular fecha de vencimiento (14 días después)
                fecha_p_date = date.fromisoformat(str(fecha_p)) if isinstance(fecha_p, str) else fecha_p
                prestamo.fecha_max = fecha_p_date + timedelta(days=14)
                prestamo.save()
                
                messages.success(request, f"Préstamo registrado y stock actualizado. Entrega a: {usuario_obj.username}.")
            else:
                # Si es cliente, solo confirmamos la solicitud sin tocar el stock
                messages.success(request, f"Solicitud para '{libro_obj.titulo}' enviada. Pendiente de aprobación.")

            return redirect('lista_prestamos')

        except Exception as e:
            messages.error(request, f"Error al procesar el préstamo: {str(e)}")

    # Preparar datos para el formulario
    libros_disponibles = Libro.objects.filter(disponible=True, ejemplares_disponibles__gt=0)
    usuarios = User.objects.all() if es_bibliotecario else None
    
    context = {
        'libros': libros_disponibles,
        'usuarios': usuarios,
        'es_bibliotecario': es_bibliotecario,
        'today_date': timezone.now().date().strftime('%Y-%m-%d')
    }
    return render(request, 'templates_crear/crear_prestamo.html', context)

from django.db import transaction # Importante para la seguridad de los datos

@login_required
@user_passes_test(es_gestion_prestamos)
def aprobar_prestamo(request, prestamo_id):
    # Buscamos el préstamo asegurándonos que esté en estado 's' (solicitado)
    prestamo = get_object_or_404(Prestamos, id=prestamo_id, estado='s')

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'aprobar':
            # Usamos atomic para que si falla el save del prestamo, no se reste el libro (o viceversa)
            with transaction.atomic():
                libro = prestamo.libro
                if libro.ejemplares_disponibles > 0:
                    # 1. Actualizar el Préstamo
                    prestamo.estado = 'p'
                    prestamo.fecha_aprobacion = timezone.now().date()
                    # Sincronizamos con tu otra función: 14 días de plazo
                    prestamo.fecha_max = timezone.now().date() + timedelta(days=14)
                    prestamo.save()

                    # 2. Actualizar el Libro (Stock)
                    libro.ejemplares_disponibles -= 1
                    if libro.ejemplares_disponibles == 0:
                        libro.disponible = False
                    libro.save()

                    messages.success(request, f"Préstamo aprobado para {prestamo.usuario.username}. Stock restante: {libro.ejemplares_disponibles}")
                else:
                    messages.error(request, f"No se puede aprobar: El libro '{libro.titulo}' se acaba de agotar.")
        
        elif accion == 'rechazar':
            prestamo.estado = 'r'
            prestamo.save()
            messages.info(request, "La solicitud ha sido rechazada.")
        
        return redirect('lista_prestamos')

    return render(request, 'templates_crear/aprobar_prestamo.html', {'prestamo': prestamo})

@login_required
@user_passes_test(es_gestion_prestamos)
def devolver_libro(request, prestamo_id):
    # Solo podemos devolver algo que esté marcado como 'Prestado'
    prestamo = get_object_or_404(Prestamos, id=prestamo_id, estado='p')
    
    with transaction.atomic():
        # 1. Registrar fecha de devolución real
        prestamo.fecha_devolucion = timezone.now().date()
        
        # 2. Devolver stock al libro
        libro = prestamo.libro
        libro.ejemplares_disponibles += 1
        libro.disponible = True  # Al sumar uno, siempre estará disponible
        libro.save()
        
        # 3. Lógica de Multas
        # Usamos prestamo.dias_retraso (asegúrate de que este método exista en tu modelo)
        if prestamo.dias_retraso > 0:
            # Estado 'm' (Devuelto con multa pendiente)
            prestamo.estado = 'm'
            
            # Crear la multa en la base de datos
            multa_obj, created = Multa.objects.get_or_create(
                prestamo=prestamo,
                tipo_multa='retraso',
                defaults={
                    'monto': prestamo.multa_total, # Asegúrate que multa_total sea un property o campo
                    'fecha': timezone.now().date()
                }
            )
            messages.warning(request, f"Devolución registrada con {prestamo.dias_retraso} días de retraso. Se ha generado una multa.")
        else:
            # Estado 'd' (Devuelto a tiempo)
            prestamo.estado = 'd'
            messages.success(request, f"Libro '{libro.titulo}' devuelto correctamente y a tiempo.")
            
        prestamo.save()
        
    return redirect('lista_prestamos')

@login_required
def lista_multa(request):
    es_staff = request.user.is_superuser or request.user.groups.filter(name__in=['Administrador', 'Bibliotecario']).exists()
    
    if es_staff:
        multas_registradas = Multa.objects.all()
        # Buscamos préstamos que estén en estado multa pero sin registro en tabla Multa
        prestamos_vencidos = Prestamos.objects.filter(estado='m', multas__isnull=True)
    else:
        multas_registradas = Multa.objects.filter(prestamo__usuario=request.user)
        prestamos_vencidos = []
        
    return render(request, 'Gestion/templates/multas.html', {
        'multas': multas_registradas,
        'pendientes': prestamos_vencidos,
        'es_staff': es_staff
    })

@login_required
@user_passes_test(es_gestion_prestamos)
def crear_multa(request, prestamo_id):
    prestamo = get_object_or_404(Prestamos, id=prestamo_id)
    if request.method == 'POST':
        tipo = request.POST.get('tipo_multa')
        if tipo == 'retraso':
            monto_sancion = prestamo.multa_total
        else:
            montos_fijos = {'deterioro': 5.00, 'perdida': 9.00}
            monto_sancion = montos_fijos.get(tipo, 2.00)
            
        multa, creada = Multa.objects.get_or_create(
            prestamo=prestamo,
            tipo_multa=tipo,
            defaults={'monto': monto_sancion, 'fecha': timezone.now()}
        )
        
        # Ajustar stock si es pérdida
        if tipo == 'perdida':
             if prestamo.libro.cantidad_total > 0:
                 prestamo.libro.cantidad_total -= 1
             prestamo.libro.save()
             prestamo.estado = 'm'
        
        # Ajustar devolución si es deterioro/retraso y no se ha devuelto
        elif tipo in ['deterioro', 'retraso'] and not prestamo.fecha_devolucion:
             prestamo.libro.ejemplares_disponibles += 1
             prestamo.libro.disponible = True
             prestamo.libro.save()
             prestamo.fecha_devolucion = timezone.now().date()
             prestamo.estado = 'm'

        prestamo.save()
        messages.success(request, f"Multa registrada: ${monto_sancion}")
        return redirect('lista_multas')
        
    return render(request, 'Gestion/templates/templates_crear/crear_multa.html', {'prestamo': prestamo})

@user_passes_test(es_gestion_prestamos)
def pagar_multa(request, multa_id):
    multa = get_object_or_404(Multa, id=multa_id)
    multa.pagada = True
    multa.save()
    
    prestamo = multa.prestamo
    if not Multa.objects.filter(prestamo=prestamo, pagada=False).exists():
        prestamo.estado = 'd' # Devuelto y pagado
        prestamo.save()
        
    messages.success(request, f"Multa de {prestamo.usuario.username} pagada.")
    return redirect('lista_multas')

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            grupo_cliente = Group.objects.get(name='Cliente')
            usuario.groups.add(grupo_cliente)
            login(request, usuario)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'Gestion/templates/registration/registro.html', {'form': form})

@user_passes_test(es_admin)
def crear_empleado(request):
    if request.method == 'POST':
        form = CrearEmpleadoForm(request.POST)
        if form.is_valid():
            nuevo_user = form.save()
            # Asignar grupo seleccionado
            grupo = form.cleaned_data.get('grupo')
            if grupo:
                nuevo_user.groups.add(grupo)
            messages.success(request, "Empleado registrado con éxito.")
            return redirect('index')
    else:
        form = CrearEmpleadoForm()
        # Admin puede crear todo MENOS clientes
        form.fields['grupo'].queryset = Group.objects.exclude(name='Cliente')
        
    return render(request, 'admin_crear_empleado.html', {'form': form})

# --- MIXINS PARA CLASES ---

class StaffBodegaMixin(UserPassesTestMixin):
    """Permite acceso a Superusuario, Admin y Bodega para EDITAR LIBROS"""
    def test_func(self):
        u = self.request.user
        return u.is_superuser or u.groups.filter(name__in=['Administrador', 'Bodega']).exists()

    def handle_no_permission(self):
        messages.error(self.request, "Acceso restringido a Bodega.")
        return redirect('libro_list')

class PrestamoAdminMixin(UserPassesTestMixin):
    """Solo Admin puede eliminar historiales de prestamos"""
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(name='Administrador').exists()

class LibroDetalleView(LoginRequiredMixin, DetailView):
    model = Libro
    template_name = 'Gestion/templates/detalle_libro.html'
    context_object_name = 'libro'

class LibroListView(LoginRequiredMixin, ListView):
    model = Libro
    template_name = 'Gestion/templates/libro_view.html'
    context_object_name = 'libros'
    paginate_by = 5

class LibroUpdateView(LoginRequiredMixin, StaffBodegaMixin, UpdateView):
    model = Libro
    fields = ['titulo', 'autor', 'descripcion', 'cantidad_total'] # Agrega los campos que necesites
    template_name = 'Gestion/templates/editar_libro.html'
    success_url = reverse_lazy('libro_list')

class LibroDeleteView(LoginRequiredMixin, StaffBodegaMixin, DeleteView):
    model = Libro
    template_name = 'Gestion/templates/eliminar_libro.html'
    success_url = reverse_lazy('libro_list')
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "No se puede eliminar: el libro tiene préstamos activos.")
            return redirect('libro_list')

class PrestamoDeleteView(LoginRequiredMixin, PrestamoAdminMixin, DeleteView):
    model = Prestamos
    template_name = 'Gestion/templates/eliminar_prestamo.html'
    success_url = reverse_lazy('lista_prestamos')

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "No se puede eliminar este préstamo, tiene multas asociadas.")
            return redirect('lista_prestamos')