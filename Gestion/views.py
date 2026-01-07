from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
import requests
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from .models import Autor, Libro, Prestamos, Multa

def index(request):
    title = settings.TITLE
    return render(request, 'Gestion/templates/home.html', {'titulo': title})

@login_required
def lista_libros(request):
    libros = Libro.objects.all()
    return render(request, 'Gestion/templates/libros.html', {'libros': libros})

@login_required
@permission_required('Gestion.change_prestamos', raise_exception=True)
def devolver_libro(request, prestamo_id):
    prestamo = get_object_or_404(Prestamos, id=prestamo_id)
    
    if prestamo.fecha_devolucion:
        messages.info(request, "Este libro ya fue marcado como devuelto.")
        return redirect('lista_prestamos')

    # 3. REGISTRO DE LA DEVOLUCIÓN
    prestamo.fecha_devolucion = timezone.now().date()
    
    # 4. MANEJO DE STOCK (El libro regresa a la estantería)
    libro = prestamo.libro
    libro.ejemplares_disponibles += 1
    libro.disponible = True
    libro.save()

# 5. CÁLCULO DE MORA AUTOMÁTICO
    if prestamo.dias_retraso > 0:
        prestamo.estado = 'm'
        
        # Guardamos el objeto 'multa_obj' y el booleano 'created'
        multa_obj, created = Multa.objects.get_or_create(
            prestamo=prestamo,
            tipo_multa='retraso',
            defaults={
                'monto': prestamo.multa_total, # Aquí toma el valor calculado (ej: 2.50)
                'fecha': timezone.now().date()
            }
        )
        
        # MEJORA: Mostramos el monto exacto en el mensaje
        if created:
            messages.warning(request, f"Devolución con retraso. Multa generada de ${multa_obj.monto}.")
        else:
            messages.info(request, f"Devolución con retraso. Ya existía una multa de ${multa_obj.monto}.")
    else:
        prestamo.estado = 'd'  # Estado: Devuelto
        messages.success(request, f"Libro '{libro.titulo}' devuelto correctamente y a tiempo.")

    # 6. GUARDAR EL PRÉSTAMO ACTUALIZADO
    prestamo.save()
    
    return redirect('lista_prestamos')

@login_required
@permission_required('Gestion.add_libro', raise_exception=True)
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
                        partes = nombre_completo.split(' ', 1)
                        nom = partes[0]
                        ape = partes[1] if len(partes) > 1 else " "

                        autor_obj, creado = Autor.objects.get_or_create(
                            nombre=nom, 
                            apellido=ape
                        )
                        autor_id_final = autor_obj.id
                        
                        if creado:
                            messages.info(request, f"Se ha registrado un nuevo autor: {nombre_completo}")

                    # Generamos la URL de la portada para mostrarla en el HTML
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

        # --- ACCIÓN: GUARDAR LIBRO DEFINITIVAMENTE ---
        elif 'guardar_manual' in request.POST:
            titulo = request.POST.get('titulo')
            autor_id = request.POST.get('autor')
            isbn_final = request.POST.get('isbn_final')
            descripcion = request.POST.get('descripcion')
            cantidad = request.POST.get('cantidad', 1)
            url_imagen = request.POST.get('portada_url_temp') # Viene del input oculto

            if titulo and autor_id:
                autor = Autor.objects.get(id=autor_id)
                
                # Creamos la instancia sin guardar en BD aún
                libro_instancia = Libro(
                    titulo=titulo,
                    autor=autor,
                    isbn=isbn_final,
                    descripcion=descripcion,
                    cantidad_total=cantidad,
                    disponible=True
                )

                # --- PROCESAMIENTO CON PILLOW ---
                if url_imagen:
                    try:
                        res = requests.get(url_imagen, timeout=10)
                        if res.status_code == 200:
                            # Abrimos la imagen con Pillow desde la memoria
                            img = Image.open(BytesIO(res.content))
                            
                            # Convertimos a RGB (por si es PNG o tiene otros formatos)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # Guardamos en un buffer temporal
                            buffer = BytesIO()
                            img.save(buffer, format='JPEG', quality=85)
                            
                            # Guardamos el archivo en el modelo
                            nombre_foto = f"portada_{isbn_final}.jpg"
                            libro_instancia.portada.save(nombre_foto, ContentFile(buffer.getvalue()), save=False)
                    except Exception as e:
                        print(f"Error Pillow: {e}")

                libro_instancia.save() # Guardado final en la base de datos
                messages.success(request, "¡Libro guardado con éxito!")
                return redirect('libro_list')

    autores = Autor.objects.all()
    return render(request, 'Gestion/templates/templates_crear/crear_libro.html', {
        'autores': autores,
        'datos_api': datos_api
    })

def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'Gestion/templates/autores.html', {'autores': autores})

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
    return render(request, 'Gestion/templates/templates_crear/crear_autor.html', context)

