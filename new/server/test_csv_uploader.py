"""
End-to-End Test for the CSV Uploader (Import Emissions Data Wizard)
Tests the full pipeline: API Upload -> Background Processor -> Database
"""

import sys
import os
import io
import time
import unittest

# Add the server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Facility, Emission


class TestCSVUploaderE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Override DB to a test file so we don't touch production data
        cls.db_file = os.path.join(os.path.dirname(__file__), "test_uploader_e2e.db")

        # Setting testing configs
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{cls.db_file}"
        app.config["WTF_CSRF_ENABLED"] = False

        cls.client = app.test_client()
        cls.app_context = app.app_context()
        cls.app_context.push()

        db.create_all()

        # 1. Create a test user
        cls.user = User(
            fullName="Test Uploader Admin",
            orgName="Org",
            sector="IT",
            email="uploader@test.com",
            role="admin",
        )
        cls.user.set_password("ComplexPassword123!")
        db.session.add(cls.user)

        # 2. Create test facilities that match our CSV names
        cls.fac_alpha = Facility(
            name="Test Plant Alpha", region="North", activity="Production"
        )
        cls.fac_beta = Facility(
            name="Test Plant Beta", region="South", activity="Refining"
        )
        db.session.add_all([cls.fac_alpha, cls.fac_beta])

        db.session.commit()

        # 3. Log in via API to get session cookie
        res = cls.client.post(
            "/api/auth/login",
            json={"email": "uploader@test.com", "password": "ComplexPassword123!"},
        )
        assert res.status_code == 200, f"Login failed in setup: {res.json}"

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()
        if os.path.exists(cls.db_file):
            try:
                os.remove(cls.db_file)
            except:
                pass

    def test_upload_csv_end_to_end(self):
        """
        Tests the CSV upload endpoint with a mock CSV containing mixed scenarios.
        Validates the background job progress and the final saved database records.
        """
        # 1. Prepare CSV Content covering multiple process types (Tier 1 & Tier 3)
        # Note: We must use the exact UI headers that _build_mapping expects (e.g. Region maps to facility).
        csv_content = (
            "Date,Region,Process,Fuel,Factor Type,Quantity,Unit,Combustion Efficiency,Flare Type,Well Depth,Diameter,Pressure,Events,CH4 Content\n"
            # Row 1: Tier 1 Combustion (Natural Gas)
            "2024-01,Test Plant Alpha,Combustion,Natural Gas,Default,10000,scf,,,,,,,,\n"
            # Row 2: Tier 1 Flaring (Associated Gas)
            "2024-02,Test Plant Alpha,Flaring,Associated Gas (Flaring),Default,5000,m3,,,,,,,,\n"
            # Row 3: Tier 3 Flaring (Elevated, CH4=85%)
            "2024-03,Test Plant Alpha,Flaring,Custom,Specific,1000,m3,98.4,elevated,,,,,85\n"
            # Row 4: Tier 3 Liquids Unloading
            "2024-04,Test Plant Beta,Liquids Unloading,Custom,Specific,12,events,,,,5000,2.441,500,12,85\n"
            # Row 5: Invalid Facility (Should error out for this row but process others)
            "2024-05,Invalid Plant,Combustion,Natural Gas,Default,100,m3,,,,,,,,\n"
        )

        # 2. Upload file via the API
        data = {
            "file": (io.BytesIO(csv_content.encode("utf-8")), "test_upload.csv"),
            "global_factor_type": "auto",
        }
        upload_response = self.client.post(
            "/api/emissions/upload/start", data=data, content_type="multipart/form-data"
        )

        self.assertEqual(
            upload_response.status_code, 200, f"Upload failed: {upload_response.json}"
        )
        job_id = upload_response.json.get("job_id")
        self.assertIsNotNone(job_id, "Job ID not returned by upload endpoint")

        # 3. Poll status API until completion
        max_retries = 20
        job_data = {}
        for _ in range(max_retries):
            status_res = self.client.get(f"/api/emissions/upload/status/{job_id}")
            self.assertEqual(status_res.status_code, 200, "Failed to get job status")
            job_data = status_res.json
            if job_data.get("status") in ["completed", "error"]:
                break
            time.sleep(0.5)

        self.assertEqual(
            job_data.get("status"),
            "completed",
            f"Job did not complete successfully. Final data: {job_data}",
        )
        self.assertEqual(
            job_data.get("processed"),
            5,
            "Should have processed all 5 rows from the CSV",
        )

        # The 5th row should have been skipped because of 'Invalid Plant'
        skipped_count = job_data.get("skipped_count", len(job_data.get("skipped", [])))
        skipped = job_data.get("skipped_preview", job_data.get("skipped", []))
        self.assertEqual(
            skipped_count, 1, "Exactly 1 row should be skipped due to invalid facility"
        )
        self.assertTrue(
            "not found" in skipped[0]["reason"].lower(),
            f"Unexpected skip reason: {skipped[0]['reason']}",
        )

        # 4. Verify Database Records
        emissions = Emission.query.order_by(Emission.month).all()
        self.assertEqual(
            len(emissions), 4, "4 valid rows should have been saved in the database"
        )

        # Check Row 1 (Combustion, Alpha)
        row1 = emissions[0]
        self.assertEqual(row1.process_type, "Combustion")
        self.assertEqual(row1.facility.name, "Test Plant Alpha")
        self.assertEqual(row1.quantity, 10000)
        self.assertEqual(row1.unit, "scf")
        self.assertGreater(row1.co2_emissions, 0, "Calculated CO2 must be > 0")
        self.assertGreater(row1.co2e_total, 0, "Calculated CO2e must be > 0")
        self.assertIsNotNone(row1.source_payload, "Source payload JSON must be saved")

        # Check Row 2 (Tier 1 Flaring, Alpha)
        row2 = emissions[1]
        self.assertEqual(row2.process_type, "Flaring")
        self.assertGreater(row2.co2e_total, 0)

        # Check Row 3 (Tier 3 Flaring, Alpha)
        row3 = emissions[2]
        self.assertEqual(row3.process_type, "Flaring")

        # Check Row 4 (Tier 3 Liquids Unloading, Beta)
        row4 = emissions[3]
        self.assertEqual(row4.facility.name, "Test Plant Beta")
        self.assertEqual(row4.process_type, "Liquids Unloading")
        self.assertEqual(row4.quantity, 12)
        self.assertEqual(row4.unit, "events")


if __name__ == "__main__":
    unittest.main(verbosity=2)
