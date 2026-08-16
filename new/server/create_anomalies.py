from app import app
from extensions import db
from models import Emission, Scope2Emission, Scope3Emission
import random

def create_anomalies():
    with app.app_context():
        # Get one record from each scope and flag it as an anomaly
        e1 = Emission.query.first()
        e2 = Scope2Emission.query.first()
        e3 = Scope3Emission.query.first()

        count = 0
        if e1:
            e1.qa_flag = "Anomaly: Quantity exceeds threshold (10,000,000)"
            e1.status = "Pending Review"
            e1.uncertainty_pct = 15.0
            count += 1
        
        if e2:
            e2.qa_flag = "Anomaly: Quantity exceeds threshold (10,000,000)"
            e2.status = "Pending Review"
            e2.uncertainty_pct = 10.0
            count += 1
            
        if e3:
            e3.qa_flag = "Anomaly: Quantity exceeds threshold (10,000,000)"
            e3.status = "Pending Review"
            e3.uncertainty_pct = 20.0
            count += 1
            
        if count > 0:
            db.session.commit()
            print(f"Successfully flagged {count} records as anomalies for testing.")
        else:
            print("No records found in the database to flag.")

if __name__ == "__main__":
    create_anomalies()
