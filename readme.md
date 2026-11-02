# Rappiteca

Rappiteca es una aplicación web de gestión de biblioteca para instituciones educativas. Permite a estudiantes, docentes y personal consultar disponibilidad de libros, solicitar préstamos y gestionar devoluciones en tiempo real, mientras que los administradores controlan el inventario, las fechas de vencimiento y las multas desde un mismo lugar — reemplazando procesos manuales y en papel.

## Arquitectura (MVT)

El proyecto sigue el patrón **Model–View–Template** de Django, dividido en apps por dominio funcional:

El proyecto está dividido en las siguientes apps, cada una responsable de un dominio funcional:

| App | Responsabilidad |
|---|---|
| `accounts` | Registro, inicio de sesión (usuario y administrador), cierre de sesión, recuperación de contraseña, y gestión de perfiles de usuario |
| `catalog` | Gestión del inventario de libros (agregar, editar, eliminar), búsqueda, filtros y visualización de disponibilidad y detalle de cada libro |
| `loans` | Solicitud, devolución y renovación de préstamos, visualización de préstamos activos e historial, y recordatorios/alertas de vencimiento |
| `reservations` | Reserva de libros no disponibles, cancelación de reservas, y notificación cuando un libro reservado queda disponible |
| `fines` | Cálculo y aplicación de multas por retraso, seguimiento del estado de pago, y notificaciones de multas |
| `reports` | Generación de reportes administrativos (libros más prestados, tasas de mora, usuarios más activos) y registro de auditoría de acciones de administrador |

> **Convención de archivos estáticos y templates**: cada app anida sus estáticos bajo `static/<nombre_app>/...` (por ejemplo `catalog/static/catalog/css/style.css`) para evitar colisiones cuando dos apps tienen un archivo con el mismo nombre relativo.

## Requisitos previos

- Python 3.13.14
- pip 26.1.2

## Librerías utilizadas

| Librería | Uso |
|---|---|
| `Django` | Framework principal del proyecto (modelos, vistas, templates, ORM, panel de administración) |
| `Pillow` | Procesamiento de imágenes (ej. portadas de libros) |
| `gunicorn` | Servidor WSGI para producción |
| `whitenoise` | Manejo de archivos estáticos en producción |

Todas las librerías necesarias están listadas en `requirements.txt`.

## Base de datos

El proyecto utiliza **SQLite**, la base de datos por defecto de Django. No se requiere ninguna instalación o configuración adicional: el archivo de base de datos se crea automáticamente al aplicar las migraciones.

## Instalación

### Opción 1: Instalación tradicional (sin Docker)

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

### Opción 2: Con Docker (recomendado)

**Requisitos previos:**
- Docker y Docker Compose instalados en tu computadora

**Pasos:**

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd Rappiteca

# 2. Construir y levantar la aplicación con Docker Compose
docker compose up -d --build

# 3. Crear un superusuario dentro del contenedor (para acceder a /admin)
docker compose exec web python manage.py createsuperuser
```

Las migraciones y la recolección de archivos estáticos se ejecutan automáticamente cada vez que el contenedor arranca, por lo que no es necesario correrlas manualmente. El servidor de producción utilizado es **Gunicorn**, y los archivos estáticos se sirven con **WhiteNoise**.

La aplicación queda disponible en `http://localhost/` y el panel de administración en `http://localhost/admin/`.

**Comandos útiles:**

```bash
# Ver los logs de la aplicación
docker compose logs -f web

# Detener la aplicación
docker compose down

# Reiniciar tras cambios en el código
docker compose up -d --build
```

> **Nota:** La base de datos (`db.sqlite3`) y los archivos subidos (`media/`) se guardan en la carpeta del proyecto, por lo que se conservan aunque el contenedor se detenga o se recree.

#### Variables de entorno (definidas en `docker-compose.yml`)

| Variable | Descripción |
|---|---|
| `DEBUG` | `0` para producción, `1` para desarrollo |
| `SECRET_KEY` | Clave secreta de Django |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma (`*` acepta cualquiera) |

#### Despliegue en AWS

La aplicación está desplegada en una instancia **EC2** (Ubuntu) con Docker. URL: `http://<IP-ELASTICA>/`

## Cómo probar la aplicación

Actualmente no se incluyen *fixtures* ni datos de prueba precargados. Para probar la aplicación:

1. **Crear datos de prueba (libros, etc.):** inicia sesión en `http://127.0.0.1:8000/admin/` con el superusuario creado en el paso 5 de la instalación, y crea los registros necesarios (libros, categorías, etc.) directamente desde el panel de administración.
2. **Crear un usuario normal:** ve a la página de *signup* de la aplicación (`http://127.0.0.1:8000/accounts/signup/`) y regístrate como un usuario regular para probar la experiencia desde ese rol.
3. **Crear un usuario administrador (opcional):** si necesitas otro usuario con permisos de administrador (además del superusuario), puedes crearlo con:

```bash
python manage.py createsuperuser
```

o asignarle el estado de *staff*/*superuser* a un usuario existente desde el panel de `/admin/`.
