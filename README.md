# Multi-Tenant Project & Workflow Management Platform (Backend)

A secure, scalable, enterprise-grade multi-tenant project and workflow management backend built with **Python**, **FastAPI**, **SQLAlchemy**, **PostgreSQL**, **Alembic**, and **Pydantic**.

---

## 🌟 Highlights & Capabilities

- **Strict Multi-Tenant Isolation**: Organizations are fully isolated. Users in one organization can never access, query, or modify resources belonging to another organization. URL ID tampering is strictly blocked.
- **Dual-Layer Authorization**: Enforces both Role-Based Access Control (**RBAC**) and Resource-Based Authorization across 5 roles: `Super Admin`, `Organization Admin`, `Project Manager`, `Team Member`, and `Viewer`.
- **JWT Authentication & Token Rotation**: Secure password hashing (`bcrypt`), access tokens, refresh token storage, and automatic token rotation on refresh. Inactive users are immediately locked out.
- **Workflow State Machines**: Strict status transitions for Projects and Tasks. Invalid transitions are rejected with detailed API errors.
- **Task Dependencies & Cycle Prevention**: Tasks can depend on prerequisite tasks. Dependent tasks cannot progress to active states until prerequisites are completed. Graph cycle detection prevents circular dependencies.
- **File Upload Security & Magic Byte Inspection**: Upload validation verifies MIME types, file sizes, and binary magic bytes (PDF, PNG, JPEG, ZIP, DOCX, XLSX, text). Client-supplied file extensions are never trusted blindly.
- **Comments & `@username` Mentions**: Rich discussion threads with automatic regex parsing of mentions that trigger instant notifications.
- **Real-Time WebSocket Notifications**: Live notification delivery over WebSockets with REST fallback endpoints.
- **Role-Specific Dashboards**: Tailored metrics and analytics for Organization Admins, Project Managers, and Team Members.
- **Immutable Audit Logging**: Automatic recording of all security, project, task, member, and file actions with IP address and metadata tracking.
- **Clean Architecture**: Clear separation of concerns:
  `Routes -> Dependencies -> Services -> Repositories -> Models -> Database`.

---

## 📁 Repository Structure

```
muilt_tenant_project/
├── app/
│   ├── api/
│   │   ├── dependencies.py          # Auth, Tenant Context, RBAC Dependencies
│   │   └── v1/
│   │       ├── api_router.py        # Central Router
│   │       └── endpoints/           # Individual Route Handlers
│   │           ├── auth.py          # Register, Login, Refresh, Logout, Me
│   │           ├── organizations.py # Org CRUD, Members, Roles, Status
│   │           ├── projects.py      # Projects CRUD, Archive, Members
│   │           ├── tasks.py         # Task CRUD, Assign, Status, Dependencies
│   │           ├── comments.py      # Comments & Mentions
│   │           ├── files.py         # File Uploads, Downloads, Validation
│   │           ├── notifications.py # Notification Listing & Read Marks
│   │           ├── dashboard.py     # Role-based Dashboard Analytics
│   │           ├── audit_logs.py    # Activity & Audit Logs
│   │           └── websockets.py    # Real-Time WebSocket Push
│   ├── core/
│   │   ├── config.py                # Pydantic Settings & Environment
│   │   ├── security.py              # JWT Encoding & Bcrypt Password Hashing
│   │   ├── exceptions.py            # Custom Exception Classes & Status Codes
│   │   ├── response.py              # Standardized API Response Envelopes
│   │   └── websocket_manager.py     # Active WebSocket Connection Manager
│   ├── db/
│   │   ├── session.py               # Engine & Sessionmaker
│   │   └── init_db.py               # Initial Database Seeder
│   ├── models/                      # SQLAlchemy ORM Models
│   │   ├── enums.py                 # System Enums (Roles, Statuses, Actions)
│   │   ├── user.py                  # User Model
│   │   ├── refresh_token.py         # Refresh Token Rotation Model
│   │   ├── organization.py          # Tenant Organization Model
│   │   ├── organization_member.py   # Membership & Role Mapping
│   │   ├── project.py               # Project Model
│   │   ├── project_member.py        # Project Participant Mapping
│   │   ├── task.py                  # Task Model
│   │   ├── task_dependency.py       # Prerequisite Dependency Mapping
│   │   ├── comment.py               # Comment Model
│   │   ├── attachment.py            # File Attachment Model
│   │   ├── notification.py          # Notification Alert Model
│   │   └── audit_log.py             # Immutable Activity Trail Model
│   ├── schemas/                     # Pydantic Schemas (DTOs)
│   ├── repositories/                # Data Access Layer (Clean Architecture)
│   ├── services/                    # Business Logic Layer (Clean Architecture)
│   └── main.py                      # FastAPI Application Entrypoint
├── alembic/                         # Database Migration Scripts
├── tests/                           # Automated Pytest Test Suite
│   ├── conftest.py                  # Test Fixtures & In-Memory Isolation
│   ├── test_auth.py                 # Authentication Tests
│   ├── test_multi_tenancy.py        # Tenant Isolation & Tampering Tests
│   ├── test_organizations.py        # Organization & Membership Tests
│   ├── test_projects.py             # Project CRUD & Transition Tests
│   ├── test_tasks.py                # Task CRUD & Assignment Rule Tests
│   ├── test_task_workflow.py        # Workflow State Machine Tests
│   ├── test_task_dependencies.py    # Dependencies & Cycle Detection Tests
│   ├── test_comments_mentions.py    # Comments & Mentions Tests
│   ├── test_files.py                # File Validation & Magic Byte Tests
│   └── test_dashboard.py            # Role Dashboard Metrics Tests
├── uploads/                         # Tenant-Isolated File Upload Storage
├── Dockerfile                       # Multi-Stage Production Container
├── docker-compose.yml               # PostgreSQL, Redis & FastAPI Services
├── requirements.txt                 # Python Dependencies
├── postman_collection.json          # Complete Postman Test Collection
├── ER_DIAGRAM.md                    # Database ER Diagram & Invariants
├── ARCHITECTURE.md                  # Clean Architecture & Flow Diagrams
└── README.md                        # Documentation & Setup Guide
```

