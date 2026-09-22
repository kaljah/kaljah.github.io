import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from extensions import db
from models import User


def seed_admin():
    with app.app_context():
        db.create_all()

        force_reset = "--force-reset-password" in sys.argv

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@ghg.com").strip().lower()
        admin_password = os.environ.get("ADMIN_PASSWORD")

        it_admin_email = os.environ.get("IT_ADMIN_EMAIL", "itadmin@ghg.com").strip().lower()
        it_admin_password = os.environ.get("IT_ADMIN_PASSWORD")

        is_production = os.environ.get("FLASK_ENV") == "production"
        if is_production and (not admin_password or not it_admin_password):
            raise ValueError(
                "FATAL: ADMIN_PASSWORD and IT_ADMIN_PASSWORD must be explicitly set via environment variables in production."
            )

        # Fallback for dev local setup only
        if not admin_password:
            admin_password = "ChangeMeAdmin2026!"
            print("[WARNING] ADMIN_PASSWORD not set in env; using temporary dev password. Set ADMIN_PASSWORD in production!")
        if not it_admin_password:
            it_admin_password = "ChangeMeITAdmin2026!"
            print("[WARNING] IT_ADMIN_PASSWORD not set in env; using temporary dev password. Set IT_ADMIN_PASSWORD in production!")

        it_email = os.environ.get("IT_EMAIL", "it@ghg.com").strip().lower()
        it_password = os.environ.get("IT_PASSWORD") or "ChangeMeIT2026!"

        users_to_seed = [
            {
                "email": "a",
                "password": "a",
                "role": "admin",
                "fullName": "Administrator",
                "jobTitle": "Sustainability Lead",
            },
            {
                "email": "a@a",
                "password": "a",
                "role": "admin",
                "fullName": "Administrator",
                "jobTitle": "Sustainability Lead",
            },
            {
                "email": "z",
                "password": "z",
                "role": "it_manager",
                "fullName": "IT Manager",
                "jobTitle": "IT Systems Manager",
            },
            {
                "email": "z@z",
                "password": "z",
                "role": "it_manager",
                "fullName": "IT Manager",
                "jobTitle": "IT Systems Manager",
            },
            {
                "email": admin_email,
                "password": admin_password,
                "role": "admin",
                "fullName": "Administrator",
                "jobTitle": "Sustainability Lead",
            },
            {
                "email": it_admin_email,
                "password": it_admin_password,
                "role": "it_admin",
                "fullName": "IT Administrator",
                "jobTitle": "Systems Administrator",
            },
            {
                "email": it_email,
                "password": it_password,
                "role": "it",
                "fullName": "IT Support",
                "jobTitle": "IT Support Specialist",
            },
        ]

        for u_data in users_to_seed:
            email = u_data["email"]
            user = User.query.filter_by(email=email).first()
            if user:
                if force_reset:
                    user.set_password(u_data["password"])
                    user.role = u_data["role"]
                    user.fullName = u_data["fullName"]
                    user.jobTitle = u_data["jobTitle"]
                    user.status = "active"
                    db.session.commit()
                    print(f"  [OK] User '{email}' already existed. Password reset due to --force-reset-password flag.")
                else:
                    print(f"  [INFO] User '{email}' already exists. Password preserved (pass --force-reset-password to overwrite).")
            else:
                new_user = User(
                    fullName=u_data["fullName"],
                    orgName="GHG Operations",
                    email=email,
                    role=u_data["role"],
                    sector="Oil & Gas",
                    department="Sustainability & IT",
                    jobTitle=u_data["jobTitle"],
                    location="Global",
                    status="active",
                )
                new_user.set_password(u_data["password"])
                db.session.add(new_user)
                db.session.commit()
                print(f"  [OK] User '{email}' (role: {u_data['role']}) seeded successfully.")


if __name__ == "__main__":
    seed_admin()
