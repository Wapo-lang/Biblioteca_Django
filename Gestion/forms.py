# Gestion/forms.py
from django import forms
from django.contrib.auth.models import User, Group

class CrearEmpleadoForm(forms.ModelForm):
    # El queryset se filtrará en la vista para mayor seguridad
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.all(), 
        label="Rol del Empleado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password']) # Encripta la clave
        if commit:
            user.save()
            user.groups.add(self.cleaned_data['grupo']) # Asigna el grupo
            user.is_staff = True  # Permite que entre a la interfaz administrativa básica
            user.save()
        return user