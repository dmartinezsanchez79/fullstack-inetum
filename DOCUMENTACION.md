## Portal de Incidencias / Tickets – Documentación técnica

Este documento explica **qué hace** el proyecto, **cómo está organizado** el backend y el frontend, y **por qué** se han tomado ciertas decisiones. Está pensado para alguien que viene de Java y está empezando con Python/FastAPI.

---

### 1. Visión general

**Objetivo:** portal sencillo de gestión de incidencias / tickets (mini Service Desk).

- **Backend**: Python 3.11, FastAPI, SQLModel (sobre SQLAlchemy) y SQLite.
- **Autenticación**: JWT (access token) + contraseñas con hash (pbkdf2_sha256).
- **Frontend**: HTML + CSS + JavaScript (sin frameworks).
- **BBDD**: archivo SQLite `app.db` en la raíz del proyecto.

Roles:

- `USER`: usuario final que crea tickets y ve solo los suyos.
- `AGENT`: agente que ve todos los tickets, puede cambiarlos, asignárselos, borrarlos y exportarlos a Excel.

---

### 2. Estructura de carpetas (backend)

Ruta base del backend: `backend/app/`

- `main.py`: punto de entrada de la aplicación FastAPI.
- `db.py`: conexión a SQLite y creación de sesiones.
- `core/`
  - `config.py`: configuración global (nombre app, claves JWT, CORS…).
  - `security.py`: hashing de contraseñas y creación/decodificación de tokens JWT.
- `models/`
  - `user.py`: modelo `User` y enum `UserRole`.
  - `ticket.py`: modelo `Ticket`, enums `TicketPriority` y `TicketStatus`.
  - `comment.py`: modelo `Comment`.
  - `__init__.py`: “reexporta” los modelos para imports más cortos.
- `schemas/`
  - `auth.py`: esquemas Pydantic para login/registro/usuario leído.
  - `ticket.py`: esquemas de creación/lectura/actualización de tickets.
  - `comment.py`: esquemas de creación/lectura de comentarios.
- `routers/`
  - `auth.py`: endpoints de autenticación (`/api/auth/...`).
  - `tickets.py`: endpoints de tickets y comentarios (`/api/tickets/...`).
- `deps.py`: dependencias reutilizables de FastAPI (auth, roles, DB).
- `services/`
  - `seed.py`: semillas (usuarios demo y tickets de ejemplo).

---

### 3. FastAPI: `main.py`

Archivo: `backend/app/main.py`

Responsabilidades:

- Crear la aplicación FastAPI.
- Configurar CORS (para que el frontend pueda llamar a la API).
- Ejecutar lógica de arranque (crear tablas, limpiar datos huérfanos, seed).
- Incluir los routers (`auth`, `tickets`).
- Servir el frontend estático desde `frontend/`.

Puntos clave:

- `app = FastAPI(title=settings.app_name)`: instancia principal de la API.
- `CORSMiddleware`: se permite cualquier origen (`"*"` en desarrollo); se podría restringir en producción.
- `@app.on_event("startup")`:
  - `init_db()`: crea tablas en SQLite si no existen.
  - Limpia comentarios cuyo ticket ya no existe para evitar comentarios huérfanos.
  - `seed_data(session)`: garantiza usuarios demo y tickets iniciales.
- `app.include_router(auth.router)` y `tickets.router`: “enchufan” las rutas específicas.
- `app.mount("/", StaticFiles(...))`: sirve `frontend/index.html` cuando entras a `http://localhost:8000`.

---

### 4. Base de datos: `db.py` (SQLite + SQLModel)

Archivo: `backend/app/db.py`

Responsabilidades:

- Crear el `engine` de SQLAlchemy/SQLModel apuntando a `app.db`.
- Activar `PRAGMA foreign_keys=ON` en SQLite.
- Exponer funciones para crear tablas y obtener una sesión de BD.

Elementos importantes:

- `BASE_DIR` y `DB_PATH`: construyen la ruta absoluta al archivo `app.db` en la raíz del proyecto.
- `engine = create_engine(DATABASE_URL, ...)`: objeto que maneja la conexión.
- Decorador `@event.listens_for(engine, "connect")`:
  - Ejecuta `PRAGMA foreign_keys=ON` al conectar, para que SQLite respete las claves foráneas.
- `init_db()`:
  - Importa los modelos (`from . import models`) para registrar todas las tablas.
  - `SQLModel.metadata.create_all(bind=engine)`: crea las tablas si faltan.
