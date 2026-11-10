import os
import io
import json
import time
import pytest
from models import (
    User,
    Facility,
    CustomFactor,
    ProductionData,
    EmissionSource,
    MitigationProject,
)
from extensions import db

@pytest.fixture(scope="module")
def app():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        # Cleanup
        try:
            EmissionSource.query.filter(EmissionSource.name.like("BulkTest%")).delete()
            MitigationProject.query.filter(MitigationProject.name.like("BulkTest%")).delete()
            CustomFactor.query.filter(CustomFactor.name.like("BulkTest%")).delete()
            ProductionData.query.filter_by(year=2026, month=11).delete()
            Facility.query.filter(Facility.name.like("BulkTest Facility%")).delete()
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
        user = User.query.filter_by(email="bulk_tester@example.com").first()
        if not user:
            user = User(fullName="Bulk Tester", orgName="TestOrg", sector="TestSector", email="bulk_tester@example.com", role="admin")
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
        if data and data.get("status") in ["completed", "error", "failed"]:
            return data
        time.sleep(0.3)
    return {"status": "timeout"}

def test_sources_duplicate_prevention_and_overwrite(logged_client, app):
    """Test that sources return an error on duplicate without overwrite, and update in-place with overwrite."""
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="BulkTest Facility 1").first()
        if not fac:
            fac = Facility(name="BulkTest Facility 1", location="Basin Alpha")
            db.session.add(fac)
            db.session.commit()
        EmissionSource.query.filter(EmissionSource.name.like("BulkTest%")).delete()
        db.session.commit()

    csv_data = (
        "facility_name,name,equipment_id,type,fuel_type,description\n"
        "BulkTest Facility 1,BulkTest Generator,BT-GEN-01,combustion,Natural Gas,Initial Desc\n"
    )
    mapping = {
        "facility_name": "facility_name",
        "name": "name",
        "equipment_id": "equipment_id",
        "type": "type",
        "fuel_type": "fuel_type",
        "description": "description",
    }

    # 1. Initial upload
    res = client.post("/api/emissions/upload/start", data={
        "scope": "sources",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "sources.csv")
    }, content_type="multipart/form-data")
    assert res.status_code == 200
    job = wait_for_job(client, res.get_json()["job_id"])
    assert job["status"] == "completed"
    assert job["skipped_count"] == 0

    with app.app_context():
        src = EmissionSource.query.filter_by(equipment_id="BT-GEN-01").first()
        assert src is not None
        assert src.description == "Initial Desc"

    # 2. Duplicate upload without overwrite -> should report error / skip
    res2 = client.post("/api/emissions/upload/start", data={
        "scope": "sources",
        "overwrite_duplicates": "false",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "sources.csv")
    }, content_type="multipart/form-data")
    assert res2.status_code == 200
    job2 = wait_for_job(client, res2.get_json()["job_id"])
    assert job2["status"] == "completed"
    assert job2["skipped_count"] == 1
    assert "already exists" in job2["skipped_preview"][0]["reason"]

    # 3. Duplicate upload with overwrite -> updates in place
    csv_updated = (
        "facility_name,name,equipment_id,type,fuel_type,description\n"
        "BulkTest Facility 1,BulkTest Generator,BT-GEN-01,combustion,Diesel,Updated Desc\n"
    )
    res3 = client.post("/api/emissions/upload/start", data={
        "scope": "sources",
        "overwrite_duplicates": "true",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_updated.encode("utf-8")), "sources_up.csv")
    }, content_type="multipart/form-data")
    assert res3.status_code == 200
    job3 = wait_for_job(client, res3.get_json()["job_id"])
    assert job3["status"] == "completed"
    assert job3["skipped_count"] == 0

    with app.app_context():
        src_up = EmissionSource.query.filter_by(equipment_id="BT-GEN-01").first()
        assert src_up is not None
        assert src_up.fuel_type == "Diesel"
        assert src_up.description == "Updated Desc"

