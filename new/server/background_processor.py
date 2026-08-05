import threading
import uuid
import os
import csv
import traceback
from datetime import datetime
from openpyxl import load_workbook
import copy

# Global in-memory job tracker
# Structure: { job_id: { 'status', 'progress', 'processed', 'total', 'skipped': [{row, reason, ...}], 'error_csv_path' } }
upload_jobs = {}

def start_background_upload(app, file_path, original_filename, user_id, global_factor_type):
    job_id = str(uuid.uuid4())
    upload_jobs[job_id] = {
        'status': 'processing',
        'progress': 0,
        'processed': 0,
        'total': 0,
        'errors': [],       # fatal/global errors
        'skipped': [],      # per-row skip reasons [{row, reason, date, facility, ...}]
        'error_csv_path': None
    }
    
    # Spawn the background thread
    thread = threading.Thread(
        target=_process_file_thread, 
        args=(app, job_id, file_path, original_filename, user_id, global_factor_type)
    )
    thread.daemon = True
    thread.start()
    
    return job_id

def get_job_status(job_id):
    job = upload_jobs.get(job_id)
    if not job:
        return None
    skipped_all = job.get('skipped', [])
    return {
        'status':         job['status'],
        'progress':       job['progress'],
        'processed':      job['processed'],
        'total':          job['total'],
        'errors':         job.get('errors', []),
        'skipped_count':  len(skipped_all),
        'skipped_preview': skipped_all[:100],   # first 100 for inline display
        'error_csv_path': job.get('error_csv_path'),
    }

