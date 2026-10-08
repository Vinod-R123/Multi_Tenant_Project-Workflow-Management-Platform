from datetime import datetime, timezone, timedelta
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import (
    Base,
    Organization,
    OrganizationMember,
    OrganizationRole,
    Project,
    ProjectMember,
    ProjectStatus,
    Task,
    TaskDependency,
    TaskPriority,
    TaskStatus,
    User,
)


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).filter(User.username == "superadmin").first():
            print("Database already contains seed data.")
            return

        print("Seeding database...")
        now = datetime.now(timezone.utc)

        # 1. Super Admin
        super_admin = User(
            email="superadmin@example.com",
            username="superadmin",
            hashed_password=hash_password("SuperAdmin@123"),
            full_name="Global Super Admin",
            is_active=True,
            is_super_admin=True,
        )
        db.add(super_admin)

        # 2. Org Admin
        org_admin = User(
            email="admin@acme.com",
            username="acme_admin",
            hashed_password=hash_password("Admin@123"),
            full_name="Acme Administrator",
            is_active=True,
            is_super_admin=False,
        )
        db.add(org_admin)

        # 3. Project Manager
        pm = User(
            email="pm@acme.com",
            username="acme_pm",
            hashed_password=hash_password("Manager@123"),
            full_name="Project Manager Dave",
            is_active=True,
            is_super_admin=False,
        )
        db.add(pm)

        # 4. Team Member 1 (Alice)
        alice = User(
            email="alice@acme.com",
            username="alice",
            hashed_password=hash_password("Alice@123"),
            full_name="Alice Developer",
            is_active=True,
            is_super_admin=False,
        )
        db.add(alice)

        # 5. Team Member 2 (Bob)
        bob = User(
            email="bob@acme.com",
            username="bob",
            hashed_password=hash_password("Bob@123"),
            full_name="Bob Engineer",
            is_active=True,
            is_super_admin=False,
        )
        db.add(bob)

        # 6. Viewer
        viewer = User(
            email="viewer@acme.com",
            username="viewer",
            hashed_password=hash_password("Viewer@123"),
            full_name="Victor Viewer",
            is_active=True,
            is_super_admin=False,
        )
        db.add(viewer)

        # 7. Another Organization User (Charlie - Org Beta)
        charlie = User(
            email="charlie@beta.com",
            username="charlie",
            hashed_password=hash_password("Charlie@123"),
            full_name="Charlie Beta",
            is_active=True,
            is_super_admin=False,
        )
        db.add(charlie)

        db.commit()

        # Refresh users
        for u in [super_admin, org_admin, pm, alice, bob, viewer, charlie]:
            db.refresh(u)

        # 8. Create Organizations
        org_acme = Organization(
            name="Acme Corporation",
            slug="acme-corp",
            description="Leading software solutions and agile development",
            is_active=True,
        )
        org_beta = Organization(
            name="Beta Innovations",
            slug="beta-innovations",
            description="Next-gen robotics and IoT company",
            is_active=True,
        )
        db.add_all([org_acme, org_beta])
        db.commit()
        db.refresh(org_acme)
        db.refresh(org_beta)

        # 9. Add Organization Members
        members = [
            OrganizationMember(organization_id=org_acme.id, user_id=org_admin.id, role=OrganizationRole.ORGANIZATION_ADMIN),
            OrganizationMember(organization_id=org_acme.id, user_id=pm.id, role=OrganizationRole.PROJECT_MANAGER),
            OrganizationMember(organization_id=org_acme.id, user_id=alice.id, role=OrganizationRole.TEAM_MEMBER),
            OrganizationMember(organization_id=org_acme.id, user_id=bob.id, role=OrganizationRole.TEAM_MEMBER),
            OrganizationMember(organization_id=org_acme.id, user_id=viewer.id, role=OrganizationRole.VIEWER),
            OrganizationMember(organization_id=org_beta.id, user_id=charlie.id, role=OrganizationRole.ORGANIZATION_ADMIN),
        ]
        db.add_all(members)
        db.commit()

        # 10. Create Projects
        proj_cloud = Project(
            organization_id=org_acme.id,
            owner_id=pm.id,
            name="Cloud Migration Project",
            description="Migrate legacy on-prem services to Kubernetes and AWS cloud infrastructure",
            status=ProjectStatus.ACTIVE,
            start_date=now - timedelta(days=10),
            due_date=now + timedelta(days=45),
        )
        proj_beta = Project(
            organization_id=org_beta.id,
            owner_id=charlie.id,
            name="Beta Autonomous Robot",
            description="Firmware and ROS2 package for prototype rover",
            status=ProjectStatus.ACTIVE,
            start_date=now - timedelta(days=5),
            due_date=now + timedelta(days=30),
        )
        db.add_all([proj_cloud, proj_beta])
        db.commit()
        db.refresh(proj_cloud)
        db.refresh(proj_beta)

        # Project Members
        db.add_all([
            ProjectMember(project_id=proj_cloud.id, user_id=pm.id),
            ProjectMember(project_id=proj_cloud.id, user_id=alice.id),
            ProjectMember(project_id=proj_cloud.id, user_id=bob.id),
            ProjectMember(project_id=proj_beta.id, user_id=charlie.id),
        ])
        db.commit()

        # 11. Create Tasks with Dependencies
        # Task A: Setup VPC & Networking
        task_a = Task(
            organization_id=org_acme.id,
            project_id=proj_cloud.id,
            title="Setup VPC & Subnets",
            description="Configure AWS VPC, private/public subnets, and NAT Gateways",
            assignee_id=alice.id,
            reporter_id=pm.id,
            priority=TaskPriority.HIGH,
            status=TaskStatus.DONE,
            due_date=now - timedelta(days=2),
            estimated_hours=16,
            actual_hours=14,
        )
        db.add(task_a)
        db.commit()
        db.refresh(task_a)

        # Task B: Provision EKS Cluster (Depends on Task A)
        task_b = Task(
            organization_id=org_acme.id,
            project_id=proj_cloud.id,
            title="Provision EKS Cluster with Terraform",
            description="Deploy multi-AZ Elastic Kubernetes Service cluster",
            assignee_id=bob.id,
            reporter_id=pm.id,
            priority=TaskPriority.URGENT,
            status=TaskStatus.IN_PROGRESS,
            due_date=now + timedelta(days=5),
            estimated_hours=24,
            actual_hours=8,
        )
        db.add(task_b)
        db.commit()
        db.refresh(task_b)

        # Task C: Deploy Microservices Helm Charts (Depends on Task B)
        task_c = Task(
            organization_id=org_acme.id,
            project_id=proj_cloud.id,
            title="Deploy Microservices using Helm",
            description="Install ingress-nginx, cert-manager, and services",
            assignee_id=alice.id,
            reporter_id=pm.id,
            priority=TaskPriority.HIGH,
            status=TaskStatus.TODO,
            due_date=now + timedelta(days=12),
            estimated_hours=20,
        )
        db.add(task_c)
        db.commit()
        db.refresh(task_c)

        # Add dependencies: Task B depends on Task A; Task C depends on Task B
        db.add_all([
            TaskDependency(task_id=task_b.id, depends_on_task_id=task_a.id),
            TaskDependency(task_id=task_c.id, depends_on_task_id=task_b.id),
        ])
        db.commit()

        print("Seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
