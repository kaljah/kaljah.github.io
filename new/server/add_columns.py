from app import app
from extensions import db
from sqlalchemy import text

def add_columns():
    with app.app_context():
        tables = ['emissions', 'scope2_emissions', 'scope3_emissions']
        columns = [
            ('uncertainty_pct', 'FLOAT'),
            ('qa_flag', 'VARCHAR(255)')
        ]
        
        with db.engine.connect() as conn:
            for table in tables:
                for col_name, col_type in columns:
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
                        print(f"Added {col_name} to {table}")
                    except Exception as e:
                        print(f"Column {col_name} might already exist in {table} or error: {e}")
            conn.commit()

if __name__ == "__main__":
    add_columns()