def _process_file_thread(app, job_id, file_path, original_filename, user_id, global_factor_type):
    with app.app_context():
        try:
            is_excel = original_filename.lower().endswith('.xlsx')
            
            headers = []
            rows_iterator = None
            wb = None
            f = None
            
            # 1. Open File & Extract Headers
            tier3_data_map = {}
            if is_excel:
                wb = load_workbook(file_path, read_only=True, data_only=True)
                
                # Check for Gas Composition and Tier 3 sheets
                for sheet_name in wb.sheetnames:
                    if sheet_name == 'Gas Composition' or sheet_name.startswith('⚙ '):
                        t3_ws = wb[sheet_name]
                        # Tier 3 sheets have headers on row 3, but let's just find the header row by looking for 'Equipment ID'
                        t3_iter = t3_ws.iter_rows(values_only=True)
                        t3_headers = []
                        for row in t3_iter:
                            str_row = [str(c).strip().lower() if c is not None else '' for c in row]
                            if 'equipment id' in str_row:
                                t3_headers = str_row
                                break
                        
                        if not t3_headers: continue
                        
                        # Read data rows
                        for t3_row in t3_iter:
                            if not any(t3_row): continue
                            row_dict = dict(zip(t3_headers, t3_row))
                            eq_id = str(row_dict.get('equipment id') or '').strip()
                            if eq_id:
                                if eq_id not in tier3_data_map:
                                    tier3_data_map[eq_id] = {}
                                tier3_data_map[eq_id].update(row_dict)
                
                ws = wb['Data Entry'] if 'Data Entry' in wb.sheetnames else wb.active
                rows_iterator = ws.iter_rows(values_only=True)
                headers_tuple = next(rows_iterator, [])
                headers = [str(h).strip() if h is not None else '' for h in headers_tuple]
                
                total_rows = ws.max_row - 1 if ws.max_row else 0
            else:
                f = open(file_path, 'r', encoding='utf-8-sig')
                reader = csv.reader(f)
                headers = next(reader, [])
                headers = [h.strip() for h in headers]
                rows_iterator = reader
                total_rows = 0
            
            upload_jobs[job_id]['total'] = total_rows
            
            # 2. Setup Field Mappings (Fuzzy Match)
            mapping = _build_mapping(headers)
            
            # 3. Setup context variables for calculation
            from models import Facility, CustomFactor, Emission
            from extensions import db
            from calculations import compute_emissions
            from emission_factors import API_FACTORS
            
            all_facilities = Facility.query.all()
            fac_name_map = { f.name.lower(): f for f in all_facilities }
            fac_id_map = { str(f.id): f for f in all_facilities }
            
            custom_factors = CustomFactor.query.filter_by(created_by=user_id).all()
            cf_name_map = { cf.name.lower(): cf for cf in custom_factors }
            
            processed = 0
            chunk = []
            skipped_rows = [] # Store raw row data for error CSV
            
            # Headers for error CSV
            error_headers = ['Error Reason'] + headers
            
            for raw_row in rows_iterator:
                # Stop if empty row (Excel read_only sometimes yields empty trailing rows)
                if not any(raw_row):
                    continue
                    
                processed += 1
                
                # Zip headers with row values safely
                row_dict = {}
                for i, h in enumerate(headers):
                    if i < len(raw_row):
                        row_dict[h] = raw_row[i]
                    else:
                        row_dict[h] = None
                        
                # Extract mapped values
                mapped_data = {}
                for sys_key, header_name in mapping.items():
                    if header_name:
                        mapped_data[sys_key] = row_dict.get(header_name)
                
                # Merge Tier 3 / Gas Composition if present
                eq_id_raw = str(mapped_data.get('equipment') or '').strip()
                if eq_id_raw and eq_id_raw in tier3_data_map:
                    mapped_data.update(tier3_data_map[eq_id_raw])
                        
                # Process Row
                emission_obj, row_errors = _process_row(
                    mapped_data, 
                    user_id, 
                    fac_name_map, 
                    fac_id_map,
                    cf_name_map, 
                    compute_emissions,
                    API_FACTORS,
                    global_factor_type
                )
                
                if row_errors:
                    skip_entry = {
                        'row': processed,
                        'reason': '; '.join(row_errors),
                        'date':     mapped_data.get('date', ''),
                        'facility': mapped_data.get('facility_name', ''),
                        'process':  mapped_data.get('process', ''),
                        'fuel':     mapped_data.get('fuel', ''),
                        'quantity': mapped_data.get('quantity', ''),
                    }
                    upload_jobs[job_id]['skipped'].append(skip_entry)
                    # Also keep flat list for CSV
                    skipped_list = ['; '.join(row_errors)]
                    skipped_list.extend([str(row_dict.get(h, '')) for h in headers])
                    skipped_rows.append(skipped_list)
                elif emission_obj:
                    chunk.append(emission_obj)
                    
                # Commit chunks of 2000
                if len(chunk) >= 2000:
                    db.session.bulk_save_objects(chunk)
                    db.session.commit()
                    chunk = []
                    
                # Update progress every 100 rows
                if processed % 100 == 0:
                    upload_jobs[job_id]['processed'] = processed
                    if total_rows > 0:
                        upload_jobs[job_id]['progress'] = min(99, int((processed / total_rows) * 100))
                        
            # Final chunk commit
            if chunk:
                db.session.bulk_save_objects(chunk)
                db.session.commit()
                
            upload_jobs[job_id]['processed'] = processed
            upload_jobs[job_id]['progress'] = 100
            upload_jobs[job_id]['status'] = 'completed'
            
            # Generate Error CSV if needed
            if skipped_rows:
                error_file = file_path + "_errors.csv"
                with open(error_file, 'w', newline='', encoding='utf-8') as ef:
                    writer = csv.writer(ef)
                    writer.writerow(error_headers)
                    writer.writerows(skipped_rows)
                upload_jobs[job_id]['error_csv_path'] = error_file
                
        except Exception as e:
            traceback.print_exc()
            upload_jobs[job_id]['status'] = 'error'
            upload_jobs[job_id]['errors'].append(f"Fatal error: {str(e)}")
            
        finally:
            if wb:
                wb.close()
            if f:
                f.close()
            # Clean up the original uploaded file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass


