from django.urls import path, include
from .views import *
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .api_views import LibroViewSet, AutorViewSet

router = DefaultRouter()
router.register(r'libros-api', LibroViewSet, basename='libros-api')
router.register(r'autores-api', AutorViewSet, basename='autores-api')

urlpatterns = [
    path('', index, name ='index'),

    path('api/', include(router.urls)),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),

    # Libros
    path('libros_list/', LibroListView.as_view(), name='libro_list'),
    path('libros/<int:pk>/', LibroDetalleView.as_view(), name='libro_detalle'),
    path('libros/<int:pk>/editar/', LibroUpdateView.as_view(), name='libro_editar'),
    path('libros/<int:pk>/eliminar/', LibroDeleteView.as_view(), name='libro_eliminar'),
    path('libros/nuevo/', crear_libro, name='crear_libro'),

    # Usuarios y Autenticación
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('registro/', registro, name='registro'),
    path('personal/crear-empleado/', crear_empleado, name='crear_empleado'),

    # Autores
    path('autores/', lista_autores, name='lista_autores'),
    path('autores/nuevo/', crear_autor, name='crear_autor'),
    path('autores/<int:id>/editar/', crear_autor, name='editar_autor'),

    # Préstamos
    path('prestamos/', lista_prestamos, name='lista_prestamos'),
    path('prestamos/nuevo/', crear_prestamo, name='crear_prestamo'),
    path('prestamos/devolver/<int:prestamo_id>/', devolver_libro, name='devolver_libro'),
    path('prestamos/<int:pk>/eliminar/', PrestamoDeleteView.as_view(), name='eliminar_prestamo'),
    
    # ESTA ES LA QUE TE DABA EL ERROR (Faltaba definirla):
    path('prestamos/aprobar/<int:prestamo_id>/', aprobar_prestamo, name='aprobar_prestamo'),

    # Multas
    path('multas/', lista_multa, name='lista_multas'),
    path('multas/nuevo/<int:prestamo_id>/', crear_multa, name='crear_multa'),
    path('multas/pagar/<int:multa_id>/', pagar_multa, name='pagar_multa'),
]