---

## 🚀 Quickstart & Setup Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- PostgreSQL (or use the included `docker-compose.yml`)

### Option 1: Running Locally with Python

1. **Clone and Navigate into the Project**:
   ```bash
   cd muilt_tenant_project
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Adjust DATABASE_URL in .env if needed (default: postgresql://postgres@localhost:5433/multitenant_pm)
   ```

5. **Run Migrations & Seed Sample Data**:
   ```bash
   python -m alembic upgrade head
   python -m app.db.init_db
   ```

6. **Start the FastAPI Development Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Access the Interactive API Docs**:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Option 2: Running with Docker Compose

To start the complete environment (FastAPI Backend, PostgreSQL, Redis) with a single command:

```bash
docker-compose up --build
```

The service will automatically:
1. Initialize the PostgreSQL database container.
2. Run database migrations via Alembic.
3. Seed default users, organizations, and sample tasks.
4. Expose the API at `http://localhost:8000`.

---

## 🧪 Running Automated Tests

The test suite covers positive scenarios, negative edge cases, authorization restrictions, and multi-tenant isolation.

```bash
python -m pytest tests/ -v
```

### Coverage Highlights:
- **Authentication**: Registration, Login, Token Expiry, Token Rotation, Password Change.
- **Multi-Tenant Isolation**: Cross-tenant project access rejection, ID tampering prevention, cross-tenant dashboard/file isolation.
- **Organizations**: Role management, member activation/deactivation, duplicate prevention.
- **Projects**: Status transitions, member association, owner/admin deletion permissions.
- **Tasks**: Assignment rules (viewers cannot be assigned, members must belong to project), priority changes.
- **Task Workflow**: Valid progression (`TODO -> IN_PROGRESS -> REVIEW -> DONE`), invalid skips (`TODO -> DONE`).
- **Dependencies**: Cycle detection (DFS), prerequisite gating (cannot start until prerequisite is done).
- **Files**: Magic bytes verification (`%PDF-`, `PNG`, `JPEG`, `ZIP/DOCX`), fake extension rejection.
- **Comments & Mentions**: `@username` detection and recipient notification dispatch.
- **Dashboards**: Org Admin, PM, and Team Member metrics computation.

---

## 🔑 Default Seeded Accounts

For testing and demonstration, the database comes pre-seeded with the following credentials:

| Role | Username | Email | Password | Organization |
|---|---|---|---|---|
| **Super Admin** | `superadmin` | `superadmin@example.com` | `SuperAdmin@123` | Platform-Wide |
| **Org Admin** | `acme_admin` | `admin@acme.com` | `Admin@123` | Acme Corporation |
| **Project Manager** | `acme_pm` | `pm@acme.com` | `Manager@123` | Acme Corporation |
| **Team Member** | `alice` | `alice@acme.com` | `Alice@123` | Acme Corporation |
| **Team Member** | `bob` | `bob@acme.com` | `Bob@123` | Acme Corporation |
| **Viewer** | `viewer` | `viewer@acme.com` | `Viewer@123` | Acme Corporation |
| **Other Tenant Admin** | `charlie` | `charlie@beta.com` | `Charlie@123` | Beta Innovations |

