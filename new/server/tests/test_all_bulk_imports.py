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
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        # Teardown: Clean up test created records
        try:
            Emission.query.filter_by(process_type="combustion", fuel_type="Natural Gas", year=2024, month=8).delete()
            Scope2Emission.query.filter_by(electricity_kwh=5000, year=2024, month=6).delete()
            Scope3Emission.query.filter_by(category="Category 1", year=2024, month=7).delete()
            ProductionData.query.filter_by(production_type="oil", year=2024, month=5).delete()
            EmissionSource.query.filter_by(source_name="Test Flare Stack 1").delete()
            MitigationProject.query.filter_by(project_name="Test Flare Reduction Project").delete()
            CustomFactor.query.filter_by(fuel_type="Special Test Fuel").delete()
            Facility.query.filter_by(name="Test Facility A").delete()
            Facility.query.filter_by(name="Test New Facility 1").delete()
            Facility.query.filter_by(name="Test New Facility 2").delete()
            User.query.filter_by(email="test@example.com").delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
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
    with app.app_context():
        from models import Scope2Emission, Scope3Emission
        facs = Facility.query.filter(Facility.name.like("Imported Facility%")).all()
        fac_ids = [f.id for f in facs]
        if fac_ids:
            Emission.query.filter(Emission.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            Scope2Emission.query.filter(Scope2Emission.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            Scope3Emission.query.filter(Scope3Emission.facility_id.in_(fac_ids)).delete(synchronize_session=False)
        Facility.query.filter(Facility.name.like("Imported Facility%")).delete(synchronize_session=False)
        db.session.commit()
    # Prepare CSV payload
    csv_data = (
        "name,location,description,activity,division,region,field,segment,code,external_id\n"
        "Imported Facility A,Location A,Desc A,Upstream,Prod,North,Field 1,Seg 1,C001,EXT-01\n"
        "Imported Facility B,Location B,Desc B,Upstream,Prod,South,Field 2,Seg 2,C002,EXT-02\n"
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
        facs = Facility.query.filter(Facility.name.like("Imported Facility%")).all()
        assert len(facs) == 2
        assert facs[0].location == "Location A"
        assert facs[1].region == "South"

    # Test overwrite mode on existing facilities (Bug 1 & Bug 2 fix verification)
    csv_overwrite = (
        "name,location,description,activity,division,region,field,segment,code,external_id\n"
        "Imported Facility A,Updated Location A,Desc A Updated,Upstream,Prod,North,Field 1,Seg 1,C001,EXT-01\n"
    )
    data_overwrite = {
        "scope": "facilities",
        "global_factor_type": "default",
        "overwrite_duplicates": "true",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_overwrite.encode("utf-8")), "facilities_ov.csv")
    }
    res_ov = client.post("/api/emissions/upload/start", data=data_overwrite, content_type="multipart/form-data")
    assert res_ov.status_code == 200
    job_id_ov = res_ov.get_json().get("job_id")
    status_ov = wait_for_job(client, job_id_ov)
    assert status_ov["status"] == "completed"

    with app.app_context():
        fac_updated = Facility.query.filter_by(name="Imported Facility A").first()
        assert fac_updated is not None
        assert fac_updated.location == "Updated Location A"
        assert fac_updated.description == "Desc A Updated"

def test_bulk_import_custom_factors(logged_client, app):
    client = logged_client
    with app.app_context():
        CustomFactor.query.filter_by(name="My Factor").delete()
        db.session.commit()
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

def test_bulk_import_duplicate_prevention_and_overwrite(logged_client, app):
    """DEF-04 Verification: Ensure duplicate rows are skipped by default and updated when overwrite_duplicates=True."""
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
        # Clean test records
        Emission.query.filter_by(year=2025, month=1).delete()
        db.session.commit()

    csv_data = (
        "facility_name,date,process,fuel,quantity,unit\n"
        "Test Facility A,2025-01,combustion,Natural Gas,1000,scf\n"
    )
    mapping = {
        "facility_name": "facility_name",
        "date": "date",
        "process": "process",
        "fuel": "fuel",
        "quantity": "quantity",
        "unit": "unit"
    }

    # First upload: should insert 1 record
    res1 = client.post("/api/emissions/upload/start", data={
        "scope": "1",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "scope1_test.csv")
    }, content_type="multipart/form-data")
    assert res1.status_code == 200
    job1 = wait_for_job(client, res1.get_json()["job_id"])
    assert job1["status"] == "completed"

    with app.app_context():
        count1 = Emission.query.filter_by(year=2025, month=1).count()
        assert count1 == 1

    # Second upload WITHOUT overwrite: should skip the duplicate row
    res2 = client.post("/api/emissions/upload/start", data={
        "scope": "1",
        "global_factor_type": "default",
        "overwrite_duplicates": "false",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "scope1_test.csv")
    }, content_type="multipart/form-data")
    assert res2.status_code == 200
    job2 = wait_for_job(client, res2.get_json()["job_id"])
    assert job2["status"] == "completed"
    assert job2["skipped_count"] == 1
    assert "Duplicate record" in job2["skipped_preview"][0]["reason"]

    with app.app_context():
        # Count MUST still be 1 (NOT silently doubled to 2!)
        count2 = Emission.query.filter_by(year=2025, month=1).count()
        assert count2 == 1

    # Third upload WITH overwrite and new quantity: should update in place
    csv_updated = (
        "facility_name,date,process,fuel,quantity,unit\n"
        "Test Facility A,2025-01,combustion,Natural Gas,2500,scf\n"
    )
    res3 = client.post("/api/emissions/upload/start", data={
        "scope": "1",
        "global_factor_type": "default",
        "overwrite_duplicates": "true",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_updated.encode("utf-8")), "scope1_updated.csv")
    }, content_type="multipart/form-data")
    assert res3.status_code == 200
    job3 = wait_for_job(client, res3.get_json()["job_id"])
    assert job3["status"] == "completed"

    with app.app_context():
        count3 = Emission.query.filter_by(year=2025, month=1).count()
        assert count3 == 1
        updated_rec = Emission.query.filter_by(year=2025, month=1).first()
        assert updated_rec.quantity == 2500
        # Cleanup
        Emission.query.filter_by(year=2025, month=1).delete()
        db.session.commit()


