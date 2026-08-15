import re

with open('background_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

eeio_processor = """def _process_row_scope3_eeio(row, user_id, fac_name_map, fac_id_map):
    from models import Scope3Emission
    from emission_factors.eeio_factors import get_eeio_factor

    errors = []

    # 1. Parse Date
    date_str = str(row.get("date") or "").strip()
    year = int(row.get("year") or 2024)
    month = int(row.get("month") or 1)
    if date_str and date_str != "None":
        try:
            parts = date_str.split("-")
            year = int(parts[0])
            if len(parts) > 1:
                month = int(parts[1])
        except:
            pass

    if not year or not month:
        return None, ["Missing valid date (YYYY-MM) or separate year and month columns"]

    # 2. Resolve Facility
    fac_raw = str(row.get("facility_name") or row.get("facility_id") or "").strip()
    facility = fac_id_map.get(fac_raw) or fac_name_map.get(fac_raw.lower())
    if not facility:
        return None, [f"Facility '{fac_raw}' not found"]

    # 3. Resolve NAICS and Spend
    naics = str(row.get("naics_code") or "").strip()
    try:
        spend_usd = float(row.get("spend_usd") or 0)
    except:
        return None, [f"Invalid spend amount: {row.get('spend_usd')}"]

    if spend_usd <= 0:
        return None, ["Spend amount must be greater than zero"]

    # 4. Calculate
    factor_data = get_eeio_factor(naics)
    spend_k = spend_usd / 1000.0
    kg_co2e = spend_k * factor_data["kg_co2e_per_1000_usd"]
    tonnes_co2e = kg_co2e / 1000.0

    emission = Scope3Emission(
        facility_id=facility.id,
        year=year,
        month=month,
        category="Category 1",
        sub_category=f"Spend-based: {factor_data['name']} (NAICS {naics})",
        activity_data=spend_usd,
        unit="USD",
        emission_factor=factor_data["kg_co2e_per_1000_usd"],
        co2e=tonnes_co2e,
        calculation_method="Spend-based (EEIO)",
        data_quality="Average-data method",
        notes=row.get("notes", "Bulk Imported via EEIO"),
        created_by=user_id,
        status="Pending",
    )
    return emission, errors

def _process_row_scope3("""

content = content.replace("def _process_row_scope3(", eeio_processor)

routing = """                elif str(scope) == "3_eeio":
                    emission_obj, row_errors = _process_row_scope3_eeio(
                        mapped_data, user_id, fac_name_map, fac_id_map
                    )
                elif str(scope) == "3":"""

content = content.replace('                elif str(scope) == "3":', routing)

with open('background_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done inserting Scope 3 EEIO processor")