def test_custom_factors_duplicate_prevention_and_overwrite(logged_client, app):
    """Test custom factors duplicate handling: error when duplicate, in-place update when overwrite."""
    client = logged_client
    with app.app_context():
        CustomFactor.query.filter(CustomFactor.name.like("BulkTest%")).delete()
        db.session.commit()

    csv_data = (
        "name,co2_factor,ch4_factor,n2o_factor,unit\n"
        "BulkTest Factor Alpha,2.5,0.01,0.001,kg\n"
    )
    mapping = {
        "name": "name",
        "co2_factor": "co2_factor",
        "ch4_factor": "ch4_factor",
        "n2o_factor": "n2o_factor",
        "unit": "unit",
    }

    # 1. Initial upload
    res = client.post("/api/emissions/upload/start", data={
        "scope": "custom_factors",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "cf.csv")
    }, content_type="multipart/form-data")
    assert res.status_code == 200
    job = wait_for_job(client, res.get_json()["job_id"])
    assert job["status"] == "completed"
    assert job["skipped_count"] == 0

    with app.app_context():
        cf = CustomFactor.query.filter_by(name="BulkTest Factor Alpha").first()
        assert cf is not None
        assert cf.co2_factor == 2.5

    # 2. Duplicate upload without overwrite -> error / skipped
    res2 = client.post("/api/emissions/upload/start", data={
        "scope": "custom_factors",
        "overwrite_duplicates": "false",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "cf.csv")
    }, content_type="multipart/form-data")
    assert res2.status_code == 200
    job2 = wait_for_job(client, res2.get_json()["job_id"])
    assert job2["status"] == "completed"
    assert job2["skipped_count"] == 1
    assert "already exists" in job2["skipped_preview"][0]["reason"]

    # 3. Duplicate upload with overwrite -> update in place
    csv_updated = (
        "name,co2_factor,ch4_factor,n2o_factor,unit\n"
        "BulkTest Factor Alpha,3.8,0.02,0.002,kg\n"
    )
    res3 = client.post("/api/emissions/upload/start", data={
        "scope": "custom_factors",
        "overwrite_duplicates": "true",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_updated.encode("utf-8")), "cf_up.csv")
    }, content_type="multipart/form-data")
    assert res3.status_code == 200
    job3 = wait_for_job(client, res3.get_json()["job_id"])
    assert job3["status"] == "completed"
    assert job3["skipped_count"] == 0

    with app.app_context():
        cf_up = CustomFactor.query.filter_by(name="BulkTest Factor Alpha").first()
        assert cf_up is not None
        assert cf_up.co2_factor == 3.8

def test_production_duplicate_prevention_and_overwrite(logged_client, app):
    """Test production duplicate handling: error when duplicate, in-place update when overwrite."""
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="BulkTest Facility 1").first()
        if not fac:
            fac = Facility(name="BulkTest Facility 1", location="Basin Alpha")
            db.session.add(fac)
            db.session.commit()
        ProductionData.query.filter_by(year=2026, month=11).delete()
        db.session.commit()

    csv_data = (
        "facility_name,year,month,production_volume,production_unit,energy_consumption,energy_unit\n"
        "BulkTest Facility 1,2026,11,10000,bbl,5000,mscf\n"
    )
    mapping = {
        "facility_name": "facility_name",
        "year": "year",
        "month": "month",
        "production_volume": "production_volume",
        "production_unit": "production_unit",
        "energy_consumption": "energy_consumption",
        "energy_unit": "energy_unit",
    }

    # 1. Initial upload
    res = client.post("/api/emissions/upload/start", data={
        "scope": "production",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "prod.csv")
    }, content_type="multipart/form-data")
    assert res.status_code == 200
    job = wait_for_job(client, res.get_json()["job_id"])
    assert job["status"] == "completed"
    assert job["skipped_count"] == 0

    with app.app_context():
        prod = ProductionData.query.filter_by(year=2026, month=11).first()
        assert prod is not None
        assert prod.oil_amount == 10000

    # 2. Duplicate upload without overwrite -> error / skipped
    res2 = client.post("/api/emissions/upload/start", data={
        "scope": "production",
        "overwrite_duplicates": "false",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "prod.csv")
    }, content_type="multipart/form-data")
    assert res2.status_code == 200
    job2 = wait_for_job(client, res2.get_json()["job_id"])
    assert job2["status"] == "completed"
    assert job2["skipped_count"] == 1
    assert "already exists" in job2["skipped_preview"][0]["reason"]

    # 3. Duplicate upload with overwrite -> update in place
    csv_updated = (
        "facility_name,year,month,production_volume,production_unit,energy_consumption,energy_unit\n"
        "BulkTest Facility 1,2026,11,25000,bbl,8000,mscf\n"
    )
    res3 = client.post("/api/emissions/upload/start", data={
        "scope": "production",
        "overwrite_duplicates": "true",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_updated.encode("utf-8")), "prod_up.csv")
    }, content_type="multipart/form-data")
    assert res3.status_code == 200
    job3 = wait_for_job(client, res3.get_json()["job_id"])
    assert job3["status"] == "completed"
    assert job3["skipped_count"] == 0

    with app.app_context():
        prod_up = ProductionData.query.filter_by(year=2026, month=11).first()
        assert prod_up is not None
        assert prod_up.oil_amount == 25000