@login_required
def lista_prestamos(request):
    es_gestion = request.user.is_superuser or request.user.groups.filter(name__in=['Administrador', 'Bibliotecario']).exists()

    if es_gestion:
        # Los que gestionan ven la lista completa de todos los clientes
        prestamos = Prestamos.objects.all().order_by('-fecha_prestamo')
    else:
        # Los Clientes (y Bodega, si entrara aquí) solo ven sus propios registros
        prestamos = Prestamos.objects.filter(usuario=request.user).order_by('-fecha_prestamo')
        
    return render(request, 'Gestion/templates/prestamos.html', {'prestamos': prestamos})

@login_required
def crear_prestamo(request):
    # 1. Definir roles claramente
    es_bibliotecario = request.user.is_superuser or request.user.groups.filter(name__in=['Administrador', 'Bibliotecario']).exists()
    es_cliente = request.user.groups.filter(name='Cliente').exists()

    # 2. Seguridad: Si no es personal ni cliente, prohibido
    if not (es_bibliotecario or es_cliente):
        return HttpResponseForbidden("No tienes permiso para solicitar préstamos.")

    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        # Si el cliente no puede editar la fecha, usamos la de hoy
        fecha_p = request.POST.get('fecha_prestamo') or timezone.now().date()
        
        # 3. Identificar quién recibirá el libro
        if es_bibliotecario:
            usuario_id = request.POST.get('usuario')
            usuario_obj = get_object_or_404(User, id=usuario_id)
        else:
            usuario_obj = request.user # El cliente se asigna a sí mismo

        libro_obj = get_object_or_404(Libro, id=libro_id)

        # 4. Validar disponibilidad real antes de crear
        if libro_obj.ejemplares_disponibles <= 0:
            messages.error(request, f"Lo sentimos, el libro '{libro_obj.titulo}' ya no tiene ejemplares disponibles.")
            return redirect('libro_list')

        try:
            # 5. Crear el registro
            Prestamos.objects.create(
                libro=libro_obj, 
                usuario=usuario_obj, 
                fecha_prestamo=fecha_p,
                estado='p' # 'p' de pedido/pendiente
            )
            
            # 6. Actualizar el stock del libro
            libro_obj.ejemplares_disponibles -= 1
            if libro_obj.ejemplares_disponibles == 0:
                libro_obj.disponible = False
            libro_obj.save()

            messages.success(request, "El préstamo se ha registrado correctamente.")
            return redirect('lista_prestamos')
            
        except Exception as e:
            messages.error(request, f"Error al procesar el préstamo: {str(e)}")

    # Preparación para el GET (Carga del formulario)
    libros_disponibles = Libro.objects.filter(disponible=True, ejemplares_disponibles__gt=0)
    usuarios = User.objects.all() if es_bibliotecario else None
    
    context = {
        'libros': libros_disponibles,
        'usuarios': usuarios,
        'es_bibliotecario': es_bibliotecario,
        'today_date': timezone.now().date().isoformat() # Para el valor default del HTML
    }
    
    return render(request, 'Gestion/templates/templates_crear/crear_prestamo.html', context)
def detalle_prestamo(request):
    pass

@login_required
def lista_multa(request):
    if request.user.is_staff:
        # El Admin ve todas las multas y los préstamos pendientes de sanción
        multas_registradas = Multa.objects.all()
        prestamos_vencidos = Prestamos.objects.filter(estado='m', multas__isnull=True)
    else:
        # El Usuario normal solo ve SUS multas ya procesadas
        multas_registradas = Multa.objects.filter(prestamo__usuario=request.user)
        # Los usuarios no deberían ver "pendientes" de procesamiento administrativo
        prestamos_vencidos = [] 
    
    return render(request, 'Gestion/templates/multas.html', {
        'multas': multas_registradas,
        'pendientes': prestamos_vencidos
    })

@user_passes_test(lambda u: u.groups.filter(name__in=['Administrador', 'Bibliotecario']).exists())
def pagar_multa(request, multa_id):
    multa = get_object_or_404(Multa, id=multa_id)
    multa.pagada = True
    multa.save()

    prestamo = multa.prestamo
    multas_pendientes = Multa.objects.filter(prestamo=prestamo, pagada=False).exists()
    
    if not multas_pendientes:
        prestamo.estado = 'd'
        prestamo.save()

    messages.success(request, f"Multa de {prestamo.usuario.username} pagada. Estado actualizado.")
    return redirect('lista_multas')

