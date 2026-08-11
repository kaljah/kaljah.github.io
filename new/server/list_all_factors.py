from emission_factors_api2021 import API_FACTORS, EQUIPMENT_FACTORS, VENTED_FACTORS

print("=== API_FACTORS keys ===")
for k in sorted(API_FACTORS.keys()):
    f = API_FACTORS[k]
    print(
        f"API: {k} -> cat={f.get('process_category')} | co2={f.get('co2')} | ch4={f.get('ch4')}"
    )

print("\n=== EQUIPMENT_FACTORS keys ===")
for k in sorted(EQUIPMENT_FACTORS.keys()):
    f = EQUIPMENT_FACTORS[k]
    print(
        f"EQ: {k} -> cat={f.get('process_category')} | co2={f.get('co2')} | ch4={f.get('ch4')}"
    )

print("\n=== VENTED_FACTORS keys ===")
for k in sorted(VENTED_FACTORS.keys()):
    f = VENTED_FACTORS[k]
    print(
        f"VENT: {k} -> cat={f.get('process_category')} | co2={f.get('co2')} | ch4={f.get('ch4')}"
    )
