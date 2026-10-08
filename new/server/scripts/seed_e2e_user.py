"""Create the throwaway sign-in the Playwright e2e specs use (email "a", password "a").

For CI and local test databases only: it refuses to run when the configuration is production.
Usage (from new/server):  python scripts/seed_e2e_user.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from extensions import db  # noqa: E402
from models import User  # noqa: E402

# (email, password, role, full name). Throwaway sign-ins for CI and local test databases only.
E2E_USERS = [
    ("a", "a", "admin", "E2E Test User"),
    ("itadmin@sonatrach.dz", "itadmin123", "it_admin", "E2E IT Admin"),
    ("operator@sonatrach.dz", "operator123", "user", "E2E Operator"),
]


def main():
    if app.config.get("IS_PRODUCTION"):
        raise SystemExit("Refusing to create the e2e test users: the configuration is production.")
    with app.app_context():
        for email, password, role, name in E2E_USERS:
            user = User.query.filter(db.func.lower(User.email) == email).first()
            if user is None:
                user = User(
                    fullName=name,
                    orgName="E2E",
                    email=email,
                    role=role,
                    sector="Oil & Gas",
                    department="QA",
                    jobTitle="Tester",
                    location="Global",
                    status="active",
                )
                db.session.add(user)
                action = "created"
            else:
                user.role, user.status = role, "active"
                action = "updated"
            user.set_password(password)
            db.session.commit()
            print(f"e2e user {email!r} {action} (id {user.id}, role {user.role})")


if __name__ == "__main__":
    main()