- `get_session()`:
  - Función generadora que devuelve una `Session` de SQLModel para usarla como dependencia en FastAPI (`Depends(get_db)`).

---

### 5. Modelos de dominio (`models/`)

En Python usamos SQLModel para definir tablas con anotaciones de tipo.

#### 5.1 `models/user.py` – usuarios

- `UserRole(str, Enum)`: enum con valores `"USER"` y `"AGENT"`.
- `UserBase(SQLModel)`:
  - `email: str`
  - `full_name: str | None`
  - `role: UserRole`
  - `is_active: bool`
- `User(UserBase, table=True)`:
  - `id: Optional[int] = Field(..., primary_key=True)`
  - `hashed_password: str`
  - `created_at: datetime` (se rellena automáticamente).

Este modelo se corresponde con la tabla `user` en SQLite.

#### 5.2 `models/ticket.py` – tickets

- `TicketPriority(str, Enum)`: `LOW`, `MEDIUM`, `HIGH`.
- `TicketStatus(str, Enum)`: `OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`.
- `TicketBase(SQLModel)`:
  - `title`, `description`, `priority`, `status`.
- `Ticket(TicketBase, table=True)`:
  - `id`: PK.
  - `created_by_id`: FK a `user.id`.
  - `assigned_to_id`: FK opcional a `user.id` (agente asignado).
  - `created_at`, `updated_at`: fechas de creación/actualización.

#### 5.3 `models/comment.py` – comentarios

- `CommentBase(SQLModel)`:
  - `content: str`
- `Comment(CommentBase, table=True)`:
  - `id`: PK.
  - `ticket_id`: FK a `ticket.id`.
  - `author_id`: FK a `user.id`.
  - `created_at`: fecha de creación.

#### 5.4 `models/__init__.py` – “barrel” de modelos

Este archivo expone los modelos principales desde un solo sitio:

- `from .user import User, UserRole`
- `from .ticket import Ticket, TicketPriority, TicketStatus`
- `from .comment import Comment`
- `__all__ = [...]`

Gracias a esto se puede importar con:

```python
from app.models import User, Ticket
```

en lugar de `from app.models.user import User`, etc.

---

### 6. Schemas / DTOs (`schemas/`)

Los `schemas` definen **cómo son los datos que entran y salen** por la API (JSON). No son tablas, sino clases Pydantic que se usan en `request` y `response`.

#### 6.1 `schemas/auth.py`

Define:

- `LoginRequest`: JSON esperado en `/api/auth/login`:
  - `email: EmailStr`
  - `password: constr(min_length=8)`
- `Token`:
  - `access_token: str`
  - `token_type: str = "bearer"`
- `UserCreate`: para registro (en este proyecto es opcional):
  - `email`, `full_name`, `password`, `role`.
- `UserRead`: cómo se devuelve un usuario desde la API:
  - `id`, `email`, `full_name`, `role`, `is_active`, `created_at`.

#### 6.2 `schemas/ticket.py`

- `TicketCreate`: cuerpo de `POST /api/tickets`:
  - `title`, `description`, `priority`.
- `TicketUpdate`: campos opcionales que se pueden modificar con `PATCH`:
  - `status`, `priority`, `assigned_to_id` (en este diseño solo para AGENT).
- `TicketRead`: respuesta estándar de ticket:
  - `id`, `title`, `description`, `priority`, `status`
  - `created_by_id`, `assigned_to_id`
  - `created_at`, `updated_at`
  - `created_by_email`, `assigned_to_email` (para mostrar emails en el frontend).
- `PaginatedTickets`:
  - `items`: lista de `TicketRead`
  - `total`, `page`, `page_size`, `filters`.

#### 6.3 `schemas/comment.py`

- `CommentCreate`: JSON con `content: str`.
- `CommentRead`: lo que se devuelve al listar/crear comentarios:
  - `id`, `ticket_id`, `author_id`, `author_email`, `content`, `created_at`.

---

### 7. Configuración y seguridad (`core/`)

#### 7.1 `core/config.py`

- `Settings(BaseModel)`:
  - `app_name`
  - `secret_key` (clave para firmar JWT)
  - `algorithm` (HS256)
  - `access_token_expire_minutes`
  - `cors_origins`
- `settings = Settings()`:
  - Instancia única usada por el resto del código (`settings.app_name`, etc.).

