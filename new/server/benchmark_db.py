import sqlite3
import time

def benchmark_queries():
    db_path = 'ghg_app.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Dashboard Heavy Aggregation Query
    query = """
    SELECT year, SUM(co2_emissions + ch4_emissions * 28 + n2o_emissions * 265) as total_co2e
    FROM emissions
    GROUP BY year
    """
    
    print("--- Dashboard Scope 1 Aggregation Benchmark ---")
    start = time.perf_counter()
    cursor.execute(query)
    results = cursor.fetchall()
    duration = (time.perf_counter() - start) * 1000
    print(f"Execution time: {duration:.2f} ms")
    
    # Check execution plan
    print("\nEXPLAIN QUERY PLAN:")
    cursor.execute(f"EXPLAIN QUERY PLAN {query}")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- Facility Intensity Aggregation Benchmark ---")
    query2 = """
    SELECT facility_id, SUM(total_co2e) 
    FROM emissions 
    GROUP BY facility_id
    """
    start = time.perf_counter()
    cursor.execute(query2)
    results = cursor.fetchall()
    duration = (time.perf_counter() - start) * 1000
    print(f"Execution time: {duration:.2f} ms")
    
    print("\nEXPLAIN QUERY PLAN:")
    cursor.execute(f"EXPLAIN QUERY PLAN {query2}")
    for row in cursor.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    benchmark_queries()