---

## 📡 API Overview & Endpoints

### 1. Authentication (`/api/v1/auth`)
- `POST /register`: Register a new user account.
- `POST /login`: Authenticate and receive access & refresh JWTs.
- `POST /refresh`: Rotate refresh token and receive a new access token.
- `POST /logout`: Invalidate active refresh token.
- `GET  /me`: Return current user profile and organization memberships.
- `POST /change-password`: Update account password.

### 2. Organizations (`/api/v1/organizations`)
- `POST /`: Create a new organization (creator becomes Organization Admin).
- `GET  /`: List organizations the authenticated user belongs to.
- `GET  /{org_id}`: Retrieve organization details.
- `PUT  /{org_id}`: Update organization metadata.
- `POST /{org_id}/members`: Add a user to an organization with a specific role.
- `DELETE /{org_id}/members/{user_id}`: Remove member from organization.
- `PATCH /{org_id}/members/{user_id}/role`: Change member role.
- `PATCH /{org_id}/members/{user_id}/status`: Activate or deactivate a member.
- `GET  /{org_id}/members`: List organization members with server-side pagination.

### 3. Projects (`/api/v1/projects`)
- `POST /`: Create project in the active tenant.
- `GET  /`: List projects with filters (`status`, `search`, `owner_id`) and pagination.
- `GET  /{id}`: Get project details with member and task counts.
- `PUT  /{id}`: Update project metadata or status (enforces valid transitions).
- `PATCH /{id}/archive`: Archive project.
- `DELETE /{id}`: Delete project (restricted to Org Admin and Project Owner).
- `POST /{id}/members`: Add member to project.
- `DELETE /{id}/members/{user_id}`: Remove member from project.
- `GET  /{id}/members`: List project members.

### 4. Tasks (`/api/v1/tasks`)
- `POST /`: Create task.
- `GET  /`: List tasks with filters (`project_id`, `status`, `priority`, `assignee_id`, `search`) and pagination.
- `GET  /{id}`: Retrieve task details with dependencies.
- `PUT  /{id}`: Update task title, description, or hours.
- `PATCH /{id}/status`: Transition task state with workflow and dependency checks.
- `PATCH /{id}/assign`: Assign task (validates project membership and non-viewer role).
- `PATCH /{id}/priority`: Change priority (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).
- `POST /{id}/dependencies`: Link prerequisite task (prevents circular dependencies).
- `DELETE /{id}/dependencies/{dep_id}`: Remove dependency link.
- `GET  /{id}/dependencies`: List all prerequisites.

### 5. Comments & Mentions (`/api/v1/comments`)
- `POST /`: Add comment to project or task (triggers `@username` notifications).
- `GET  /`: List comments for a task or project.
- `PUT  /{id}`: Update comment (author or Org Admin).
- `DELETE /{id}`: Delete comment (author or Org Admin).

### 6. Files & Attachments (`/api/v1/files`)
- `POST /upload`: Multipart upload with magic byte inspection and size verification.
- `GET  /{id}`: Retrieve file metadata.
- `GET  /{id}/download`: Secure file streaming download.
- `GET  /`: List files by task or project.
- `DELETE /{id}`: Delete file attachment.

### 7. Notifications & Real-Time (`/api/v1/notifications`, `/api/v1/ws`)
- `GET  /notifications`: List user notifications with unread counts.
- `PATCH /notifications/{id}/read`: Mark notification as read.
- `PATCH /notifications/read-all`: Mark all notifications as read.
- `WS   /ws/notifications`: Real-time WebSocket channel for instant notifications.

### 8. Dashboards (`/api/v1/dashboard`)
- `GET  /stats`: Role-adaptive metrics for Org Admin, Project Manager, or Team Member.

### 9. Audit Logs (`/api/v1/audit-logs`)
- `GET  /`: Filterable immutable activity audit log records.

---

## 📬 Postman Collection

The file [postman_collection.json](file:///c:/muilt_tenant_project/postman_collection.json) provides pre-configured requests with variables (`{{base_url}}`, `{{token}}`, `{{org_id}}`) and auto-token extraction on login.
To use:
1. Open Postman -> Click **Import** -> Select `postman_collection.json`.
2. Send **Login (Acme Admin)** under Authentication — the collection will automatically store the JWT in `{{token}}`.
3. Test any endpoint!