#### 7.2 `core/security.py`

Responsable de:

- Hashing de contraseñas.
- Creación y decodificación de tokens JWT.

Puntos clave:

- `pwd_context = CryptContext(schemes=["pbkdf2_sha256"], ...)`:
  - Se usa `pbkdf2_sha256` en lugar de `bcrypt` porque en tu instalación concreta de Python 3.14 `bcrypt` daba problemas. A nivel de seguridad es un algoritmo robusto y estándar.
- `get_password_hash(password: str) -> str`:
  - Recibe una contraseña en texto plano y devuelve su hash.
- `verify_password(plain_password, hashed_password)`:
  - Compara contraseña introducida con el hash de la BD.
- `create_access_token(data, expires_delta)`:
  - Añade `exp` al payload.
  - Firma el token con `settings.secret_key` y `settings.algorithm`.
- `decode_access_token(token)`:
  - Devuelve el payload si el token es válido; lanza error si no lo es.

---

### 8. Dependencias de seguridad (`deps.py`)

Archivo: `backend/app/deps.py`

Aquí se definen funciones que FastAPI usa como **dependencias** (`Depends(...)`) para:

- Obtener la sesión de BD.
- Obtener el usuario actual a partir del token.
- Asegurar que el usuario es AGENT.

Funciones:

- `get_db()`:
  - Devuelve una sesión de BD usando `get_session()` de `db.py`.
- `get_current_user(token=Depends(oauth2_scheme), db=Depends(get_db))`:
  - Lee el token JWT del header `Authorization: Bearer ...`.
  - Lo decodifica (`decode_access_token`).
  - Busca el usuario por email.
  - Lanza `HTTPException(401)` si algo falla.
- `get_current_active_user(current_user=Depends(get_current_user))`:
  - Verifica `is_active`.
- `get_current_agent(current_user=Depends(get_current_active_user))`:
  - Verifica `role == AGENT`.

Estas dependencias se usan en muchos endpoints para protegerlos:

- Ejemplo: `export_tickets_excel` depende de `get_current_agent`, así que solo un AGENT puede entrar.

---

### 9. Rutas de autenticación (`routers/auth.py`)

Archivo: `backend/app/routers/auth.py`

Define `/api/auth/...`:

- `POST /api/auth/register` (opcional):
  - Crea un nuevo usuario en BD a partir de `UserCreate`.
  - Hash de contraseña con `get_password_hash`.
  - Devuelve `UserRead`.
- `POST /api/auth/login`:
  - Recibe `LoginRequest` (email + password).
  - Busca usuario por email.
  - Verifica contraseña con `verify_password`.
  - Crea un token JWT (`create_access_token`) con `sub = user.email`.
  - Devuelve `Token` con `access_token`.
- `GET /api/auth/me`:
  - Usa `get_current_user_read` para devolver información del usuario autenticado.

---

### 10. Rutas de tickets y comentarios (`routers/tickets.py`)

Archivo: `backend/app/routers/tickets.py`

Todas las rutas bajo `/api/tickets`.

#### 10.1 `_tickets_query(...)`

Función interna que construye un `select(Ticket)` con filtros:

- Si el usuario es `USER`, filtra por `created_by_id == current_user.id`.
- Aplica filtros opcionales de `status`, `priority` y `search` en título/descripción.

Se reutiliza tanto para listado como para conteo.

#### 10.2 `POST /api/tickets`

```python
@router.post("", response_model=TicketRead, status_code=201)
def create_ticket(..., current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.USER:
        raise HTTPException(403, "Solo usuarios finales (USER) pueden crear tickets")
    ...
```

- Solo un `USER` puede crear tickets.
- Usa `TicketCreate` para validar campos de entrada.

#### 10.3 `GET /api/tickets` (listado con filtros y paginación)

- Usa `_tickets_query` para aplicar reglas de visibilidad y filtros.
- Calcula `total` con una query de count (adaptado a SQLAlchemy 2.0).
- Devuelve `PaginatedTickets` con:
  - `items`: lista de `TicketRead` (cada uno incluye correos en `created_by_email` y `assigned_to_email` al leer detalle individual).

#### 10.4 `GET /api/tickets/{id}`

- Carga ticket por ID (`_get_ticket_or_404`).
- Verifica permisos (`_ensure_can_access_ticket`).
- Construye `TicketRead` añadiendo también:
  - `created_by_email`
  - `assigned_to_email`