def test_vented_fuel_key_deduplication_normalization(logged_client, app):
    """Verifies that non-combustion sources (e.g. pneumatics) normalize fuel_k to empty string,
    preventing duplicate leaks with different fuel labels from bypassing deduplication."""
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="Test Facility A").first()
        if not fac:
            fac = Facility(name="Test Facility A")
            db.session.add(fac)
            db.session.commit()
        Emission.query.filter_by(year=2025, month=2).delete()
        db.session.commit()

    # Upload 1: pneumatics row with empty fuel
    csv_data1 = (
        "facility_name,date,process,fuel,quantity,unit\n"
        "Test Facility A,2025-02,pneumatics,,500,count\n"
    )
    mapping = {
        "facility_name": "facility_name",
        "date": "date",
        "process": "process",
        "fuel": "fuel",
        "quantity": "quantity",
        "unit": "unit"
    }

    res1 = client.post("/api/emissions/upload/start", data={
        "scope": "1",
        "global_factor_type": "default",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data1.encode("utf-8")), "pneumatics1.csv")
    }, content_type="multipart/form-data")
    assert res1.status_code == 200
    job1 = wait_for_job(client, res1.get_json()["job_id"])
    assert job1["status"] == "completed"

    with app.app_context():
        count1 = Emission.query.filter_by(year=2025, month=2).count()
        assert count1 == 1

    # Upload 2: same facility, date, process ("pneumatics"), but with fuel="Natural Gas"
    # Because pneumatics is a non-combustion process, fuel_k is normalized to "",
    # so without overwrite, this should be detected as a duplicate and skipped.
    csv_data2 = (
        "facility_name,date,process,fuel,quantity,unit\n"
        "Test Facility A,2025-02,pneumatics,Natural Gas,500,count\n"
    )
    res2 = client.post("/api/emissions/upload/start", data={
        "scope": "1",
        "global_factor_type": "default",
        "overwrite_duplicates": "false",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data2.encode("utf-8")), "pneumatics2.csv")
    }, content_type="multipart/form-data")
    assert res2.status_code == 200
    job2 = wait_for_job(client, res2.get_json()["job_id"])
    assert job2["status"] == "completed"
    assert job2["skipped_count"] == 1
    assert "Duplicate record" in job2["skipped_preview"][0]["reason"]

    with app.app_context():
        count2 = Emission.query.filter_by(year=2025, month=2).count()
        assert count2 == 1
        # Cleanup
        Emission.query.filter_by(year=2025, month=2).delete()
        db.session.commit()