def _build_mapping(headers):
    # Matches the exact UI table headers to backend keys
    EXPECTED_FIELDS = [
        ('date', 'date'), 
        ('activity', 'activity'), 
        ('division', 'division'),
        ('field', 'field'), 
        ('facility_name', 'region'), # Region maps to Facility
        ('group', 'emission source'), # Emission Source maps to Group
        ('equipment', 'equipment'), 
        ('process', 'process'), 
        ('fuel', 'fuel'), ('fuel', 'activity/fuel'),
        ('factor_type', 'factor type'), 
        ('quantity', 'quantity'), 
        ('unit', 'unit'),
        ('year', 'year'), 
        ('month', 'month'),
        ('combustion_efficiency', 'combustion eff'),
        ('flare_type', 'flare type'),
        ('control_efficiency', 'control eff'),
        ('tank_gor', 'tank gor'),
        ('gor', 'gor'),
        ('pneu_count', 'pneumatic count'),
        ('pneu_bleed_rate', 'bleed rate'),
        ('pneu_hours', 'hours'),
        ('well_depth', 'well depth'),
        ('unload_diam', 'diameter'),
        ('unload_press', 'pressure'),
        ('unload_freq', 'events'),
        ('blowdown_volume', 'blowdown volume'),
        ('fugitive_method', 'fugitive method'),
        ('fugitive_ppm', 'ppm'),
        ('dehy_throughput', 'dehydrator throughput'),
        ('dehy_ch4_content', 'dehy ch4'),
        ('agr_throughput', 'agr throughput'),
        ('agr_co2_in', 'co2 in'),
        ('agr_co2_out', 'co2 out'),
        ('c1', 'c1 mol'), ('c2', 'c2 mol'), ('c3', 'c3 mol'), ('c4', 'c4 mol'), 
        ('c5', 'c5 mol'), ('c6', 'c6'), ('c7', 'c7'), ('c8', 'c8'), 
        ('c9', 'c9'), ('c10', 'c10'), ('n2', 'n2 mol'), ('hhv', 'hhv'),
        ('user_unc_co2', 'user uncertainty co2'),
        ('user_unc_ch4', 'user uncertainty ch4'),
        ('user_unc_n2o', 'user uncertainty n2o')
    ]
    
    mapping = {}
    for h in headers:
        h_lower = str(h).lower()
        for sys_key, search_term in EXPECTED_FIELDS:
            if sys_key not in mapping:
                if search_term in h_lower:
                    mapping[sys_key] = h
                    break
    return mapping


