import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import (
    Base,
    Organization,
    OrganizationMember,
    OrganizationRole,
    Project,
    ProjectMember,
    ProjectStatus,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)

# Use SQLite in-memory with StaticPool for fast, isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    def _headers(user: User, org_id: int = None):
        token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email, "username": user.username, "is_super_admin": user.is_super_admin}
        )
        h = {"Authorization": f"Bearer {token}"}
        if org_id is not None:
            h["X-Organization-ID"] = str(org_id)
        return h

    return _headers


@pytest.fixture
def test_setup(db):
    """
    Sets up two isolated organizations:
    Org 1 (Alpha):
      - admin_user (ORGANIZATION_ADMIN)
      - pm_user (PROJECT_MANAGER)
      - member_user (TEAM_MEMBER)
      - viewer_user (VIEWER)
      - project_alpha (owned by pm_user, members: pm_user, member_user)
    Org 2 (Beta):
      - beta_admin (ORGANIZATION_ADMIN)
      - project_beta
    """
    # Create Users
    admin_user = User(
        email="admin@alpha.com",
        username="alpha_admin",
        hashed_password=hash_password("Password@123"),
        is_active=True,
        is_super_admin=False,
    )
    pm_user = User(
        email="pm@alpha.com",
        username="alpha_pm",
        hashed_password=hash_password("Password@123"),
        is_active=True,
        is_super_admin=False,
    )
    member_user = User(
        email="member@alpha.com",
        username="alpha_member",
        hashed_password=hash_password("Password@123"),
        is_active=True,
        is_super_admin=False,
    )
    viewer_user = User(
        email="viewer@alpha.com",
        username="alpha_viewer",
        hashed_password=hash_password("Password@123"),
        is_active=True,
        is_super_admin=False,
    )
    inactive_user = User(
        email="inactive@alpha.com",
        username="alpha_inactive",
        hashed_password=hash_password("Password@123"),
        is_active=False,
        is_super_admin=False,
    )
    beta_admin = User(
        email="admin@beta.com",
        username="beta_admin",
        hashed_password=hash_password("Password@123"),
        is_active=True,
        is_super_admin=False,
    )
    super_admin = User(
        email="superadmin@root.com",
        username="superadmin",
        hashed_password=hash_password("Password@123"),
        is_active=True,
        is_super_admin=True,
    )

    db.add_all([admin_user, pm_user, member_user, viewer_user, inactive_user, beta_admin, super_admin])
    db.commit()

    # Create Organizations
    org_alpha = Organization(name="Alpha Org", slug="alpha-org", is_active=True)
    org_beta = Organization(name="Beta Org", slug="beta-org", is_active=True)
    db.add_all([org_alpha, org_beta])
    db.commit()

    # Memberships
    m_admin = OrganizationMember(organization_id=org_alpha.id, user_id=admin_user.id, role=OrganizationRole.ORGANIZATION_ADMIN)
    m_pm = OrganizationMember(organization_id=org_alpha.id, user_id=pm_user.id, role=OrganizationRole.PROJECT_MANAGER)
    m_member = OrganizationMember(organization_id=org_alpha.id, user_id=member_user.id, role=OrganizationRole.TEAM_MEMBER)
    m_viewer = OrganizationMember(organization_id=org_alpha.id, user_id=viewer_user.id, role=OrganizationRole.VIEWER)
    m_beta = OrganizationMember(organization_id=org_beta.id, user_id=beta_admin.id, role=OrganizationRole.ORGANIZATION_ADMIN)

    db.add_all([m_admin, m_pm, m_member, m_viewer, m_beta])
    db.commit()

    # Projects
    project_alpha = Project(
        organization_id=org_alpha.id,
        owner_id=pm_user.id,
        name="Alpha Project 1",
        status=ProjectStatus.ACTIVE
    )
    project_beta = Project(
        organization_id=org_beta.id,
        owner_id=beta_admin.id,
        name="Beta Project 1",
        status=ProjectStatus.ACTIVE
    )
    db.add_all([project_alpha, project_beta])
    db.commit()

    # Project Members
    pm_alpha_pm = ProjectMember(project_id=project_alpha.id, user_id=pm_user.id)
    pm_alpha_mem = ProjectMember(project_id=project_alpha.id, user_id=member_user.id)
    db.add_all([pm_alpha_pm, pm_alpha_mem])
    db.commit()

    return {
        "org_alpha": org_alpha,
        "org_beta": org_beta,
        "admin_user": admin_user,
        "pm_user": pm_user,
        "member_user": member_user,
        "viewer_user": viewer_user,
        "inactive_user": inactive_user,
        "beta_admin": beta_admin,
        "super_admin": super_admin,
        "project_alpha": project_alpha,
        "project_beta": project_beta,
    }
