# Rappiteca

Rappiteca es una aplicación web de gestión de biblioteca para instituciones educativas. Permite a estudiantes, docentes y personal consultar disponibilidad de libros, solicitar préstamos y gestionar devoluciones en tiempo real, mientras que los administradores controlan el inventario, las fechas de vencimiento y las multas desde un mismo lugar — reemplazando procesos manuales y en papel.

## Arquitectura (MVT)

El proyecto sigue el patrón **Model–View–Template** de Django, dividido en apps por dominio funcional:

| App | Responsabilidad |
|---|---|
| `accounts` | Registro, inicio de sesión, cierre de sesión y datos de usuario |
| `catalog` | Página de inicio y búsqueda pública del catálogo de libros |

Apps planeadas para las siguientes etapas: `loans` (préstamos), `reservations` (reservas), `fines` (multas), `reports` (reportes administrativos).

> **Convención de archivos estáticos y templates**: cada app anida sus estáticos bajo `static/<nombre_app>/...` (por ejemplo `catalog/static/catalog/css/style.css`) para evitar colisiones cuando dos apps tienen un archivo con el mismo nombre relativo.

## Requisitos previos

- Python 3.13.14
- pip 26.1.2

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd Rappiteca

# 2. Crear y activar un entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# 5. Crear un superusuario (para acceder a /admin)
python manage.py createsuperuser

# 6. Correr el servidor de desarrollo
python manage.py runserver
```

La aplicación queda disponible en `http://127.0.0.1:8000/` y el panel de administración en `http://127.0.0.1:8000/admin/`.