def _process_row(row, user_id, fac_name_map, fac_id_map, cf_name_map, compute_emissions_fn, API_FACTORS_dict, global_factor_type):
    """
    Validates a single mapped row and runs calculation via compute_emissions.
    Returns (Emission_Object, list_of_errors)
    """
    from models import Emission
    errors = []

    # Skip instructional walkthrough rows
    if str(row.get('date', '')).strip().upper().startswith('[INSTRUCTION]'):
        return None, []

    # 1. Parse Date
    date_str = str(row.get('date') or '').strip()
    year, month = None, None
    if date_str and date_str != 'None':
        try:
            parts = date_str.split('-')
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
        except:
            pass

    if not year:
        try:
            year = int(row.get('year') or 0)
            month = int(row.get('month') or 1)
        except:
            pass

    if not year:
        return None, ["Missing valid date or year."]

    # 2. Resolve Facility
    fac_raw = str(row.get('facility_name') or '').strip()
    facility = fac_id_map.get(fac_raw) or fac_name_map.get(fac_raw.lower())
    if not facility:
        return None, [f"Facility '{fac_raw}' not found."]

    # 3. Quantity
    try:
        amount = float(row.get('quantity') or 0)
    except:
        return None, [f"Invalid quantity: {row.get('quantity')}"]

    process_type = str(row.get('process') or '').strip()
    fuel        = str(row.get('fuel') or '').strip()
    unit        = str(row.get('unit') or 'm3').strip()

    if not process_type:
        return None, ["Missing process type."]

    # 4. Resolve emission factor (same logic as emissions route)
    factor_type_raw = str(row.get('factor_type') or '').lower()
    factor_source = global_factor_type if global_factor_type != 'auto' else (
        'custom' if factor_type_raw == 'custom' else 'default'
    )

    factor_data = {}
    if factor_source == 'custom':
        cf = cf_name_map.get(fuel.lower())
        if cf:
            factor_data = {
                'co2': cf.co2_factor, 'ch4': cf.ch4_factor,
                'n2o': cf.n2o_factor, 'co': cf.co_factor,
                'unit': cf.unit, 'hhv': cf.hhv_factor,
                'type': 'custom', 'name': cf.name,
                'uncertainty': {
                    'co2': float(getattr(cf, 'co2_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,
                    'ch4': float(getattr(cf, 'ch4_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,
                    'n2o': float(getattr(cf, 'n2o_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0
                }
            }
        else:
            factor_data = API_FACTORS_dict.get(fuel, {})
    else:
        factor_data = API_FACTORS_dict.get(fuel, {})

    # 5. Build calc_data payload (mirrors what the emissions route sends)
    calc_data = {
        'year': year, 'month': month,
        'facility_id': facility.id,
        'process_type': process_type,
        'fuel': fuel,
        'amount': amount,
        'unit': unit,
        'factor_source': factor_source,
    }
    
    # Inject all other optional variables dynamically (e.g. C1-C10, flare_type, etc.)
    for k, v in row.items():
        if k not in calc_data and v is not None:
            val = str(v).strip()
            if val:
                try:
                    calc_data[k] = float(val)
                except ValueError:
                    calc_data[k] = val
                    
    # Defaults if missing
    if 'ch4_content' not in calc_data: calc_data['ch4_content'] = 85.0
    if 'co2_content' not in calc_data: calc_data['co2_content'] = 2.0

    # 6. Run calculation
    try:
        em_result, _method = compute_emissions_fn(calc_data, factor_data)

        co2_val = float(em_result.get('co2') or 0)
        ch4_val = float(em_result.get('ch4') or 0)
        n2o_val = float(em_result.get('n2o') or 0)
        total   = float(em_result.get('totalCo2e') or (co2_val + ch4_val * 28 + n2o_val * 265))

        # 7. Uncertainty extraction
        api_res = em_result.get('_full_api_res')
        if api_res:
            unc = {
                'co2': api_res['results']['co2'].get('uncertainty', None) if isinstance(api_res['results']['co2'], dict) else None,
                'ch4': api_res['results']['ch4'].get('uncertainty', None) if isinstance(api_res['results']['ch4'], dict) else None,
                'n2o': api_res['results']['n2o'].get('uncertainty', None) if isinstance(api_res['results']['n2o'], dict) else None
            }
        else:
            unc_raw = factor_data.get('uncertainty', {})
            unc = {
                'co2': unc_raw.get('co2', None) if isinstance(unc_raw, dict) else None,
                'ch4': unc_raw.get('ch4', None) if isinstance(unc_raw, dict) else None,
                'n2o': unc_raw.get('n2o', None) if isinstance(unc_raw, dict) else None
            }

        # User Overrides
        for gas, field in [('co2', 'user_unc_co2'), ('ch4', 'user_unc_ch4'), ('n2o', 'user_unc_n2o')]:
            val = row.get(field)
            if val not in [None, '']:
                try:
                    unc[gas] = float(str(val).strip()) / 100.0
                except ValueError:
                    pass

        import uuid
        import json
        
        emission = Emission(
            record_id=str(uuid.uuid4()),
            created_by=user_id,
            facility_id=facility.id,
            activity=row.get('activity', facility.activity),
            division=row.get('division', facility.division),
            field=row.get('field', facility.field),
            group_name=row.get('group', ''),
            equipment_id=row.get('equipment', ''),
            process_type=process_type,
            fuel_type=fuel,
            quantity=amount,
            unit=unit,
            year=year,
            month=month,
            co2_emissions=co2_val,
            ch4_emissions=ch4_val,
            n2o_emissions=n2o_val,
            co2e_total=total,
            calc_method=_method,
            source_payload=json.dumps(calc_data),
            factor_source=factor_data.get('type', 'API'),
            ef_used_co2=factor_data.get('co2', 0),
            ef_used_ch4=factor_data.get('ch4', 0),
            ef_used_n2o=factor_data.get('n2o', 0),
            uncertainty=unc.get('co2', None) if isinstance(unc, dict) else (unc or None),
            uncertainty_ch4=unc.get('ch4', None) if isinstance(unc, dict) else (unc or None),
            uncertainty_n2o=unc.get('n2o', None) if isinstance(unc, dict) else (unc or None),
            status='Verified'
        )
        return emission, []

    except Exception as e:
        return None, [f"Calculation error: {str(e)}"]

