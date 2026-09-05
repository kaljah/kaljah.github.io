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

        users_to_seed = [
            {
                "email": "a@a",
                "password": "a",
                "role": "admin",
                "fullName": "Admin User",
                "jobTitle": "Sustainability Administrator",
            },
            {
                "email": "z@z",
                "password": "z",
                "role": "it_admin",
                "fullName": "IT Admin User",
                "jobTitle": "IT Administrator",
            },
            {
                "email": "a",
                "password": "a",
                "role": "admin",
                "fullName": "Admin User",
                "jobTitle": "Sustainability Administrator",
            },
            {
                "email": "z",
                "password": "z",
                "role": "it_admin",
                "fullName": "IT Admin User",
                "jobTitle": "IT Administrator",
            },
            {
                "email": "admin@ghg.com",
                "password": "Admin12345!",
                "role": "it_admin",
                "fullName": "System Administrator",
                "jobTitle": "IT Administrator",
            },
            {
                "email": "admin@test.com",
                "password": "Admin@123!",
                "role": "admin",
                "fullName": "Admin User",
                "jobTitle": "Sustainability Lead",
            },
            {
                "email": "user@test.com",
                "password": "User@123!",
                "role": "user",
                "fullName": "Regular User",
                "jobTitle": "Data Specialist",
            },
        ]

        for u_data in users_to_seed:
            email = u_data["email"]
            user = User.query.filter_by(email=email).first()
            if user:
                print(
                    f"User with email '{email}' already exists. Updating password and role..."
                )
                user.set_password(u_data["password"])
                user.role = u_data["role"]
                user.fullName = u_data["fullName"]
                user.jobTitle = u_data["jobTitle"]
                user.status = "active"
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
            print(
                f"  [OK] User '{email}' (role: {u_data['role']}) seeded successfully."
            )


if __name__ == "__main__":
    seed_admin()
