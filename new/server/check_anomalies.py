from app import app
from extensions import db
from models import Emission, Scope2Emission, Scope3Emission

with app.app_context():
    e1 = Emission.query.filter(Emission.qa_flag.isnot(None)).all()
    e2 = Scope2Emission.query.filter(Scope2Emission.qa_flag.isnot(None)).all()
    e3 = Scope3Emission.query.filter(Scope3Emission.qa_flag.isnot(None)).all()

    print(f"Scope 1 Anomaly Count: {len(e1)}")
    print(f"Scope 2 Anomaly Count: {len(e2)}")
    print(f"Scope 3 Anomaly Count: {len(e3)}")

    # Let's also check if there are ANY records at all
    print(f"Total Scope 1: {Emission.query.count()}")
    print(f"Total Scope 2: {Scope2Emission.query.count()}")
    print(f"Total Scope 3: {Scope3Emission.query.count()}")
