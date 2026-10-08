# Entity-Relationship (ER) Diagram

This document illustrates the complete PostgreSQL database schema design for the **Multi-Tenant Project & Workflow Management Platform**.

## Schema Overview

The architecture enforces multi-tenancy at the relational level:
- **`organizations`** represents each isolated tenant.
- **`organization_members`** establishes tenant memberships with role assignment (`ORGANIZATION_ADMIN`, `PROJECT_MANAGER`, `TEAM_MEMBER`, `VIEWER`).
- All primary business entities (**`projects`**, **`tasks`**, **`comments`**, **`attachments`**, **`notifications`**, **`audit_logs`**) carry foreign keys to `organizations(id)` with cascading deletes and composite unique indexes to guarantee total isolation.

---

## Mermaid ER Diagram

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : "issues"
    USERS ||--o{ ORGANIZATION_MEMBERS : "belongs to"
    USERS ||--o{ PROJECT_MEMBERS : "participates in"
    USERS ||--o{ PROJECTS : "owns"
    USERS ||--o{ TASKS : "reports / assigned to"
    USERS ||--o{ COMMENTS : "authors"
    USERS ||--o{ ATTACHMENTS : "uploads"
    USERS ||--o{ NOTIFICATIONS : "receives"
    USERS ||--o{ AUDIT_LOGS : "triggers"

    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : "enrolls"
    ORGANIZATIONS ||--o{ PROJECTS : "scopes"
    ORGANIZATIONS ||--o{ TASKS : "isolates"
    ORGANIZATIONS ||--o{ COMMENTS : "contains"
    ORGANIZATIONS ||--o{ ATTACHMENTS : "stores"
    ORGANIZATIONS ||--o{ NOTIFICATIONS : "channels"
    ORGANIZATIONS ||--o{ AUDIT_LOGS : "audits"

    PROJECTS ||--o{ PROJECT_MEMBERS : "contains"
    PROJECTS ||--o{ TASKS : "organizes"
    PROJECTS ||--o{ COMMENTS : "attaches"
    PROJECTS ||--o{ ATTACHMENTS : "files"

    TASKS ||--o{ TASK_DEPENDENCIES : "depends on (dependent)"
    TASKS ||--o{ TASK_DEPENDENCIES : "prerequisite for"
    TASKS ||--o{ COMMENTS : "receives"
    TASKS ||--o{ ATTACHMENTS : "contains"

    USERS {
        int id PK
        string email UK
        string username UK
        string hashed_password
        string full_name
        boolean is_active
        boolean is_super_admin
        datetime created_at
        datetime updated_at
    }

    REFRESH_TOKENS {
        int id PK
        int user_id FK
        string jti UK
        datetime expires_at
        boolean is_revoked
        datetime created_at
    }

    ORGANIZATIONS {
        int id PK
        string name
        string slug UK
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    ORGANIZATION_MEMBERS {
        int id PK
        int organization_id FK
        int user_id FK
        string role "ORGANIZATION_ADMIN | PROJECT_MANAGER | TEAM_MEMBER | VIEWER"
        boolean is_active
        datetime joined_at
    }

    PROJECTS {
        int id PK
        int organization_id FK
        int owner_id FK
        string name
        text description
        string status "PLANNING | ACTIVE | ON_HOLD | COMPLETED | ARCHIVED"
        datetime start_date
        datetime due_date
        datetime created_at
        datetime updated_at
    }

    PROJECT_MEMBERS {
        int id PK
        int project_id FK
        int user_id FK
        datetime joined_at
    }

    TASKS {
        int id PK
        int organization_id FK
        int project_id FK
        string title
        text description
        int assignee_id FK "nullable"
        int reporter_id FK
        string priority "LOW | MEDIUM | HIGH | URGENT"
        string status "BACKLOG | TODO | IN_PROGRESS | BLOCKED | REVIEW | DONE | CANCELLED"
        datetime due_date
        numeric estimated_hours
        numeric actual_hours
        datetime created_at
        datetime updated_at
    }

    TASK_DEPENDENCIES {
        int id PK
        int task_id FK "Dependent Task"
        int depends_on_task_id FK "Prerequisite Task"
        datetime created_at
    }

    COMMENTS {
        int id PK
        int organization_id FK
        int user_id FK
        int project_id FK "nullable"
        int task_id FK "nullable"
        text content
        datetime created_at
        datetime updated_at
    }

    ATTACHMENTS {
        int id PK
        int organization_id FK
        int uploaded_by FK
        int project_id FK "nullable"
        int task_id FK "nullable"
        string file_name
        int file_size
        string mime_type
        string storage_path
        datetime created_at
    }

    NOTIFICATIONS {
        int id PK
        int user_id FK
        int organization_id FK
        string event_type
        string title
        text message
        boolean is_read
        string entity_type
        int entity_id
        datetime created_at
    }

    AUDIT_LOGS {
        int id PK
        int organization_id FK
        int user_id FK "nullable"
        string action
        string entity_type
        int entity_id "nullable"
        string ip_address
        text details "JSON"
        datetime timestamp
    }
```

---

## Key Constraints & Invariants

1. **Multi-Tenant Data Isolation**:
   - `tasks.organization_id == projects.organization_id`
   - Every individual resource lookup queries with `organization_id == active_tenant_id`.
   - Modifying entity IDs across organizations returns `404 Not Found` or `403 Forbidden`.

2. **Composite Unique Constraints**:
   - `organization_members`: `UNIQUE(organization_id, user_id)` (A user can join an organization only once).
   - `project_members`: `UNIQUE(project_id, user_id)` (A user cannot be duplicated in the same project).
   - `task_dependencies`: `UNIQUE(task_id, depends_on_task_id)` (Prevents redundant dependency links).

3. **Cascading & Referential Integrity**:
   - `ondelete="CASCADE"` on organizations cleanly wipes child projects, tasks, comments, files, and audit records when an organization is purged.
   - `ondelete="SET NULL"` on `tasks.assignee_id` preserves tasks when a user is deactivated or removed.
   - `ondelete="CASCADE"` on `task_dependencies` ensures dependent links are cleanly removed when prerequisite tasks are deleted.
