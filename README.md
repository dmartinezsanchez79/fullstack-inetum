## Portal de Incidencias / Tickets (mini Service Desk)

Proyecto de ejemplo tipo Service Desk desarrollado con **FastAPI + SQLModel + JWT** en el backend y **HTML/CSS/JS vanilla** en el frontend.

### Estructura del proyecto

- **backend/**
  - `app/main.py` – aplicación FastAPI, CORS, rutas y static files
  - `app/db.py` – conexión SQLite y utilidades de sesión
  - `app/core/config.py` – configuración general y JWT
  - `app/core/security.py` – hash de contraseñas y creación de tokens
  - `app/models/` – modelos SQLModel (`User`, `Ticket`, `Comment`)
  - `app/schemas/` – esquemas Pydantic para requests/responses
  - `app/routers/auth.py` – endpoints de autenticación
  - `app/routers/tickets.py` – endpoints de tickets y comentarios
  - `app/services/seed.py` – semillas de usuarios y tickets de ejemplo
- **frontend/**
  - `index.html` – SPA sencilla (login + dashboard + detalle)
  - `styles.css` – estilos responsivos tipo panel
  - `app.js` – lógica de UI y llamadas a la API
- `requirements.txt` – dependencias de Python
- `requests.http` – ejemplos de peticiones HTTP

### Requisitos

- Python 3.11
- pip

### Instalación y ejecución

1. Crear y activar entorno virtual (opcional pero recomendado):

```bash
cd "UNIVERSIDAD /inetum"
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Ejecutar el servidor de desarrollo:

```bash
uvicorn backend.app.main:app --reload
```

4. Abrir el navegador en:

- `http://localhost:8000` → frontend SPA
- `http://localhost:8000/docs` → documentación interactiva Swagger

### Modelos principales

- **User**
  - `id`, `email`, `full_name`, `role` (`USER` | `AGENT`), `hashed_password`, `is_active`, `created_at`
- **Ticket**
  - `id`, `title`, `description`, `priority` (`LOW` | `MEDIUM` | `HIGH`)
  - `status` (`OPEN` | `IN_PROGRESS` | `RESOLVED` | `CLOSED`)
  - `created_by_id`, `assigned_to_id`, `created_at`, `updated_at`
- **Comment**
  - `id`, `ticket_id`, `author_id`, `content`, `created_at`

### Autenticación y roles

- **JWT** tipo Bearer:
  - `POST /api/auth/login` devuelve `access_token`
  - El token se envía en `Authorization: Bearer <token>`
- Roles de usuario:
  - `USER` – usuario final que crea tickets y puede editar los suyos mientras estén `OPEN`
  - `AGENT` – agente de soporte que ve todos los tickets, cambia estado, prioridad y asignación, y puede borrar tickets

Endpoints principales:

- `POST /api/auth/register` – registro de usuario (opcional, devuelve `USER` o `AGENT` según rol enviado)
- `POST /api/auth/login` – login con `email` y `password`, devuelve `access_token`
- `GET /api/auth/me` – información del usuario autenticado

### Tickets

- `POST /api/tickets` (USER) – crear ticket
- `GET /api/tickets` – listar:
  - USER → solo sus tickets
  - AGENT → todos los tickets
  - Parámetros:
    - `status` (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`)
    - `priority` (`LOW`, `MEDIUM`, `HIGH`)
    - `search` (busca en `title` y `description`)
    - `page`, `page_size`
- `GET /api/tickets/{id}` – detalle (creador o AGENT)
- `PATCH /api/tickets/{id}`:
  - USER → no permitido (usa comentarios para actualizaciones)
  - AGENT → puede modificar `status`, `priority`, `assigned_to_id`
- `DELETE /api/tickets/{id}` – solo AGENT

### Comentarios

- `POST /api/tickets/{id}/comments` – añadir comentario (creador o AGENT)
- `GET /api/tickets/{id}/comments` – listar comentarios del ticket

### Exportación a Excel (AGENT)

- `GET /api/tickets/export` – exporta todos los tickets a un `.xlsx` (solo AGENT)

### Semillas de datos

Al iniciar la aplicación se aseguran automáticamente estos usuarios demo (solo se crean si no existen):

- Usuario demo **USER principal**:
  - Email: `user@demo.com`
  - Password: `Demo1234!`
- Usuario demo **USER secundario (user1)**:
  - Email: `user1@demo.com`
  - Password: `Demo1234!`
- Usuario demo **AGENT**:
  - Email: `agent@demo.com`
  - Password: `Demo1234!`

Si aún no existen tickets, también se crean:

- 3 tickets de ejemplo asociados al usuario `user@demo.com` y asignados al agente.
- 1 ticket de ejemplo asociado a `user1@demo.com` y asignado al agente.

### Frontend (flujo de uso)

1. Abrir `http://localhost:8000`.
2. Iniciar sesión con uno de los usuarios demo:
   - USER principal: `user@demo.com` / `Demo1234!`
   - USER secundario (user1): `user1@demo.com` / `Demo1234!`
   - AGENT: `agent@demo.com` / `Demo1234!`
3. El token JWT se almacena en `localStorage` y se envía automáticamente en todas las llamadas `fetch` como `Authorization: Bearer ...`.
4. Dashboard:
   - Si eres **USER**:
     - Verás "Mis tickets".
     - Botón **"Crear ticket"** (abre modal para nuevo ticket).
    - Puedes añadir comentarios para dejar actualizaciones (mini chat).
   - Si eres **AGENT**:
     - Verás "Todos los tickets".
     - En el detalle de ticket puedes:
       - Cambiar estado (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`).
       - Cambiar prioridad (`LOW`, `MEDIUM`, `HIGH`).
       - Pulsar "**Asignarme ticket**" para poner `assigned_to_id` a tu id.
       - Eliminar el ticket.
    - Puedes exportar las incidencias a Excel desde el dashboard.
5. Vista detalle:
   - Muestra datos del ticket, metadatos y comentarios.
   - Caja de texto para añadir comentarios (USER creador o AGENT).

### Ejemplos de requests

En `requests.http` tienes 4–6 ejemplos listos para usar (VSCode/Cursor/IntelliJ con soporte para `.http`):

- Login USER demo
- Login AGENT demo
- `GET /api/auth/me`
- `GET /api/tickets`
- `POST /api/tickets`
- `PATCH /api/tickets/{id}`
- `POST /api/tickets/{id}/comments`
- `GET /api/tickets/export`

Solo debes sustituir `{{access_token}}` por el token devuelto en el login.

### Notas sobre seguridad y entorno real

- Cambia `secret_key` en `backend/app/core/config.py` por un valor seguro en producción.
- Ajusta `cors_origins` a los orígenes permitidos reales.
- Para un entorno enterprise real, añadirías:
  - Migraciones con Alembic.
  - Gestión de usuarios/roles más avanzada.
  - Logs estructurados, tracing, tests automatizados, etc.

