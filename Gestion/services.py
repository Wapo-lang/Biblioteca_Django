import requests

def obtener_datos_libro(isbn):
    # La API de OpenLibrary permite buscar por ISBN y pedir formato JSON
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        key = f"ISBN:{isbn}"
        if key in data:
            book_info = data[key]
            
            # Extraemos los datos con seguridad
            datos = {
                'titulo': book_info.get('title'),
                'autor_nombre': book_info.get('authors', [{}])[0].get('name', 'Anónimo'),
                # OpenLibrary a veces no trae descripción en 'data', 
                # pero trae 'notes' o el extracto.
                'descripcion': book_info.get('notes', 'Sin descripción disponible.')
            }
            return datos
        return None
    except Exception as e:
        print(f"Error conectando con OpenLibrary: {e}")
        return None