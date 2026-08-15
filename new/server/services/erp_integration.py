import time
import random
from models import Scope3Emission
from extensions import db
from datetime import datetime

def sync_erp_data(user_id):
    """
    Mock ERP synchronization service.
    In a real scenario, this would call SAP/Oracle APIs using OAuth2,
    fetch spend data or activity data, and map it to the internal GHG schema.
    """
    time.sleep(2) # Mock network latency
    
    # Simulate fetching 3 records from an ERP system
    records = [
        {
            "facility_id": 1,
            "year": datetime.now().year,
            "month": datetime.now().month,
            "category": "1",
            "sub_category": "ERP Sync: Professional Services",
            "activity_data": 50000,
            "unit": "USD",
            "emission_factor": 0.12, 
            "co2e": 6.0,
            "calculation_method": "Spend-based (EEIO)",
            "data_quality": "Average-data method",
            "notes": "Auto-synced from SAP Ariba - Inv #9921",
            "status": "Pending"
        },
        {
            "facility_id": 1,
            "year": datetime.now().year,
            "month": datetime.now().month,
            "category": "6",
            "sub_category": "ERP Sync: Business Flights",
            "activity_data": 12000,
            "unit": "passenger-km",
            "emission_factor": 0.255, 
            "co2e": 3.06,
            "calculation_method": "Activity-based",
            "data_quality": "Average-data method",
            "notes": "Auto-synced from Concur - Sep Flights",
            "status": "Pending"
        },
        {
            "facility_id": 1,
            "year": datetime.now().year,
            "month": datetime.now().month,
            "category": "2",
            "sub_category": "ERP Sync: IT Equipment",
            "activity_data": 15000,
            "unit": "USD",
            "emission_factor": 0.35, 
            "co2e": 5.25,
            "calculation_method": "Spend-based",
            "data_quality": "Average-data method",
            "notes": "Auto-synced from SAP - Laptops",
            "status": "Pending"
        }
    ]
    
    inserted_count = 0
    try:
        for rec in records:
            emission = Scope3Emission(
                facility_id=rec["facility_id"],
                year=rec["year"],
                month=rec["month"],
                category=rec["category"],
                sub_category=rec["sub_category"],
                activity_data=rec["activity_data"],
                unit=rec["unit"],
                emission_factor=rec["emission_factor"],
                co2e=rec["co2e"],
                calculation_method=rec["calculation_method"],
                data_quality=rec["data_quality"],
                notes=rec["notes"],
                created_by=user_id,
                status=rec["status"]
            )
            db.session.add(emission)
            inserted_count += 1
            
        db.session.commit()
        return {"success": True, "synced_records": inserted_count, "message": f"Successfully synced {inserted_count} records from ERP"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
