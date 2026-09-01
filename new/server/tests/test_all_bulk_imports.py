import os
import io
import json
import time
import pytest
from flask import Flask
from models import (
    User,
    Facility,
    CustomFactor,
    ProductionData,
    EmissionSource,
    MitigationProject,
    Scope2Emission,
    Scope3Emission,
    Emission,
)
from extensions import db
from datetime import datetime

# Tests for the new universal background_processor.py bulk upload pipeline

@pytest.fixture(scope="module")
def app():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app_context():
        yield flask_app
        db.session.remove()

@pytest.fixture(scope="module")
def client(app):
    return app.test_client()

@pytest.fixture(scope="module")
def logged_client(client, app):
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(fullName="Test", orgName="TestOrg", sector="TestSector", email="test@example.com", role="admin")
            user.set_password("pass123")
            db.session.add(user)
            db.session.commit()
            
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            
    return client

def wait_for_job(client, job_id, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        res = client.get(f"/api/emissions/upload/status/{job_id}")
        data = res.get_json()
        if data["status"] in ["completed", "error", "failed"]:
            return data
        time.time()
        time.sleep(0.5)
    return {"status": "timeout"}

def test_bulk_import_facilities(logged_client, app):
    client = logged_client
    # Prepare CSV payload
    csv_data = (
        "name,location,description,activity,division,region,field,segment,code,external_id\n"
        "Test Facility A,Location A,Desc A,Upstream,Prod,North,Field 1,Seg 1,C001,EXT-01\n"
        "Test Facility B,Location B,Desc B,Upstream,Prod,South,Field 2,Seg 2,C002,EXT-02\n"
    )
    
    mapping = {
        "name": "name",
        "location": "location",
        "description": "description",
        "activity": "activity",
        "division": "division",
        "region": "region",
        "field": "field",
        "segment": "segment",
        "code": "code",
        "external_id": "external_id"
    }

    data = {
        "scope": "facilities",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "facilities.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        facs = Facility.query.filter(Facility.name.like("Test Facility%")).all()
        assert len(facs) == 2
        assert facs[0].location == "Location A"
        assert facs[1].region == "South"

def test_bulk_import_custom_factors(logged_client, app):
    client = logged_client
    csv_data = (
        "name,co2_factor,ch4_factor,n2o_factor,co_factor,unit,hhv_factor,usage,parent_fuel,source,version,uncertainty\n"
        "My Factor,10.5,0.1,0.01,0.5,kg,40,test,Gas,EPA,v1,5\n"
    )
    
    mapping = {
        "name": "name",
        "co2_factor": "co2_factor",
        "ch4_factor": "ch4_factor",
        "n2o_factor": "n2o_factor",
        "co_factor": "co_factor",
        "unit": "unit",
        "hhv_factor": "hhv_factor",
        "usage": "usage",
        "parent_fuel": "parent_fuel",
        "source": "source",
        "version": "version",
        "uncertainty": "uncertainty"
    }

    data = {
        "scope": "custom_factors",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "factors.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        factor = CustomFactor.query.filter_by(name="My Factor").first()
        assert factor is not None
        assert factor.co2_factor == 10.5
        assert factor.unit == "kg"

def test_bulk_import_production(logged_client, app):
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
            
    csv_data = (
        "facility_name,activity,division,field,year,month,production_volume,production_unit,energy_consumption,energy_unit\n"
        "Test Facility A,Upstream,Prod,Field 1,2024,5,1000,bbl,500,MWh\n"
    )
    
    mapping = {
        "facility_name": "facility_name",
        "activity": "activity",
        "division": "division",
        "field": "field",
        "year": "year",
        "month": "month",
        "production_volume": "production_volume",
        "production_unit": "production_unit",
        "energy_consumption": "energy_consumption",
        "energy_unit": "energy_unit"
    }

    data = {
        "scope": "production",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "prod.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        prod = ProductionData.query.filter_by(year=2024, month=5).first()
        assert prod is not None
        assert prod.oil_amount == 1000

def test_bulk_import_sources(logged_client, app):
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
            
    csv_data = (
        "activity,division,facility_name,field,name,equipment_id,type,fuel_type\n"
        "Upstream,Prod,Test Facility A,Field 1,Generator 1,EQ-001,combustion,Diesel\n"
    )
    
    mapping = {
        "activity": "activity",
        "division": "division",
        "facility_name": "facility_name",
        "field": "field",
        "name": "name",
        "equipment_id": "equipment_id",
        "type": "type",
        "fuel_type": "fuel_type"
    }

    data = {
        "scope": "sources",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "sources.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        src = EmissionSource.query.filter_by(equipment_id="EQ-001").first()
        assert src is not None
        assert src.type == "combustion"

def test_bulk_import_mitigation(logged_client, app):
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
            
    csv_data = (
        "facility_name,name,type,year,quantity_tco2e,status,start_date,investment_amount\n"
        "Test Facility A,Project X,Solar,2024,500,Active,2024-01-01,100000\n"
    )
    
    mapping = {
        "facility_name": "facility_name",
        "name": "name",
        "type": "type",
        "year": "year",
        "quantity_tco2e": "quantity_tco2e",
        "status": "status",
        "start_date": "start_date",
        "investment_amount": "investment_amount"
    }

    data = {
        "scope": "mitigation",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "mitigation.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        proj = MitigationProject.query.filter_by(name="Project X").first()
        assert proj is not None
        assert proj.quantity_tco2e == 500

def test_bulk_import_scope2(logged_client, app):
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
            
    csv_data = (
        "facility_name,year,month,grid_region,consumption,unit\n"
        "Test Facility A,2024,6,Algerian National Grid,1000,MWh\n"
    )
    
    mapping = {
        "facility_name": "facility_name",
        "year": "year",
        "month": "month",
        "grid_region": "grid_region",
        "consumption": "consumption",
        "unit": "unit"
    }

    data = {
        "scope": "2",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "scope2.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        s2 = Scope2Emission.query.filter_by(year=2024, month=6).first()
        assert s2 is not None
        assert s2.electricity_kwh == 1000 * 1000
        assert s2.co2e > 0

def test_bulk_import_scope3(logged_client, app):
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
            
    csv_data = (
        "facility_name,year,month,category,amount,emission_factor,unit,ef_unit\n"
        "Test Facility A,2024,7,Category 1,500,2.5,kg,kgCO2e/kg\n"
    )
    
    mapping = {
        "facility_name": "facility_name",
        "year": "year",
        "month": "month",
        "category": "category",
        "amount": "amount",
        "emission_factor": "emission_factor",
        "unit": "unit",
        "ef_unit": "ef_unit"
    }

    data = {
        "scope": "3",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "scope3.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        s3 = Scope3Emission.query.filter_by(year=2024, month=7).first()
        assert s3 is not None
        assert s3.category == "Category 1"
        assert s3.co2e == (500 * 2.5) / 1000

def test_bulk_import_scope1(logged_client, app):
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
            
    csv_data = (
        "facility_name,date,process,fuel,quantity,unit\n"
        "Test Facility A,2024-08,combustion,Natural Gas,1000,scf\n"
    )
    
    mapping = {
        "facility_name": "facility_name",
        "date": "date",
        "process": "process",
        "fuel": "fuel",
        "quantity": "quantity",
        "unit": "unit"
    }

    data = {
        "scope": "1",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "scope1.csv")
    }

    res = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    job_id = res.get_json().get("job_id")
    
    status = wait_for_job(client, job_id)
    assert status["status"] == "completed"
    
    with app.app_context():
        s1 = Emission.query.filter_by(year=2024, month=8).first()
        assert s1 is not None
        assert s1.process_type == "combustion"
        assert s1.co2e_total > 0