@login_required
@permission_required('Gestion.add_multa', raise_exception=True)
def crear_multa(request, prestamo_id):
    prestamo = get_object_or_404(Prestamos, id=prestamo_id)
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo_multa')
        
        # --- CAMBIO AQUÍ: Lógica de montos dinámica ---
        if tipo == 'retraso':
            # Usamos el cálculo automático de tu modelo
            monto_sancion = prestamo.multa_total 
        else:
            # Para los demás casos, usamos valores fijos
            montos_fijos = {
                'deterioro': 5.00,
                'perdida': 9.00, 
            }
            monto_sancion = montos_fijos.get(tipo, 2.00)
        # ----------------------------------------------

        # Usar get_or_create para evitar duplicar multas del mismo tipo
        multa, creada = Multa.objects.get_or_create(
            prestamo=prestamo,
            tipo_multa=tipo,
            defaults={
                'monto': monto_sancion,
                'fecha': timezone.now()
            }
        )

        if not creada:
            messages.info(request, f"Ya existía una multa por {tipo} para este préstamo.")
            return redirect('lista_multas')

        # Lógica de Stock
        if tipo == 'perdida':
            if prestamo.libro.cantidad_total > 0:
                prestamo.libro.cantidad_total -= 1
            prestamo.libro.save()
            prestamo.estado = 'm' 
        
        elif tipo == 'deterioro' or tipo == 'retraso':
             # En ambos casos el libro regresa al inventario
             if not prestamo.fecha_devolucion: # Solo si no se había devuelto ya
                 prestamo.libro.ejemplares_disponibles += 1
                 prestamo.libro.disponible = True
                 prestamo.libro.save()
             prestamo.estado = 'm'

        # Cerramos el ciclo del préstamo
        if not prestamo.fecha_devolucion:
            prestamo.fecha_devolucion = timezone.now().date()
        
        prestamo.save()

        messages.success(request, f"Multa por {tipo} registrada por ${monto_sancion}.")
        return redirect('lista_multas') 

    return render(request, 'Gestion/templates/templates_crear/crear_multa.html', {'prestamo': prestamo})

from django.contrib.auth.models import Group
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

# views.py
from .forms import CrearEmpleadoForm # Asegúrate de importar el form
from django.contrib.auth.models import Group

@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='Administrador').exists())
def crear_empleado(request):
    if request.method == 'POST':
        form = CrearEmpleadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Nuevo personal registrado con éxito.")
            return redirect('index')
    else:
        form = CrearEmpleadoForm()
        
        # FILTRO DE JERARQUÍA:
        if request.user.is_superuser:
            # Superusuario ve todo menos Clientes (que se registran solos)
            form.fields['grupo'].queryset = Group.objects.exclude(name='Cliente')
        else:
            # Administrador SOLO puede crear Bibliotecarios y Bodega
            form.fields['grupo'].queryset = Group.objects.filter(name__in=['Bibliotecario', 'Bodega'])
            
    return render(request, 'admin_crear_empleado.html', {'form': form})

# Create your views here.
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import ProtectedError

class StaffBodegaMixin(UserPassesTestMixin):
    def test_func(self):
        # El nombre debe coincidir EXACTAMENTE con tu script de roles: 'Bodega' o 'Administrador'
        usuario = self.request.user
        es_personal_bodega = usuario.groups.filter(name='Bodega').exists()
        es_admin = usuario.groups.filter(name='Administrador').exists()
        
        # DEBUG: Mira tu terminal cuando intentes entrar
        print(f"DEBUG: Usuario {usuario.username} - Bodega: {es_personal_bodega} - Admin: {es_admin}")
        
        return usuario.is_superuser or es_personal_bodega or es_admin

    def handle_no_permission(self):
        messages.error(self.request, "Tu perfil no tiene permisos de Bodega para realizar esta acción.")
        return redirect('libro_list') # Redirige a la lista en lugar de Forbidden
    
class LibroDetalleView(LoginRequiredMixin, DetailView):
    model = Libro
    template_name = 'Gestion/templates/detalle_libro.html'
    context_object_name = 'libro'

class LibroListView(LoginRequiredMixin, ListView):
    model = Libro
    template_name = 'Gestion/templates/libro_view.html'
    context_object_name = 'libros'
    paginate_by = 5

class LibroCreateView(LoginRequiredMixin, StaffBodegaMixin, CreateView):
    model = Libro
    fields = ['titulo', 'autor', 'disponible'] # Asegúrate de que estos nombres existan en models.py
    template_name = 'Gestion/templates_crear/crear_libro.html' 
    success_url = reverse_lazy('libro_list')

class LibroUpdateView(LoginRequiredMixin, StaffBodegaMixin, UpdateView):
    model = Libro
    fields = ['titulo', 'autor']
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
        
class PrestamoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Prestamos
    template_name = 'Gestion/templates/eliminar_prestamo.html'
    success_url = reverse_lazy('lista_prestamos')
    permission_required = 'Gestion.delete_prestamos'

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            # Mensaje claro para el administrador
            messages.error(request, 
                "No se puede eliminar este préstamo porque tiene una MULTA asociada. "
                "Primero debes eliminar la multa correspondiente en el panel de multas."
            )
            return redirect('lista_prestamos')
