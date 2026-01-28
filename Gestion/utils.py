import xmlrpc.client
from django.conf import settings

def buscar_libro_odoo(isbn):
    try:
        # Conexión inicial
        common = xmlrpc.client.ServerProxy(f"{settings.ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(settings.ODOO_DB, settings.ODOO_USER, settings.ODOO_PASSWORD, {})
        
        if not uid:
            print("Error: Autenticación fallida en Odoo.")
            return None

        models = xmlrpc.client.ServerProxy(f"{settings.ODOO_URL}/xmlrpc/2/object")

        # 1. Buscamos el ID del libro
        # Usamos .strip() por si el ISBN trae espacios accidentales
        ids = models.execute_kw(settings.ODOO_DB, uid, settings.ODOO_PASSWORD,
            'biblioteca.libro', 'search', [[['isbn', '=', isbn.strip()]]])
        
        if ids:
            # 2. Leemos los campos específicos
            books_data = models.execute_kw(settings.ODOO_DB, uid, settings.ODOO_PASSWORD,
                'biblioteca.libro', 'read', [ids[0]], 
                {'fields': ['firstname', 'author', 'description', 'isbn']})
            
            if not books_data:
                return None
                
            libro_odoo = books_data[0]
            
            # 3. Procesar el autor (Many2one de Odoo devuelve [id, "nombre"])
            nombre_autor = "Desconocido"
            author_field = libro_odoo.get('author')
            if author_field and isinstance(author_field, list) and len(author_field) > 1:
                nombre_autor = author_field[1]
            
            # 4. Retornar diccionario limpio
            # Usamos "or ''" porque Odoo devuelve False si el campo está vacío en la DB
            return {
                'titulo': libro_odoo.get('firstname') or "Sin Título",
                'autor_nombre': nombre_autor,
                'descripcion': libro_odoo.get('description') or "Sin descripción en Odoo",
                'isbn': libro_odoo.get('isbn') or isbn,
                'origen': 'Odoo'
            }
            
    except Exception as e:
        print(f"Error crítico conectando con Odoo: {e}")
        return None
    
    return None