def test_mitigation_duplicate_prevention_and_overwrite(logged_client, app):
    """Test mitigation duplicate handling: error when duplicate, in-place update when overwrite."""
    client = logged_client
    with app.app_context():
        fac = Facility.query.filter_by(name="BulkTest Facility 1").first()
        if not fac:
            fac = Facility(name="BulkTest Facility 1", location="Basin Alpha")
            db.session.add(fac)
            db.session.commit()
        MitigationProject.query.filter(MitigationProject.name.like("BulkTest%")).delete()
        db.session.commit()

    csv_data = (
        "facility_name,name,type,year,quantity_tco2e,status,description\n"
        "BulkTest Facility 1,BulkTest Solar,Solar,2026,1200,Active,Initial Mitigation\n"
    )
    mapping = {
        "facility_name": "facility_name",
        "name": "name",
        "type": "type",
        "year": "year",
        "quantity_tco2e": "quantity_tco2e",
        "status": "status",
        "description": "description",
    }

    # 1. Initial upload
    res = client.post("/api/emissions/upload/start", data={
        "scope": "mitigation",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "mit.csv")
    }, content_type="multipart/form-data")
    assert res.status_code == 200
    job = wait_for_job(client, res.get_json()["job_id"])
    assert job["status"] == "completed"
    assert job["skipped_count"] == 0

    with app.app_context():
        mit = MitigationProject.query.filter_by(name="BulkTest Solar").first()
        assert mit is not None
        assert mit.quantity_tco2e == 1200
        assert mit.description == "Initial Mitigation"

    # 2. Duplicate upload without overwrite -> error / skipped
    res2 = client.post("/api/emissions/upload/start", data={
        "scope": "mitigation",
        "overwrite_duplicates": "false",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_data.encode("utf-8")), "mit.csv")
    }, content_type="multipart/form-data")
    assert res2.status_code == 200
    job2 = wait_for_job(client, res2.get_json()["job_id"])
    assert job2["status"] == "completed"
    assert job2["skipped_count"] == 1
    assert "already exists" in job2["skipped_preview"][0]["reason"]

    # 3. Duplicate upload with overwrite -> update in place
    csv_updated = (
        "facility_name,name,type,year,quantity_tco2e,status,description\n"
        "BulkTest Facility 1,BulkTest Solar,Solar,2026,3500,Completed,Updated Mitigation\n"
    )
    res3 = client.post("/api/emissions/upload/start", data={
        "scope": "mitigation",
        "overwrite_duplicates": "true",
        "mapping": json.dumps(mapping),
        "file": (io.BytesIO(csv_updated.encode("utf-8")), "mit_up.csv")
    }, content_type="multipart/form-data")
    assert res3.status_code == 200
    job3 = wait_for_job(client, res3.get_json()["job_id"])
    assert job3["status"] == "completed"
    assert job3["skipped_count"] == 0

    with app.app_context():
        mit_up = MitigationProject.query.filter_by(name="BulkTest Solar").first()
        assert mit_up is not None
        assert mit_up.quantity_tco2e == 3500
        assert mit_up.status == "Completed"
        assert mit_up.description == "Updated Mitigation"
