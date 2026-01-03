from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', index, name ='index'),

    #Path class view
    path('libros_list/', LibroListView.as_view(), name='libro_list'),

    #Gestion de Usuarios
    path('login/', auth_views.LoginView.as_view(), name = 'login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name = 'logout'),

    #Cambio de cantraseña
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    path('registro/', registro, name='registro'),

    #libros
    path('libros/nuevo', crear_libro, name='crear_libro'),

    #autores
    path('autores/', lista_autores, name='lista_autores'),
    path('autores/nuevo', crear_autor, name='crear_autor'),
    path('autores/<int:id>/editar', crear_autor, name='editar_autor'),

    #prestamos
    path('prestamos/', lista_prestamos, name='lista_prestamos'),
    path('prestamos/nuevo', crear_prestamo, name='crear_prestamo'),
    path('pretamos/<int:id>', detalle_prestamo, name='detalle_prestamo'),

    path('prestamos/devolver/<int:prestamo_id>/', devolver_libro, name='devolver_libro'),

    #multas
    path('multas/', lista_multa, name='lista_multas'),
    path('multas/nuevo/<int:prestamo_id>', crear_multa, name='crear_multa'),

    path('multas/pagar/<int:multa_id>/', pagar_multa, name='pagar_multa'),

]