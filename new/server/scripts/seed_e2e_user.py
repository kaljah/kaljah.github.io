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

E2E_EMAIL = "a"
E2E_PASSWORD = "a"


def main():
    if app.config.get("IS_PRODUCTION"):
        raise SystemExit("Refusing to create the e2e test user: the configuration is production.")
    with app.app_context():
        user = User.query.filter(db.func.lower(User.email) == E2E_EMAIL).first()
        if user is None:
            user = User(
                fullName="E2E Test User",
                orgName="E2E",
                email=E2E_EMAIL,
                role="admin",
                sector="Oil & Gas",
                department="QA",
                jobTitle="Tester",
                location="Global",
                status="active",
            )
            db.session.add(user)
            action = "created"
        else:
            user.role, user.status = "admin", "active"
            action = "updated"
        user.set_password(E2E_PASSWORD)
        db.session.commit()
        print(f"e2e user {E2E_EMAIL!r} {action} (id {user.id}, role {user.role})")


if __name__ == "__main__":
    main()
