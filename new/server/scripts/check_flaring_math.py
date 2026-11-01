import sqlite3

conn = sqlite3.connect('new/server/ghg_app.db')
c = conn.cursor()

c.execute("""
    SELECT 
        count(*),
        sum(quantity),
        sum(co2_emissions),
        sum(ch4_emissions),
        sum(n2o_emissions),
        sum(co2e_total)
    FROM emissions 
    WHERE lower(process_type) LIKE '%flar%'
""")
row = c.fetchone()
print(f'Count: {row[0]}')
print(f'Total Quantity: {row[1]:,.2f}')
print(f'CO2 tonnes: {row[2]:,.2f}')
print(f'CH4 tonnes: {row[3]:,.2f}')
print(f'N2O tonnes: {row[4]:,.2f}')
print(f'Total tCO2e: {row[5]:,.2f}')
if row[1] > 0:
    print(f'Overall factor (all rows): {row[5] * 1000 / row[1]:.4f} kg CO2e / m3')

# Inspect individual flaring records with their factors and quantities
c.execute("""
    SELECT id, process_type, fuel_type, quantity, unit, ef_used_co2, ef_used_ch4, ef_used_n2o, combustion_efficiency, co2e_total
    FROM emissions 
    WHERE lower(process_type) LIKE '%flar%'
    LIMIT 10
""")
print("\nSample rows:")
for r in c.fetchall():
    print(r)