Así el frontend puede mostrar emails en lugar de IDs.

#### 10.5 `PATCH /api/tickets/{id}`

- Solo **AGENT** puede modificar tickets (estado, prioridad, asignación).
- Valida:
  - Si se envía `assigned_to_id`, ese usuario debe existir y ser AGENT.
- Actualiza `updated_at`.

Esto se invoca en dos casos desde el frontend:

- Botón **“Guardar cambios”**: actualiza estado + prioridad.
- Botón **“Asignarme ticket”**: solo cambia `assigned_to_id`.

#### 10.6 `DELETE /api/tickets/{id}`

- Solo AGENT.
- Borra ticket y **sus comentarios** (para no dejar comentarios huérfanos).

#### 10.7 Comentarios

- `POST /api/tickets/{id}/comments`:
  - Creador del ticket o AGENT puede comentar.
  - Crea `Comment` asociado a ticket + author.
  - Devuelve `CommentRead` con `author_email`.
- `GET /api/tickets/{id}/comments`:
  - Devuelve lista de comentarios con `author_email` resuelto.

#### 10.8 Exportar tickets a Excel (solo AGENT)

- Ruta: `GET /api/tickets/export`.
- Usa **openpyxl** para generar un `.xlsx` con:
  - ID, Título, Descripción.
  - Prioridad, Estado.
  - ID + email de creador y asignado.
  - Fechas de creación y actualización.
- Devuelve un `Response` con `Content-Disposition: attachment; filename="tickets_YYYYMMDD_HHMMSS.xlsx"`.

---

### 11. Semillas (`services/seed.py`)

Archivo: `backend/app/services/seed.py`

Responsabilidad: garantizar que, al arrancar la app, hay:

- Usuarios demo:
  - `user@demo.com` (USER principal).
  - `user1@demo.com` (USER secundario).
  - `agent@demo.com` (AGENT).
- Tickets demo si no hay ninguno.

Puntos clave:

- Función privada `_get_or_create_user`:
  - Busca por email, si existe lo devuelve.
  - Si no, crea un nuevo usuario con contraseña `Demo1234!`.
- En `seed_data`:
  - Llama a `_get_or_create_user` para cada usuario demo (idempotente).
  - Si no existen tickets, crea 3 para `user@demo.com` y 1 para `user1@demo.com`.

---

### 12. Frontend (SPA) – `frontend/`

Archivos:

- `index.html`: estructura HTML principal (login, dashboard, panel detalle, modal de nuevo ticket).
- `styles.css`: estilos (modo oscuro moderno, paneles, tablas, badges, responsive).
- `app.js`: lógica de la SPA (login, llamadas a la API, estado, interacción).

#### 12.1 `index.html`

Organización:

- **Header**:
  - Título “Portal de Incidencias”.
  - Info del usuario logeado (email + role + botón cerrar sesión).
- **Sección login**:
  - Formulario de email + password.
  - Ayudas con credenciales demo (user, user1, agent).
- **Dashboard**:
  - Columna izquierda:
    - Cabecera con título “Tickets”.
    - Botones:
      - `Crear ticket` (solo USER).
      - `Exportar a Excel` (solo AGENT).
    - Filtros (estado, prioridad, búsqueda).
    - Tabla con:
      - ID, Título, Prioridad, Estado, Creado, Asignado a.
    - Paginación anterior/siguiente.
  - Columna derecha (panel de detalle):
    - Botón `×` para cerrar detalle.
    - Título, badges de prioridad/estado, descripción.
    - Meta:
      - “Creado por” (email).
      - “Asignado a” (email).
      - Fechas se han ocultado en UI para limpiar, pero se siguen almacenando en backend/Excel.
    - Panel de gestión para AGENT:
      - Select de estado.
      - Select de prioridad.
      - Botón `Asignarme ticket`.
      - Botón `Guardar cambios`.
      - Botón `Eliminar`.
    - Panel de comentarios:
      - Lista de comentarios (minichat USER–AGENT).
      - Autor (Usuario/Agente + email).
      - Fecha y contenido.
      - Textarea para nuevo comentario + botón “Añadir comentario”.
- **Modal nuevo ticket**:
  - Título, descripción, prioridad.
  - Botones “Crear” y “Cancelar”.

#### 12.2 `styles.css`

Características:

- Tema oscuro tipo panel (gradientes suaves, sombras).
- Layout con dos columnas (tickets + detalle), responsive a una columna en pantallas pequeñas.
- Estilos de:
  - Botones (`btn-primary`, `btn-secondary`, `btn-danger`).
  - Badges para prioridad y estado (`badge priority-HIGH`, etc.).
  - Tabla de tickets con highlight al pasar el ratón y al seleccionar.
  - Comentarios con estilos diferenciados (autor, fecha, contenido).
  - Spinner de carga global y toasts de notificación.

#### 12.3 `app.js` – lógica de la SPA

Puntos importantes:

- Variables globales:
  - `accessToken`, `currentUser`, `currentPage`, `pageSize`, `currentTicket`.
- Helper `$` para buscar elementos por ID.
- Funciones clave:
  - `apiFetch(path, options)`: wrapper sobre `fetch`:
    - Añade `Authorization: Bearer ...` si hay token.
    - Maneja errores 401 (cierra sesión).
    - Intenta parsear JSON.
  - `handleLogin(e)`:
    - Hace `POST /api/auth/login`.
    - Guarda token en `localStorage`.
    - Carga usuario, oculta login, muestra dashboard, resetea filtros y carga tickets.
  - `loadCurrentUser()`:
    - Llama a `/api/auth/me`.
    - Muestra email y rol.
    - Decide si mostrar botón `Crear ticket` (USER) o `Exportar a Excel` (AGENT).
  - `loadTickets(page)`:
    - Aplica filtros y paginación.
    - Llama a `/api/tickets`.
    - Rellena tabla.
  - `loadTicketDetail(ticketId)`:
    - Llama a `/api/tickets/{id}`.
    - Muestra título, descripción, badges.
    - Muestra `created_by_email` / `assigned_to_email`.
    - Si rol = AGENT, muestra panel de gestión.
  - `loadComments(ticketId)`:
    - Llama a `/api/tickets/{id}/comments`.
    - Construye minichat con autor (Usuario/Agente + email) y fecha.
  - `handleSaveAgentEdit()`:
    - Solo AGENT.
    - Envía estado + prioridad a `PATCH /api/tickets/{id}`.
  - `handleAssignToMe()`:
    - Solo AGENT.
    - Envía solo `assigned_to_id` (no guarda posibles cambios en estado/prioridad).
  - `handleAddComment()`:
    - Envía nuevo comentario a `/api/tickets/{id}/comments`.
  - `handleExportTickets()`:
    - Llama a `/api/tickets/export`.
    - Descarga un `.xlsx` con todos los tickets.
  - `handleCreateTicket()`:
    - Solo USER.
    - Crea ticket, resetea filtros, recarga página 1, resalta la fila del nuevo ticket.
  - `clearTicketSelection()`:
    - Limpia selección de tabla y oculta panel de detalle.
  - `bootstrap()`:
    - Asocia todos los event listeners.
    - Si hay token en `localStorage`, intenta restaurar sesión automáticamente.

---

### 13. Decisiones importantes de diseño

- **FastAPI + SQLModel**:
  - Facilita una estructura clara de modelos y schemas con tipado fuerte.
- **JWT**:
  - Permite autenticación stateless entre frontend y backend.
- **Roles USER vs AGENT**:
  - Se simplifica la lógica: USER solo ve/crea sus tickets, AGENT gestiona todos.
- **Comentarios como “mini chat”**:
  - Facilita que USER y AGENT vayan dejando trazabilidad sin tocar la descripción original del ticket.
- **SQLite como archivo `app.db`**:
  - Sencillo para desarrollo y pruebas; fácil de entregar.
- **Exportación a Excel**:
  - Útil para el rol AGENT, y demuestra integración con generación de ficheros binarios desde FastAPI.
- **Separación frontend/backend clara**:
  - Backend expone una API limpia.
  - Frontend consume esa API y gestiona estado en una sola página (SPA sencilla sin framework).

---

### 14. Cómo ejecutar y probar

1. Crear y activar entorno virtual (opcional pero recomendado).
2. Instalar dependencias: `pip install -r requirements.txt`.
3. Ejecutar: `uvicorn backend.app.main:app --reload`.
4. Abrir `http://localhost:8000` y probar con:
   - `user@demo.com` / `Demo1234!`
   - `user1@demo.com` / `Demo1234!`
   - `agent@demo.com` / `Demo1234!`

Se recomienda también probar los endpoints desde `/docs` (Swagger) y el archivo `requests.http`.

