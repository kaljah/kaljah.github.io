from flask import request, jsonify, session
from sqlalchemy import func
from . import emissions_bp
from utils import get_current_user, get_allowed_facility_ids
from models import User, Emission, ActivityLog, Scope2Emission, Scope3Emission, ProductionData, Goal, Notification, CustomFactor, Facility
from extensions import db
from utils import log_activity_and_notify
from calculations import compute_emissions, propagate_uncertainty, convert, calculate_co2e
from calculations.constants import DEFAULT_GWP, GWP_AR4, GWP_AR5, GWP_AR6
from emission_factors import API_FACTORS
from routes.auth import admin_required, login_required
import datetime
import math
import uuid
import json
from sqlalchemy import cast, String, literal, Float, desc, union_all, select, or_

def get_current_user():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None  # EXTRA-02 FIX: replaced deprecated query.get

def _escape_like(val: str) -> str:
    """NEW-07 FIX: Escape SQL LIKE wildcards in user-supplied search strings."""
    return val.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

@emissions_bp.route('/', methods=['GET'])
@login_required  # SEC-01 FIX: was missing, route was unauthenticated
def get_emissions():
    from flask import current_app
    user = get_current_user()
    if user:
        current_app.logger.info(f"[Emissions] Fetch requested by user_id: {user.id}")
    else:
        current_app.logger.info("[Emissions] Fetch requested by anonymous user")
        
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    # Parameters from request
    limit_arg = request.args.get('limit', '50')
    offset_arg = request.args.get('offset', '0')
    
    # Handle both 'page' and 'limit/offset' pagination
    if 'limit' in request.args and 'offset' in request.args:
        try:
            per_page = int(limit_arg)
            offset = int(offset_arg)
            page = (offset // per_page) + 1
        except (ValueError, TypeError, ZeroDivisionError):
            per_page = 50
            page = 1
    else:
        page = request.args.get('page', 1, type=int)
        if limit_arg == 'all':
            per_page = 5000  # SEC-10 FIX: hard cap — was 1,000,000 (DoS vector)
        else:
            try:
                per_page = int(limit_arg)
            except ValueError:
                per_page = 50
    
    scope = request.args.get('scope', 'all')
    year = request.args.get('year')
    month = request.args.get('month')
    facility_id = request.args.get('facilityId') or request.args.get('facility_id')
    process_type = request.args.get('process') or request.args.get('process_type')
    division_arg = request.args.get('division')
    field_arg = request.args.get('field')
    search_term = request.args.get('search')
    method_arg = request.args.get('method')
    
    results = []
    
    # helper to apply common filters
    def apply_filters(q, model, filter_model=None):
        fm = filter_model or model
        allowed_fids = get_allowed_facility_ids(user)
        if allowed_fids is not None:
            if hasattr(model, 'facility_id'):
                q = q.filter(model.facility_id.in_(allowed_fids))
            elif model == Facility:
                q = q.filter(Facility.id.in_(allowed_fids))
            else:
                q = q.filter(model.id == -1) # Restrict fully if unknown model
        
        nonlocal year
        if year == 'baseline':
            from models import BaseYear
            base = BaseYear.query.first()
            year = str(base.year) if base else '2020'
            
        if year and year != 'all':
            try:
                q = q.filter(model.year == int(year))
            except ValueError:
                pass
        if month and month != 'all':
            try:
                q = q.filter(model.month == int(month))
            except ValueError:
                pass
        if facility_id and facility_id != 'all':
            try:
                q = q.filter(model.facility_id == int(facility_id))
            except ValueError:
                pass
        # NEW-07 FIX: escape LIKE wildcards before filtering
        if division_arg and division_arg != 'all':
            q = q.filter(fm.division.ilike(f"%{_escape_like(division_arg.strip())}%", escape='\\'))
        if field_arg and field_arg != 'all':
            q = q.filter(fm.field.ilike(f"%{_escape_like(field_arg.strip())}%", escape='\\'))
        
        if method_arg and method_arg != 'all':
            if hasattr(model, 'calc_method'):
                q = q.filter(model.calc_method.ilike(f"%{_escape_like(method_arg)}%", escape='\\'))
            elif hasattr(model, 'calculation_method'):
                q = q.filter(model.calculation_method.ilike(f"%{_escape_like(method_arg)}%", escape='\\'))
            
        if search_term:
            from sqlalchemy import or_
            safe_term = _escape_like(search_term)
            search_filters = []
            if hasattr(model, 'process_type'): search_filters.append(model.process_type.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'fuel_type'): search_filters.append(model.fuel_type.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'activity'): search_filters.append(model.activity.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'group_name'): search_filters.append(model.group_name.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'equipment_id'): search_filters.append(model.equipment_id.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'division'): search_filters.append(model.division.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'field'): search_filters.append(model.field.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'category'): search_filters.append(model.category.ilike(f"%{safe_term}%", escape='\\'))
            if hasattr(model, 'sub_category'): search_filters.append(model.sub_category.ilike(f"%{safe_term}%", escape='\\'))
            
            if search_filters:
                q = q.filter(or_(*search_filters))
                
        return q

    queries = []

    # 1. SCOPE 1
    if scope in ['all', '1', 'scope1']:
        s1_query = apply_filters(Emission.query, Emission)
        if process_type and process_type != 'all':
            s1_query = s1_query.filter(Emission.process_type == process_type)
        
        # Outer join to avoid losing records if facility link is missing
        s1_query = s1_query.outerjoin(Facility, Emission.facility_id == Facility.id)
            
        sel1 = s1_query.with_entities(
            (literal('s1_') + cast(Emission.id, String)).label('id'),
            literal(1).label('scope'),
            Emission.year.label('year'),
            Emission.month.label('month'),
            Emission.facility_id.label('facility_id'),
            Facility.name.label('facility_name'), # Joined name
            Emission.group_name.label('group_name'),
            Emission.activity.label('activity'),
            Emission.process_type.label('process_type'),
            Emission.fuel_type.label('fuel'),
            Emission.quantity.label('amount'),
            Emission.unit.label('unit'),
            Emission.co2_emissions.label('co2_emissions'),
            Emission.ch4_emissions.label('ch4_emissions'),
            Emission.n2o_emissions.label('n2o_emissions'),
            Emission.co2e_total.label('co2e_total'),
            Emission.status.label('status'),
            Emission.timestamp.label('timestamp'),
            Emission.division.label('division'),
            Emission.field.label('field'),
            Emission.equipment_id.label('equipment_id'),
            Emission.calc_method.label('factor_type'),
            Facility.region.label('region'),
            Emission.source_payload.label('source_payload'),
            Emission.uncertainty.label('uncertainty_co2'),
            Emission.uncertainty_ch4.label('uncertainty_ch4'),
            Emission.uncertainty_n2o.label('uncertainty_n2o')
        )
        current_app.logger.info(f"[Emissions] Scope 1 count: {sel1.count()}")
        queries.append(sel1)

    # 2. SCOPE 2
    if scope in ['all', '2', 'scope2']:
        s2_query = apply_filters(Scope2Emission.query, Scope2Emission)
        
        # Outer join
        s2_query = s2_query.outerjoin(Facility, Scope2Emission.facility_id == Facility.id)
        
        sel2 = s2_query.with_entities(
            (literal('s2_') + cast(Scope2Emission.id, String)).label('id'),
            literal(2).label('scope'),
            Scope2Emission.year.label('year'),
            Scope2Emission.month.label('month'),
            Scope2Emission.facility_id.label('facility_id'),
            Facility.name.label('facility_name'), # Joined name
            literal('N/A').label('group_name'),
            Scope2Emission.activity.label('activity'),
            literal('Scope 2').label('process_type'),
            Scope2Emission.grid_region.label('fuel'),
            Scope2Emission.electricity_kwh.label('amount'),
            literal('kWh').label('unit'),
            cast(literal(0), Float).label('co2_emissions'),
            cast(literal(0), Float).label('ch4_emissions'),
            cast(literal(0), Float).label('n2o_emissions'),
            Scope2Emission.co2e.label('co2e_total'),
            Scope2Emission.status.label('status'),
            Scope2Emission.created_at.label('timestamp'),
            Scope2Emission.division.label('division'),
            Scope2Emission.field.label('field'),
            literal('N/A').label('equipment_id'),
            literal('Location-based').label('factor_type'),
            Facility.region.label('region'),
            literal(None).label('source_payload'),
            cast(literal(None), Float).label('uncertainty_co2'),
            cast(literal(None), Float).label('uncertainty_ch4'),
            cast(literal(None), Float).label('uncertainty_n2o')
        )
        current_app.logger.info(f"[Emissions] Scope 2 count: {sel2.count()}")
        queries.append(sel2)

    # 3. SCOPE 3
    if scope in ['all', '3', 'scope3']:
        # Outer join
        s3_base_query = Scope3Emission.query.outerjoin(Facility, Scope3Emission.facility_id == Facility.id)
        s3_query = apply_filters(s3_base_query, Scope3Emission, Facility)
        
        sel3 = s3_query.with_entities(
            (literal('s3_') + cast(Scope3Emission.id, String)).label('id'),
            literal(3).label('scope'),
            Scope3Emission.year.label('year'),
            Scope3Emission.month.label('month'),
            Scope3Emission.facility_id.label('facility_id'),
            Facility.name.label('facility_name'), # Joined name
            literal('N/A').label('group_name'),
            literal('Value Chain').label('activity'),
            Scope3Emission.category.label('process_type'),
            Scope3Emission.sub_category.label('fuel'),
            Scope3Emission.activity_data.label('amount'),
            Scope3Emission.unit.label('unit'),
            cast(literal(0), Float).label('co2_emissions'),
            cast(literal(0), Float).label('ch4_emissions'),
            cast(literal(0), Float).label('n2o_emissions'),
            Scope3Emission.co2e.label('co2e_total'),
            Scope3Emission.status.label('status'),
            Scope3Emission.created_at.label('timestamp'),
            Facility.division.label('division'),
            Facility.field.label('field'),
            literal('N/A').label('equipment_id'),
            Scope3Emission.calculation_method.label('factor_type'),
            Facility.region.label('region'),
            literal(None).label('source_payload'),
            cast(literal(None), Float).label('uncertainty_co2'),
            cast(literal(None), Float).label('uncertainty_ch4'),
            cast(literal(None), Float).label('uncertainty_n2o')
        )
        print(f"[Emissions] Scope 3 count: {sel3.count()}")
        queries.append(sel3)

    # Combine queries
    if len(queries) == 1:
        u = queries[0].subquery()
    else:
        u = union_all(*queries).subquery()
    
    # Get total count safely with detailed logging
    try:
        total = db.session.query(func.count()).select_from(u).scalar() or 0
    except Exception as count_err:
        current_app.logger.error(f"[Emissions] Count Query failed: {count_err}")
        total = 0
    
    # Paginate and sort
    stmt = db.session.query(u).order_by(u.c.timestamp.desc().nullslast())
    
    if limit_arg != 'all':
        start = (page - 1) * per_page
        stmt = stmt.offset(start).limit(per_page)
        
    records = stmt.all()
    
    # Resolve facility names
    facility_ids = set(r.facility_id for r in records if r.facility_id)
    facilities = {f.id: f.name for f in Facility.query.filter(Facility.id.in_(facility_ids)).all()} if facility_ids else {}

    paginated_results = []
    for r in records:
        f_name = r.facility_name
        if not f_name or f_name == 'Unknown':
            f_name = facilities.get(r.facility_id, 'Unknown')
            
        d = {
            'id': r.id,
            'scope': r.scope,
            'year': r.year,
            'month': r.month,
            'facility_id': r.facility_id,
            'facility_name': f_name,
            'activity': r.activity,
            'process_type': r.process_type,
            'fuel': r.fuel,
            'amount': r.amount,
            'unit': r.unit,
            'co2_emissions': r.co2_emissions,
            'ch4_emissions': r.ch4_emissions,
            'n2o_emissions': r.n2o_emissions,
            'co2e_total': r.co2e_total,
            'status': getattr(r, 'status', 'Verified'),
            'timestamp': r.timestamp.isoformat() if r.timestamp else None,
            'division': r.division,
            'field': r.field,
            'group_name': r.group_name,
            'equipment_id': r.equipment_id,
            'factor_type': r.factor_type,
            'region': getattr(r, 'region', None),
            'uncertainty_co2': getattr(r, 'uncertainty_co2', None),
            'uncertainty_ch4': getattr(r, 'uncertainty_ch4', None),
            'uncertainty_n2o': getattr(r, 'uncertainty_n2o', None)
        }
        if r.scope == 1 and hasattr(r, 'source_payload') and getattr(r, 'source_payload', None):
            import json
            try:
                payload = json.loads(r.source_payload)
                d['factor_source'] = payload.get('factor_source')
            except Exception:
                pass
        paginated_results.append(d)
    
    return jsonify({
        'data': paginated_results,
        'emissions': paginated_results,
        'total': total,
        'pages': (total // per_page) + (1 if total % per_page > 0 else 0) if limit_arg != 'all' else 1,
        'current_page': page
    })

# Helper: Get GWP based on user prefs and global settings
def resolve_gwp_dict(user=None):
    import json
    from calculations.constants import get_active_gwp
    try:
        prefs = json.loads(user.preferences or '{}') if user and user.preferences else {}
        model = prefs.get('gwp_standard') or prefs.get('gwpModel')
        if model in ['AR4', 'AR5', 'AR6']:
            return get_active_gwp(standard=model)
    except Exception:
        pass
    return get_active_gwp()

def resolve_gwp_standard(user=None):
    import json
    try:
        prefs = json.loads(user.preferences or '{}') if user and user.preferences else {}
        model = prefs.get('gwp_standard') or prefs.get('gwpModel')
        if model in ['AR4', 'AR5', 'AR6']:
            return model
    except Exception:
        pass
    try:
        from routes.auth import _app_settings
        return _app_settings.get('gwp_standard', 'AR5')
    except Exception:
        return 'AR5'

@emissions_bp.route('/bulk-upload', methods=['POST'])
@login_required
def add_bulk_upload():
    from datetime import datetime
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    records = data.get('records', [])
    date_format = data.get('date_format', 'YYYY-MM-DD')
    global_factor_type = data.get('global_factor_type', 'auto')
    confirm = data.get('confirm', False)
    
    allowed_facilities = get_allowed_facility_ids(user)
    
    # Map frontend date format strings to strptime formats
    fmt_map = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'MM/DD/YYYY': '%m/%d/%Y',
        'DD/MM/YYYY': '%d/%m/%Y',
        'YYYY-MM': '%Y-%m',
        'MM/YYYY': '%m/%Y',
        'YYYY': '%Y'
    }
    py_fmt = fmt_map.get(date_format, '%Y-%m-%d')

    # Pre-fetch facilities and custom factors for resolution
    all_facilities = Facility.query.all()
    fac_name_map = { f.name.lower(): f for f in all_facilities }
    
    # Pre-fetch user's custom factors
    custom_factors = CustomFactor.query.filter_by(created_by=user.id).all()
    cf_name_map = { cf.name.lower(): cf for cf in custom_factors }

    valid_records = []
    errors = []
    duplicates = []
    new_emissions = []
    
    for idx, row in enumerate(records):
        row_num = idx + 1
        row_errors = []
        
        # 1. Parse Date
        date_str = row.get('date')
        if date_str:
            try:
                dt = datetime.strptime(str(date_str).strip(), py_fmt)
                year = dt.year
                month = dt.month
            except ValueError:
                row_errors.append(f"Invalid date format: {date_str} does not match {date_format}.")
                year, month = None, None
        else:
            year_val = row.get('year')
            month_val = row.get('month')
            if year_val and month_val:
                try:
                    year = int(year_val)
                    month = int(month_val)
                except ValueError:
                    row_errors.append(f"Invalid year/month: {year_val}/{month_val}")
                    year, month = None, None
            else:
                row_errors.append("Missing date or year/month.")
                year, month = None, None

        # 2. Resolve Facility
        fac_name = row.get('facility_name', row.get('facility_id', '')).strip()
        facility = None
        if fac_name:
            # Check ID match first if they provided a number
            if fac_name.isdigit():
                facility = next((f for f in all_facilities if str(f.id) == fac_name), None)
            # If not ID or not found, try name match
            if not facility:
                facility = fac_name_map.get(fac_name.lower())
                
            if not facility:
                row_errors.append(f"Facility not found: '{fac_name}'")
            elif allowed_facilities and facility.id not in allowed_facilities:
                row_errors.append(f"You do not have permission to add data for facility: '{fac_name}'")
        else:
            row_errors.append("Missing facility.")

        # 3. Handle Quantity/Amount
        amount_raw = row.get('quantity', row.get('amount'))
        try:
            amount = float(amount_raw)
        except (ValueError, TypeError):
            row_errors.append(f"Invalid quantity: {amount_raw}")
            amount = 0

        process_type = row.get('process', row.get('process_type', row.get('type', '')))
        fuel = row.get('fuel', row.get('fuel_type', ''))
        unit = row.get('unit', '')

        if not process_type:
            row_errors.append("Missing process type.")
        if not fuel and process_type not in ['Well Completions', 'Fugitive']: # Some processes might not need fuel
            row_errors.append("Missing fuel/activity.")

        # 4. Resolve Factor (Standard vs Custom vs Sparse Engineering)
        factor_type_raw = str(row.get('factor_type', '')).lower()
        if global_factor_type and global_factor_type != 'auto':
            factor_type = global_factor_type
        else:
            factor_type = factor_type_raw
            
        factor_data = {}
        
        if process_type == 'Flaring':
            # Option B: Sparse columns
            try:
                factor_data = {
                    'c1': float(row.get('c1', 0)),
                    'c2': float(row.get('c2', 0)),
                    'c3': float(row.get('c3', 0)),
                    'c4': float(row.get('c4', 0)),
                    'c5': float(row.get('c5', 0)),
                    'c6': float(row.get('c6', 0)),
                    'co2': float(row.get('co2_mol', 0)),
                    'n2': float(row.get('n2_mol', 0))
                }
            except ValueError:
                row_errors.append("Invalid engineering calculation inputs for Flaring.")
        elif factor_type == 'custom':
            cf = cf_name_map.get(fuel.lower())
            if not cf:
                row_errors.append(f"Custom factor not found for fuel: '{fuel}'. Please save it in the app first.")
            else:
                factor_data = {
                    'co2': cf.co2_factor,
                    'ch4': cf.ch4_factor,
                    'n2o': cf.n2o_factor,
                    'co': cf.co_factor,
                    'unit': cf.unit,
                    'hhv': cf.hhv_factor,
                    'type': 'custom',
                    'name': cf.name
                }
                if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                    factor_data['uncertainty'] = {

                        'co2': float(getattr(cf, 'co2_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,

                        'ch4': float(getattr(cf, 'ch4_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,

                        'n2o': float(getattr(cf, 'n2o_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0

                    }
                elif cf.uncertainty and cf.uncertainty > 0:
                    factor_data['uncertainty'] = { 'co2': float(cf.uncertainty or 0)/100.0, 'ch4': float(cf.uncertainty or 0)/100.0, 'n2o': float(cf.uncertainty or 0)/100.0 }
                elif cf.parent_fuel:
                    parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                    if 'uncertainty' in parent_factor:
                        factor_data['uncertainty'] = parent_factor['uncertainty']
        else:
            factor_data = API_FACTORS.get(fuel, {})
            if not factor_data and not row_errors and process_type not in ['Well Completions']:
                row_errors.append(f"Standard emission factor not found for: '{fuel}'")

        # 5. Check if row is clean to compute
        if row_errors:
            errors.append({"row": row_num, "reasons": row_errors, "original": row})
            continue

        # Base calc_data
        calc_data = {
            'year': year, 'month': month, 'facility_id': facility.id, 
            'process_type': process_type, 'fuel': fuel, 'amount': amount, 'unit': unit
        }
        
        # Inject all other optional variables dynamically
        has_specific = False
        specific_keys = {
            'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10', 'n2', 'co2_comp', 'h2s', 'flare_type', 'control_efficiency',
            'mud_type', 'comp_flare_eff', 'gor', 'flowback_days',
            'unload_depth', 'unload_diam', 'unload_press', 'unload_freq', 'unload_flare_eff',
            'blowdown_volume', 'blowdown_press', 'blowdown_temp', 'blowdown_ch4',
            'tank_gor', 'tank_press', 'tank_temp', 'tank_flare_eff',
            'pneumatic_type', 'pneumatic_count', 'pneumatic_hours',
            'agr_co2_in', 'agr_co2_out', 'agr_ch4_in',
            'dehy_pump_rate', 'dehy_pump_unit', 'dehy_hours', 'dehy_eff', 'dehy_ch4_content',
            'hhv', 'ef_unit', 'fuel_type',
            'boiler_eff', 'trans_loss', 'heat_unit',
            'total_emissions', 'heat_output', 'power_output', 'allocation_method',
            'carbon_content', 'molecular_weight',
            'ch4_content', 'co2_content'
        }

        for k, v in row.items():
            if k not in calc_data and v is not None:
                val = str(v).strip()
                if val:  # only include non-empty values
                    calc_data[k] = val
                    if k in specific_keys:
                        has_specific = True
        
        if has_specific:
            calc_data['factor_source'] = 'specific'
            
        # Ensure factor source is recorded cleanly if forced globally or provided in column
        if factor_type in ['default', 'custom', 'specific']:
            calc_data['factor_source'] = factor_type
        
        # 6. Compute
        gwp_dict = resolve_gwp_dict(user)
        gwp_std = resolve_gwp_standard(user)
        try:
            em_result, method = compute_emissions(calc_data, factor_data, gwp_dict=gwp_dict)
        except Exception as e:
            errors.append({"row": row_num, "reasons": [f"Calculation failed: {str(e)}"], "original": row})
            continue

        # Fallback GWP CO2e if missing
        if not em_result.get('totalCo2e') or em_result.get('totalCo2e') == 0:
            co2_val = em_result.get('co2', 0)
            ch4_val = em_result.get('ch4', 0)
            n2o_val = em_result.get('n2o', 0)
            em_result['totalCo2e'] = calculate_co2e(co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict)

        # Uncertainty
        api_res = em_result.get('_full_api_res')
        if api_res:
            uncertainty = {
                'co2': api_res['results']['co2'].get('uncertainty') if isinstance(api_res['results']['co2'], dict) else 0.05,
                'ch4': api_res['results']['ch4'].get('uncertainty') if isinstance(api_res['results']['ch4'], dict) else 0.15,
                'n2o': api_res['results']['n2o'].get('uncertainty') if isinstance(api_res['results']['n2o'], dict) else 0.15
            }
        else:
            uncertainty = factor_data.get('uncertainty', {})

        # Prepare Record
        rec_id = str(uuid.uuid4())
        emission_obj = Emission(
            record_id=rec_id,
            year=year,
            month=month,
            facility_id=facility.id,
            group_name=row.get('group', ''),
            activity=row.get('activity', facility.activity),
            division=row.get('division', facility.division),
            field=row.get('field', facility.field),
            process_type=process_type,
            fuel_type=fuel,
            quantity=amount,
            unit=unit,
            equipment_id=row.get('equipment', ''),
            co2_emissions=em_result['co2'],
            ch4_emissions=em_result['ch4'],
            n2o_emissions=em_result['n2o'],
            co_emissions=em_result.get('co', 0),
            co2e_total=em_result['totalCo2e'],
            calc_method=method,
            gwp_version=gwp_std,
            source_payload=json.dumps(calc_data),
            created_by=user.id,
            uncertainty=uncertainty.get('co2', None) if isinstance(uncertainty, dict) else (uncertainty or None),
            uncertainty_ch4=uncertainty.get('ch4', None) if isinstance(uncertainty, dict) else (uncertainty or None),
            uncertainty_n2o=uncertainty.get('n2o', None) if isinstance(uncertainty, dict) else (uncertainty or None),
            status='Verified'
        )
        
        # 7. Check for Duplicates
        duplicate = Emission.query.filter_by(
            year=year, month=month, facility_id=facility.id, 
            process_type=process_type, equipment_id=row.get('equipment', '')
        ).first()
        
        preview_data = {
            "row": row_num, "year": year, "month": month, "facility": facility.name,
            "process": process_type, "fuel": fuel, "amount": amount, "unit": unit,
            "co2e": round(em_result['totalCo2e'], 2)
        }

        if duplicate:
            duplicates.append(preview_data)
            # If confirm=True and they chose to overwrite, we'd update. 
            # For simplicity, if we are confirming and hit a duplicate, we can delete the old one and insert new.
            if confirm:
                db.session.delete(duplicate)
                new_emissions.append(emission_obj)
        else:
            valid_records.append(preview_data)
            if confirm:
                new_emissions.append(emission_obj)

    # 8. Finalize Database changes if confirming
    if confirm:
        if new_emissions:
            db.session.add_all(new_emissions)
            try:
                db.session.commit()
                # Create a single bulk audit log
                log_activity_and_notify(
                    action='CREATE', record_id='bulk', user=user, request=request,
                    entity='Emission', details=f"Bulk imported {len(new_emissions)} emissions via CSV"
                )
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': 'Failed to save to database', 'details': str(e)}), 500
        
        return jsonify({
            'status': 'success',
            'imported': len(new_emissions),
            'errors': errors
        })

    # If preview
    return jsonify({
        'status': 'preview',
        'valid_count': len(valid_records),
        'valid_records': valid_records,
        'duplicate_count': len(duplicates),
        'duplicates': duplicates,
        'errors': errors
    })


import os
import tempfile
from flask import send_file, Response
import openpyxl
from background_processor import start_background_upload, get_job_status

@emissions_bp.route('/template/csv', methods=['GET'])
def get_csv_template():
    import csv, io
    # Exact match of the UI data table columns
    headers = [
        '[Data Entry] Date (YYYY-MM)',
        '[Data Entry] Activity',
        '[Data Entry] Division',
        '[Data Entry] Field',
        '[Data Entry] Region / Facility',
        '[Data Entry] Emission Source (Group)',
        '[Data Entry] Equipment Name',
        '[Data Entry] Equipment ID',
        '[Data Entry] Process Type',
        '[Data Entry] Activity / Fuel',
        '[Data Entry] Factor Type',
        '[Data Entry] Quantity',
        '[Data Entry] Unit',
        # Engineering / Tier 3 columns
        '[Tier 3] CH4 Content (%)',
        '[Tier 3] CO2 Content (%)',
        '[Tier 3] HHV (Btu/scf)',
        '[Tier 3] C1 Mol%', '[Tier 3] C2 Mol%', '[Tier 3] C3 Mol%', '[Tier 3] C4 Mol%', '[Tier 3] C5 Mol%', '[Tier 3] C6 Mol%',
        '[Tier 3] C7 Mol%', '[Tier 3] C8 Mol%', '[Tier 3] C9 Mol%', '[Tier 3] C10 Mol%',
        '[Tier 3] N2 Mol%', '[Tier 3] CO2 Mol% (Gas Comp)',
        '[Tier 3] Flare Type',
        '[Tier 3] Flare Control Efficiency (%)',
        '[Tier 3] User Uncertainty CO2 (%)', '[Tier 3] User Uncertainty CH4 (%)', '[Tier 3] User Uncertainty N2O (%)',
        '[Tier 3] Mud Type',
        '[Tier 3] GOR (scf/bbl)',
        '[Tier 3] Flowback Days',
        '[Tier 3] Completions Flare Efficiency (%)',
        '[Tier 3] Well Depth (ft)',
        '[Tier 3] Casing Diameter (in)',
        '[Tier 3] Well Pressure (psia)',
        '[Tier 3] Unloading Events',
        '[Tier 3] Unloading Flare Efficiency (%)',
        '[Tier 3] Tank GOR (scf/bbl)',
        '[Tier 3] Tank API Gravity',
        '[Tier 3] Tank Control Efficiency (%)',
        '[Tier 3] Blowdown Volume (scf)',
        '[Tier 3] Blowdown Pressure (psia)',
        '[Tier 3] Blowdown Events',
        '[Tier 3] Pneumatic Device Count',
        '[Tier 3] Pneumatic Bleed Rate (scf/hr/device)',
        '[Tier 3] Pneumatic Hours',
        '[Tier 3] Fugitive Method',
        '[Tier 3] Leak Concentration (ppm)',
        '[Tier 3] Pipeline Length (km)',
        '[Tier 3] AGR Unit Type',
        '[Tier 3] AGR Flow Rate',
        '[Tier 3] AGR Flow Unit',
    ]
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    
    # Write Instruction Row
    instructions = [
        '[INSTRUCTION] Format: YYYY-MM',
        'Optional Reference',
        'Optional Reference',
        'Optional Reference',
        'Must exactly match a name from the Facilities sheet',
        'Optional Reference',
        'Optional Reference',
        'Link to Tier 3 Equipment ID',
        'Combustion, Flaring, Venting, etc.',
        'Gas/fuel type e.g. Natural Gas, Diesel',
        'default = API standard, custom = saved factor',
        'Numeric quantity (e.g. 50000)',
        'e.g. scf, m3, gal, bbl, kg',
        # Tier 3 
        'Default: 85.0',
        'Default: 2.0',
        'e.g. 1020',
        'Methane fraction', 'Ethane fraction', 'Propane fraction', 'Butane fraction', 'Pentane fraction', 'Hexane fraction',
        'Heptane fraction', 'Octane fraction', 'Nonane fraction', 'Decane+ fraction',
        'Nitrogen fraction', 'CO2 fraction',
        'e.g., elevated, enclosed_ground',
        'Combustion efficiency (%)',
        'Optional override', 'Optional override', 'Optional override',
        'e.g., water_based, synthetic',
        'Gas-to-Oil Ratio (scf/bbl)',
        'Days of flowback',
        'Efficiency (%)',
        'Depth in feet',
        'Diameter in inches',
        'Pressure in psia',
        'Number of events',
        'Efficiency (%)',
        'Gas-to-Oil Ratio (scf/bbl)',
        'API Gravity',
        'Efficiency (%)',
        'Volume in scf',
        'Pressure in psia',
        'Number of events',
        'Device count',
        'Bleed rate (scf/hr/device)',
        'Hours of operation',
        'e.g., epa_method_21',
        'PPM concentration',
        'Length in km',
        'e.g., amine, selexol',
        'Flow rate',
        'e.g., scf/day'
    ]
    cw.writerow(instructions)
    
    # Write 2 sample rows
    cw.writerow([
        '2024-01','Exploration & Production','Production','Hassi Messaoud','Field Alpha',
        'Compressor Station A','Caterpillar G3516','EQ-001','Combustion','Natural Gas',
        'default','50000','scf',
        '','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','',''
    ])
    cw.writerow([
        '2024-01','Exploration & Production','Production','Hassi Messaoud','Field Alpha',
        'Flare Stack B','HP Flare Stack','EQ-002','Flaring','Associated Gas',
        'default','120000','scf',
        '83','3','1000','85','5','4','2','1','1','2','1','elevated','95',
        '','','','','','','','','','','','','','','','','','','','','','',''
    ])
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=emissions_template.csv"}
    )


@emissions_bp.route('/template/excel', methods=['GET'])
def get_excel_template():
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Color
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.comments import Comment
    from openpyxl.utils import get_column_letter
    import openpyxl.utils

    wb = openpyxl.Workbook()

    # ─── Colour palette (Modern Green Environmental Theme) ───
    GREEN_DARK  = "1B5E20"   # dark forest green – headers
    GREEN_MID   = "2E7D32"   # medium green – sub-headers / Tier-3 sheet headers
    GREEN_LIGHT = "C8E6C9"   # pale green – alternating data rows
    WHITE       = "FFFFFF"
    GREY_LIGHT  = "F5F5F5"
    YELLOW_HINT = "FFFDE7"   # required-field highlight
    BLUE_HINT   = "E3F2FD"   # info / reference cells
    ORANGE_WARN = "FF6F00"   # warning accent

    def hdr_style(cell, bg=GREEN_DARK, fg=WHITE, sz=11, bold=True, wrap=True):
        cell.font = Font(bold=bold, color=fg, size=sz, name="Calibri")
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=wrap)

    def sub_hdr(cell, bg=GREEN_MID):
        hdr_style(cell, bg=bg, fg=WHITE, sz=10, bold=True)

    def info_cell(cell, bg=BLUE_HINT, fg="1A237E"):
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.font = Font(color=fg, size=10, name="Calibri")
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    def req_cell(cell, bg=YELLOW_HINT):
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.font = Font(color="B71C1C", size=10, bold=True, name="Calibri")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin = Side(style="thin", color="BDBDBD")
    thick = Side(style="medium", color=GREEN_DARK)
    std_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    thick_border = Border(left=thick, right=thick, top=thick, bottom=thick)

    def add_comment(cell, text, author="GHG Platform"):
        c = Comment(text, author)
        c.width = 300; c.height = 120
        cell.comment = c

    # ═══════════════════════════════════════════════════════════
    # SHEET 1: INSTRUCTIONS
    # ═══════════════════════════════════════════════════════════
    ws_inst = wb.active
    ws_inst.title = "📋 Instructions"
    ws_inst.sheet_view.showGridLines = False

    # Title banner
    ws_inst.merge_cells("A1:H1")
    t = ws_inst["A1"]
    t.value = "GHG Emissions Data Entry Template – User Guide"
    t.font = Font(bold=True, size=16, color=WHITE, name="Calibri")
    t.fill = PatternFill(start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws_inst.row_dimensions[1].height = 40

    ws_inst.merge_cells("A2:H2")
    sub = ws_inst["A2"]
    sub.value = "API Compendium 2021 – Scope 1 Direct Emissions – Monthly Reporting Template"
    sub.font = Font(bold=False, size=11, color=WHITE, name="Calibri", italic=True)
    sub.fill = PatternFill(start_color=GREEN_MID, end_color=GREEN_MID, fill_type="solid")
    sub.alignment = Alignment(horizontal="center", vertical="center")
    ws_inst.row_dimensions[2].height = 22

    # Section: Quick Start
    ws_inst.merge_cells("A4:H4")
    sec = ws_inst["A4"]
    sec.value = "🚀  QUICK START"
    hdr_style(sec, bg=GREEN_MID, sz=12)
    ws_inst.row_dimensions[4].height = 28

    steps = [
        ("Step 1", "Fill in the '🏢 Facilities' sheet with your facility and equipment names. These will drive the dropdowns in the data sheet."),
        ("Step 2", "Go to the '📊 Data Entry' sheet. Each row = one piece of equipment for one calendar month."),
        ("Step 3", "Use the dropdowns in columns C (Process Type), D (Factor Type), and M (Unit) to select valid values."),
        ("Step 4", "For Tier 3 (Engineering) calculations, fill in the matching process tab (e.g. '⚙ Combustion', '⚙ Flaring')."),
        ("Step 5", "Save the file and upload it using the 'Upload' button in the GHG Platform application."),
    ]
    for r, (s, d) in enumerate(steps, 5):
        ws_inst[f"A{r}"].value = s
        ws_inst[f"A{r}"].font = Font(bold=True, color=GREEN_DARK, name="Calibri", size=10)
        ws_inst[f"A{r}"].alignment = Alignment(vertical="top")
        ws_inst.merge_cells(f"B{r}:H{r}")
        ws_inst[f"B{r}"].value = d
        ws_inst[f"B{r}"].font = Font(name="Calibri", size=10)
        ws_inst[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws_inst.row_dimensions[r].height = 28

    # Section: Column Reference
    ws_inst.merge_cells(f"A{len(steps)+6}:H{len(steps)+6}")
    sec2 = ws_inst[f"A{len(steps)+6}"]
    sec2.value = "📑  DATA ENTRY COLUMN REFERENCE"
    hdr_style(sec2, bg=GREEN_MID, sz=12)
    ws_inst.row_dimensions[len(steps)+6].height = 28

    col_ref = [
        ("A", "Date (YYYY-MM)",             "Required", "Year and month: e.g. 2024-01 for January 2024. Must be in YYYY-MM format."),
        ("B", "Activity",                    "Required", "Business activity/segment: e.g. 'Exploration & Production', 'Midstream', 'Downstream'."),
        ("C", "Division",                    "Required", "Organizational unit/division: e.g. 'Production', 'Association'."),
        ("D", "Field",                       "Optional", "Field or project name: e.g. 'Hassi Messaoud', 'South Field'."),
        ("E", "Region / Facility",           "Required", "Name of the facility as registered in the GHG Platform. Must match exactly."),
        ("F", "Emission Source (Group)",     "Optional", "Functional grouping for the emission source (e.g. 'Compressor Station A')."),
        ("G", "Equipment Name",              "Required", "Descriptive name of the equipment (e.g. 'Caterpillar G3516 Engine #3')."),
        ("H", "Equipment ID",                "Optional", "Asset tag or unique ID (e.g. 'EQ-0042'). Used for deduplication checks."),
        ("I", "Process Type",                "Required", "Select from dropdown. Options: Combustion, Flaring, Venting, Pneumatic Devices, etc."),
        ("J", "Activity / Fuel",             "Required", "Fuel or gas type consumed/emitted. Must match supported factors (e.g. 'Natural Gas', 'Diesel')."),
        ("K", "Factor Type",                 "Required", "Select 'default' (API Compendium factor) or 'custom' (user-defined factor saved in platform)."),
        ("L", "Quantity",                    "Required", "Numeric value of the activity data for the month (volume, mass, or count)."),
        ("M", "Unit",                        "Required", "Unit of the quantity. Must match the selected fuel factor unit (e.g. scf for gas, gal for liquid)."),
    ]
    r_start = len(steps) + 7
    # Header row
    for c, (col, name, req, desc) in enumerate(col_ref, 0):
        ws_inst[f"A{r_start+c}"].value = col
        ws_inst[f"A{r_start+c}"].font = Font(bold=True, color=WHITE, name="Calibri", size=10)
        ws_inst[f"A{r_start+c}"].fill = PatternFill(start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid")
        ws_inst[f"A{r_start+c}"].alignment = Alignment(horizontal="center", vertical="center")
        ws_inst[f"B{r_start+c}"].value = name
        ws_inst[f"B{r_start+c}"].font = Font(bold=True, name="Calibri", size=10)
        req_color = "B71C1C" if req == "Required" else "37474F"
        ws_inst[f"C{r_start+c}"].value = req
        ws_inst[f"C{r_start+c}"].font = Font(color=req_color, bold=True, name="Calibri", size=10)
        ws_inst[f"C{r_start+c}"].alignment = Alignment(horizontal="center")
        ws_inst.merge_cells(f"D{r_start+c}:H{r_start+c}")
        ws_inst[f"D{r_start+c}"].value = desc
        ws_inst[f"D{r_start+c}"].font = Font(name="Calibri", size=10)
        ws_inst[f"D{r_start+c}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws_inst.row_dimensions[r_start+c].height = 30

    ws_inst.column_dimensions["A"].width = 8
    ws_inst.column_dimensions["B"].width = 30
    ws_inst.column_dimensions["C"].width = 12
    for c in "DEFGH":
        ws_inst.column_dimensions[c].width = 22

    # ═══════════════════════════════════════════════════════════
    # SHEET 2: FACILITIES REFERENCE
    # ═══════════════════════════════════════════════════════════
    ws_fac = wb.create_sheet("🏢 Facilities")
    ws_fac.sheet_view.showGridLines = False

    ws_fac.merge_cells("A1:E1")
    fac_title = ws_fac["A1"]
    fac_title.value = "Facility & Equipment Reference  ← Fill this sheet first"
    fac_title.font = Font(bold=True, size=13, color=WHITE, name="Calibri")
    fac_title.fill = PatternFill(start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid")
    fac_title.alignment = Alignment(horizontal="center", vertical="center")
    ws_fac.row_dimensions[1].height = 35

    fac_cols = ["Facility Name", "Activity / Segment", "Division", "Field", "Notes"]
    for i, h in enumerate(fac_cols, 1):
        c = ws_fac.cell(row=2, column=i, value=h)
        hdr_style(c, bg=GREEN_MID)
        ws_fac.column_dimensions[get_column_letter(i)].width = 30

    sample_facs = [
        ("Field Alpha Processing Plant", "Exploration & Production", "Production", "Hassi Messaoud", "Main separation facility"),
        ("Hassi R'mel Gas Hub",           "Exploration & Production", "Production", "Hassi R'mel",    "Gas injection + compression"),
        ("South Field Compressor Stn",    "Exploration & Production", "Production", "South Field",    "4x Cat G3516 engines"),
    ]
    for r, row in enumerate(sample_facs, 3):
        for c, val in enumerate(row, 1):
            cell = ws_fac.cell(row=r, column=c, value=val)
            cell.font = Font(name="Calibri", size=10, italic=True, color="546E7A")
            cell.fill = PatternFill(start_color=GREY_LIGHT, end_color=GREY_LIGHT, fill_type="solid")
            cell.border = std_border
        ws_fac.row_dimensions[r].height = 20

    # Leave 97 blank editable rows
    for r in range(6, 103):
        for c in range(1, 6):
            cell = ws_fac.cell(row=r, column=c)
            cell.border = std_border
            cell.fill = PatternFill(start_color=WHITE, end_color=WHITE, fill_type="solid")
        ws_fac.row_dimensions[r].height = 18

    ws_fac.freeze_panes = "A3"

    # Named range for facility names (col A rows 3–102) → used for dropdown in Data sheet
    # (openpyxl doesn't support dynamic named ranges well; we define a fixed range)
    wb.create_named_range("FacilityList", ws_fac, "$A$3:$A$102")

    # ═══════════════════════════════════════════════════════════
    # SHEET 3: MAIN DATA ENTRY
    # ═══════════════════════════════════════════════════════════
    ws_data = wb.create_sheet("📊 Data Entry")
    ws_data.sheet_view.showGridLines = False

    DATA_COLS = [
        # (header, width, required)
        ("Date\n(YYYY-MM)",           14, True),
        ("Activity",                   22, True),
        ("Division",                   20, True),
        ("Field",                      20, False),
        ("Region / Facility",          28, True),
        ("Emission Source\n(Group)",   24, False),
        ("Equipment Name",             28, True),
        ("Equipment ID",               18, False),
        ("Process Type",               24, True),
        ("Activity / Fuel",            24, True),
        ("Factor Type",                16, True),
        ("Quantity",                   14, True),
        ("Unit",                       14, True),
        ("Notes / Comments",           30, False),
    ]

    # Freeze pane A2
    ws_data.freeze_panes = "A2"

    # Row 1 – Title banner
    ws_data.merge_cells(f"A1:{get_column_letter(len(DATA_COLS))}1")
    banner = ws_data["A1"]
    banner.value = "📊  GHG Emissions – Monthly Data Entry   |   One row = One equipment × One month   |   Columns in RED are required"
    banner.font = Font(bold=True, size=11, color=WHITE, name="Calibri")
    banner.fill = PatternFill(start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid")
    banner.alignment = Alignment(horizontal="center", vertical="center")
    ws_data.row_dimensions[1].height = 30

    # Row 2 – Column headers
    for i, (col_name, col_w, req) in enumerate(DATA_COLS, 1):
        cell = ws_data.cell(row=2, column=i, value=col_name)
        bg = GREEN_MID if not req else "1B5E20"
        hdr_style(cell, bg=bg, sz=10)
        ws_data.column_dimensions[get_column_letter(i)].width = col_w
        ws_data.row_dimensions[2].height = 36

        # Header comments
        hints = {
            1: "Format: YYYY-MM e.g. 2024-01",
            5: "Must exactly match a name from the 🏢 Facilities sheet",
            9: "Select from list: Combustion, Flaring, Venting, etc.",
            10: "Gas/fuel type e.g. Natural Gas, Diesel, Associated Gas",
            11: "default = API Compendium standard factor | custom = your saved factor",
            12: "Numeric quantity for the month (e.g. 50000)",
            13: "e.g. scf, m3, gal, bbl, kg, tonne",
        }
        if i in hints:
            add_comment(cell, hints[i])

    # Data Validations

    dv_process = DataValidation(
        type="list",
        formula1='"Combustion,Flaring,Fugitive Emissions,Venting,Well Completions & Workovers,Liquids Unloading,Dehydrator,Pneumatic Device,Storage Tank - Flashing,Storage Tank - Working Losses,Storage Tank - Breathing,Drilling Operations,Acid Gas Removal (AGR),Mobile Combustion,Loading Losses,Wastewater / Separation"',
        allow_blank=True,
        showInputMessage=True, promptTitle="Process Type", prompt="Select the emission process type.",
        showErrorMessage=True, errorTitle="Invalid Value", error="Please select a value from the dropdown list."
    )
    ws_data.add_data_validation(dv_process)
    dv_process.sqref = "I3:I1048576"

    dv_factor = DataValidation(
        type="list", formula1='"default,custom"', allow_blank=True,
        showInputMessage=True, promptTitle="Factor Type",
        prompt="'default' = API Compendium 2021 standard factor.\n'custom' = factor saved in your GHG Platform account.",
        showErrorMessage=True, errorTitle="Invalid Value", error="Please select 'default' or 'custom'."
    )
    ws_data.add_data_validation(dv_factor)
    dv_factor.sqref = "K3:K1048576"

    dv_unit = DataValidation(
        type="list",
        formula1='"scf,Mscf,MMscf,m3,gal,bbl,kg,tonne,tonnes/yr,kWh,MWh,km,miles,hours"',
        allow_blank=True,
        showInputMessage=True, promptTitle="Unit",
        prompt="Select the unit that matches your quantity and fuel type.",
        showErrorMessage=False  # allow custom units too
    )
    ws_data.add_data_validation(dv_unit)
    dv_unit.sqref = "M3:M1048576"

    dv_date = DataValidation(
        type="textLength", operator="greaterThanOrEqual", formula1="7",
        allow_blank=True,
        showErrorMessage=True, errorTitle="Date Format", error="Please enter a date in YYYY-MM format (e.g. 2024-01)."
    )
    ws_data.add_data_validation(dv_date)
    dv_date.sqref = "A3:A1048576"

    dv_qty = DataValidation(
        type="decimal", operator="greaterThanOrEqual", formula1="0",
        allow_blank=True,
        showErrorMessage=True, errorTitle="Invalid Quantity", error="Quantity must be a non-negative number."
    )
    ws_data.add_data_validation(dv_qty)
    dv_qty.sqref = "L3:L1048576"

    # ── Sample data rows ──
    samples = [
        ["2024-01","Exploration & Production","Production","Hassi Messaoud","Field Alpha Processing Plant","Compressor Station A","Caterpillar G3516 #1","EQ-001","Combustion","Natural Gas","default",50000,"scf","Tier 1 – standard factor"],
        ["2024-01","Exploration & Production","Production","Hassi Messaoud","Field Alpha Processing Plant","Flare Stack","HP Flare Stack - West","EQ-002","Flaring","Associated Gas","default",120000,"scf","Tier 3 – see Flaring sheet"],
        ["2024-01","Exploration & Production","Production","Hassi Messaoud","Field Alpha Processing Plant","Production Separator","3-Phase Separator #2","EQ-003","Venting","Natural Gas (Venting/Blowdown)","default",8000,"m3","Venting from separator depressuring"],
        ["2024-01","Exploration & Production","Production","Hassi Messaoud","Field Alpha Processing Plant","Storage","Crude Oil Storage Tank #5","EQ-004","Storage Tank - Flashing","Tank - Flash Emissions (Gas Well)","default",9500,"bbl","Monthly oil throughput"],
        ["2024-01","Exploration & Production","Production","South Field","South Field Compressor Stn","Pneumatics","Control Valve Bank A","EQ-005","Pneumatic Device","Pneumatic High-Bleed Device","default",12,"units","Count of high-bleed controllers"],
    ]
    for r, row in enumerate(samples, 3):
        for c, val in enumerate(row, 1):
            cell = ws_data.cell(row=r, column=c, value=val)
            cell.border = std_border
            cell.font = Font(name="Calibri", size=10, italic=True, color="37474F")
            bg = GREEN_LIGHT if r % 2 == 1 else WHITE
            cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
            cell.alignment = Alignment(vertical="center", wrap_text=False)
        ws_data.row_dimensions[r].height = 18

    # Empty rows with alternating shading and borders
    for r in range(8, 2003):
        for c in range(1, len(DATA_COLS) + 1):
            cell = ws_data.cell(row=r, column=c)
            cell.border = std_border
            bg = GREEN_LIGHT if r % 2 == 0 else WHITE
            cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        ws_data.row_dimensions[r].height = 18

    # ═══════════════════════════════════════════════════════════
    # SHEET 4+: TIER 3 ENGINEERING SHEETS (one per process)
    # ═══════════════════════════════════════════════════════════
    TIER3_SHEETS = {
        "⚙ Tier 3 Calculations": {
            "desc": "Engineering parameters for Tier 3 calculations and Gas Composition data.",
            "cols": [
                ("Equipment ID", 18, "Link to Equipment ID in Data Entry sheet"),
                ("Date (YYYY-MM)", 14, "Must match the date in Data Entry sheet"),
                ("Process Type", 18, "Optional Reference"),
                # Gas Composition
                ("C1 (mol %)", 14, "Methane (CH4) fraction"),
                ("C2 (mol %)", 14, "Ethane fraction"),
                ("C3 (mol %)", 14, "Propane fraction"),
                ("C4 (mol %)", 14, "Butane fraction"),
                ("C5 (mol %)", 14, "Pentane fraction"),
                ("C6 (mol %)", 14, "Hexane fraction"),
                ("C7 (mol %)", 14, "Heptane fraction"),
                ("C8 (mol %)", 14, "Octane fraction"),
                ("C9 (mol %)", 14, "Nonane fraction"),
                ("C10 (mol %)", 14, "Decane+ fraction"),
                ("N2 (mol %)", 14, "Nitrogen fraction"),
                ("Flare Type", 18, "e.g., elevated, enclosed_ground"),
                ("Flare Control Efficiency (%)", 22, "Combustion efficiency (%)"),
                # User Uncertainty Overrides
                ("User Uncertainty CO2 (%)", 22, "Optional: Override CO2 Uncertainty"),
                ("User Uncertainty CH4 (%)", 22, "Optional: Override CH4 Uncertainty"),
                ("User Uncertainty N2O (%)", 22, "Optional: Override N2O Uncertainty"),
                # Storage Tanks
                ("Tank GOR", 14, "Gas-to-Oil Ratio (scf/bbl)"),
                # Pneumatics
                ("Pneumatic Count", 16, "Number of identical devices"),
                ("Bleed Rate (scf/hr)", 20, "Bleed rate per device"),
                ("Hours", 10, "Hours of operation in month"),
                # Well Completions / Workovers
                ("Well Depth (ft)", 16, "Depth of the well"),
                ("Diameter (in)", 14, "Casing or tubing diameter"),
                ("Pressure (psi)", 16, "Surface or bottom-hole pressure"),
                ("Events", 10, "Number of unloading/completion events"),
                # Venting / Blowdowns
                ("Blowdown Volume (Mscf)", 22, "Total volume of gas blown down"),
                # Fugitive Emissions
                ("Fugitive Method", 18, "Component count or leak survey method"),
                ("PPM", 10, "Leak concentration in PPM"),
                # Dehydrators / AGR
                ("Dehydrator Throughput (Mscf/day)", 28, "Monthly gas throughput"),
                ("Dehy CH4 (%)", 16, "Methane slip from Dehy"),
                ("AGR Throughput (Mscf/day)", 24, "Monthly gas feed rate to AGR"),
                ("CO2 In (%)", 14, "CO2 in feed"),
                ("CO2 Out (%)", 14, "CO2 in sweet gas")
            ]
        }
    }

    for sheet_name, cfg in TIER3_SHEETS.items():
        ws_t3 = wb.create_sheet(sheet_name)
        ws_t3.sheet_view.showGridLines = False
        ws_t3.freeze_panes = "A3"

        # Title
        col_count = len(cfg["cols"])
        ws_t3.merge_cells(f"A1:{get_column_letter(col_count)}1")
        t3_title = ws_t3["A1"]
        t3_title.value = f"{sheet_name.replace('⚙ ', '')} – Tier 3 Engineering Parameters"
        t3_title.font = Font(bold=True, size=13, color=WHITE, name="Calibri")
        t3_title.fill = PatternFill(start_color=GREEN_MID, end_color=GREEN_MID, fill_type="solid")
        t3_title.alignment = Alignment(horizontal="center", vertical="center")
        ws_t3.row_dimensions[1].height = 35

        # Description
        ws_t3.merge_cells(f"A2:{get_column_letter(col_count)}2")
        desc_c = ws_t3["A2"]
        desc_c.value = cfg["desc"]
        desc_c.font = Font(italic=True, size=10, color="37474F", name="Calibri")
        desc_c.fill = PatternFill(start_color=GREEN_LIGHT, end_color=GREEN_LIGHT, fill_type="solid")
        desc_c.alignment = Alignment(horizontal="center", vertical="center")
        ws_t3.row_dimensions[2].height = 22

        # Column headers
        for i, (col_name, col_w, col_hint) in enumerate(cfg["cols"], 1):
            cell = ws_t3.cell(row=3, column=i, value=col_name)
            hdr_style(cell, bg=GREEN_DARK, sz=10)
            ws_t3.column_dimensions[get_column_letter(i)].width = col_w
            ws_t3.row_dimensions[3].height = 32
            add_comment(cell, col_hint)

        # Empty data rows
        for r in range(4, 1004):
            for c in range(1, col_count + 1):
                cell = ws_t3.cell(row=r, column=c)
                cell.border = std_border
                bg = GREEN_LIGHT if r % 2 == 0 else WHITE
                cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
            ws_t3.row_dimensions[r].height = 18

    # ─── Save ──────────────────────────────────────────────────
    # Ensure exactly 3 sheets as requested (remove instructions)
    if "📋 Instructions" in wb.sheetnames:
        del wb["📋 Instructions"]
        
    fd, path = tempfile.mkstemp(suffix='.xlsx')
    with os.fdopen(fd, 'w'):
        pass
    wb.save(path)
    return send_file(
        path, as_attachment=True,
        download_name="GHG_Emissions_Template_v2.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )



@emissions_bp.route('/upload/start', methods=['POST'])
@login_required
def upload_start():
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    global_factor_type = request.form.get('global_factor_type', 'auto')
    
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
    file.save(path)
    
    from flask import current_app
    job_id = start_background_upload(
        current_app._get_current_object(),
        path, 
        file.filename, 
        user.id, 
        global_factor_type
    )
    
    return jsonify({'job_id': job_id})

@emissions_bp.route('/upload/status/<job_id>', methods=['GET'])
@login_required
def upload_status(job_id):
    status = get_job_status(job_id)
    if not status:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(status)
    
@emissions_bp.route('/upload/errors/<job_id>', methods=['GET'])
@login_required
def upload_errors(job_id):
    status = get_job_status(job_id)
    if not status or not status.get('error_csv_path'):
        return jsonify({'error': 'No errors file found'}), 404
    path = status['error_csv_path']
    return send_file(path, as_attachment=True, download_name=f"errors_{job_id}.csv", mimetype="text/csv")


@emissions_bp.route('/', methods=['POST'])
@login_required
def add_emission():
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    # Validation
    required = ['year', 'month', 'facility_id', 'process_type']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 422
            
    # Calculate Emissions
    # We need to fetch factor data if not specific
    # For now, using a simplified factor data placeholder or letting calculate handle it
    # In a real scenario, we'd query the factor database here.
    # Passing empty factor_data relies on hardcoded defaults in calculations.py if any
    
    # Fetch real factor data from Constants based on fuel_type
    factor_data = API_FACTORS.get(data.get('fuel'), {}) 
    
    # Custom Factor Override
    custom_factor_id = data.get('custom_factor_id')
    if custom_factor_id:
        cf = CustomFactor.query.get(custom_factor_id)
        if cf:
            # Map CustomFactor to factor_data structure
            # API_FACTORS usually has: { 'co2': val, 'ch4': val, 'n2o': val, 'unit': '...', 'hhv': ... }
            factor_data = {
                'co2': cf.co2_factor,
                'ch4': cf.ch4_factor,
                'n2o': cf.n2o_factor,
                'co': cf.co_factor,
                'unit': cf.unit,
                'hhv': cf.hhv_factor,
                'type': 'custom', # Helper to know source
                'name': cf.name
            }
            
            # Uncertainty Handling
            if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                factor_data['uncertainty'] = {
                    'co2': float(getattr(cf, 'co2_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,
                    'ch4': float(getattr(cf, 'ch4_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,
                    'n2o': float(getattr(cf, 'n2o_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0
                }
            elif cf.uncertainty and cf.uncertainty > 0:
                # Use saved custom uncertainty
                factor_data['uncertainty'] = {
                    'co2': cf.uncertainty,
                    'ch4': cf.uncertainty,
                    'n2o': cf.uncertainty
                }
            elif cf.parent_fuel:
                # Fallback to parent fuel uncertainty
                parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                if 'uncertainty' in parent_factor:
                    factor_data['uncertainty'] = parent_factor['uncertainty']
    
    # Call compute_emissions to calculate the actual emissions
    gwp_dict = resolve_gwp_dict(user)
    gwp_std = resolve_gwp_standard(user)
    try:
        em_result, method = compute_emissions(data, factor_data, gwp_dict=gwp_dict)
    except ValueError as e:
        # Extract missing field name from error message
        import re
        match = re.search(r"Missing required field: (\w+)", str(e))
        field = match.group(1) if match else "unknown"
        return jsonify({'error': 'Missing required field', 'field': field}), 422

    # Fallback: Calculate totalCo2e if it's missing or zero
    if not em_result.get('totalCo2e') or em_result.get('totalCo2e') == 0:
        co2_val = em_result.get('co2', 0)
        ch4_val = em_result.get('ch4', 0)
        n2o_val = em_result.get('n2o', 0)
        em_result['totalCo2e'] = calculate_co2e(co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict)

    # Extract uncertainty from rich API result if available, otherwise fallback to factor data
    api_res = em_result.get('_full_api_res')
    if api_res:
        # Use uncertainties calculated by the new engine, or None if not provided
        uncertainty = {
            'co2': api_res['results']['co2'].get('uncertainty', None) if isinstance(api_res['results']['co2'], dict) else None,
            'ch4': api_res['results']['ch4'].get('uncertainty', None) if isinstance(api_res['results']['ch4'], dict) else None,
            'n2o': api_res['results']['n2o'].get('uncertainty', None) if isinstance(api_res['results']['n2o'], dict) else None
        }
    else:
        uncertainty = factor_data.get('uncertainty', {})

    # NOTE: user_uncertainty is now handled inside dispatcher.py and propagated via SRSS
    
    record = Emission(
        record_id=str(uuid.uuid4()),
        year=data['year'],
        month=data['month'],
        facility_id=data['facility_id'],
        group_name=data.get('group_name'),
        activity=data.get('activity'),
        division=data.get('division'),
        field=data.get('field'),
        process_type=data['process_type'],
        fuel_type=data.get('fuel'),
        quantity=data.get('amount'),
        unit=data.get('unit'),
        equipment_id=data.get('equipment_id'),
        
        co2_emissions=em_result['co2'],
        ch4_emissions=em_result['ch4'],
        n2o_emissions=em_result['n2o'],
        co_emissions=em_result.get('co', 0),
        co2e_total=em_result['totalCo2e'],
        
        calc_method=method,
        gwp_version=gwp_std,
        source_payload=json.dumps(data),
        created_by=user.id,
        uncertainty=uncertainty.get('co2', None) if isinstance(uncertainty, dict) else (uncertainty or None),
        uncertainty_ch4=uncertainty.get('ch4', None) if isinstance(uncertainty, dict) else (uncertainty or None),
        uncertainty_n2o=uncertainty.get('n2o', None) if isinstance(uncertainty, dict) else (uncertainty or None),
        status=data.get('status', 'Verified')
    )
    
    db.session.add(record)
    db.session.flush()

    # --- Audit Log ---
    try:
        # Fetch facility name for better description
        facility = Facility.query.get(data['facility_id'])
        facility_name = facility.name if facility else 'Unknown'
        
        log_details = f"Added {record.process_type} emission: {record.quantity} {record.unit} of {record.fuel_type} for {facility_name} ({record.month}/{record.year})"
        log_activity_and_notify(
            action='CREATE',
            record_id=str(record.id),
            user=user,
            request=request,
            entity='Emission',
            details=log_details
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Audit Log Error: {e}")
        # Not raising here to not block notifications, but we committed atomically if no error
    
    # --- Notification Logic: Check Goal ---
    try:
        # Check user preference first
        prefs = json.loads(user.preferences or '{}')
        if prefs.get('notifTargets', True): # Default to True
            current_year = data.get('year')
            if current_year:
                # Get Total Emissions for Year
                total_emissions = db.session.query(func.sum(Emission.co2e_total)).filter(Emission.year == current_year).scalar() or 0
                
                # Get Goal
                goal = Goal.query.get(current_year)
                
                if goal and goal.target_amount > 0:
                    percent = total_emissions / goal.target_amount
                    
                    title = None
                    msg = None
                    n_type = None
                    
                    if percent >= 1.0:
                        title = f"Goal Exceeded for {current_year}"
                        msg = f"Emissions ({total_emissions:.1f}t) have exceeded the goal of {goal.target_amount}t."
                        n_type = 'critical'
                    elif percent >= 0.8:
                        title = f"Goal Warning for {current_year}"
                        msg = f"You have reached {percent*100:.0f}% of your emission goal ({total_emissions:.1f} / {goal.target_amount}t)."
                        n_type = 'warning'
                    
                    if title:
                        # EXTRA-08 FIX: Deduplicate — only create a new notification if
                        # an unread notification of the same type and year doesn't exist.
                        from datetime import timedelta
                        cutoff = datetime.datetime.utcnow() - timedelta(hours=24)
                        existing = Notification.query.filter(
                            Notification.user_id == user.id,
                            Notification.type == n_type,
                            Notification.title == title,
                            Notification.is_read == False,
                            Notification.created_at >= cutoff
                        ).first()
                        if not existing:
                            Notification.create(
                                title=title,
                                message=msg,
                                type=n_type,
                                user_id=user.id
                            )
    except Exception as e:
        from flask import current_app
        current_app.logger.warning(f"Notification check error: {e}")

    
    # Return emission result with uncertainty
    return jsonify({
        'message': 'Record added',
        'id': record.id,
        'emissions': {
            'co2': em_result['co2'],
            'ch4': em_result['ch4'],
            'n2o': em_result['n2o'],
            'totalCo2e': em_result['totalCo2e'],
            'uncertainty': uncertainty
        },
        'record': {
            'process_type': data['process_type'],
            # BUG-04 FIX: safe facility name lookup
            'facility_name': (Facility.query.get(data['facility_id']).name
                              if data.get('facility_id') and Facility.query.get(data['facility_id'])
                              else 'Unknown'),
            'month': data['month'],
            'year': data['year'],
            'fuel': data.get('fuel'),
            'amount': data.get('amount'),
            'unit': data.get('unit')
        },
        'calculation_method': method
    }), 201

@emissions_bp.route('/<id>', methods=['DELETE'])
@login_required  # SEC-01 FIX: was missing
def delete_emission(id):
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    record = Emission.query.filter_by(record_id=id).first() or db.session.get(Emission, int(id) if str(id).isdigit() else -1)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    # SEC-03 FIX: IDOR — enforce ownership; admins may delete any record, users can delete own records
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and record.facility_id not in allowed_fids:
        if record.created_by != user.id:
            return jsonify({'error': 'Forbidden: Outside your region'}), 403

    # BUG-05 FIX: capture audit data before deletion, then commit everything atomically
    log_details = f"Deleted {record.process_type} record: {record.quantity} {record.unit} of {record.fuel_type} ({record.month}/{record.year})"

    db.session.delete(record)

    try:
        log_activity_and_notify(
            action='DELETE',
            record_id=str(id),
            user=user,
            request=request,
            entity='Emission',
            details=log_details
        )
        db.session.commit()  # single atomic commit for delete + audit
    except Exception as e:
        db.session.rollback()
        raise e
    
    return jsonify({'message': 'Record deleted'})

@emissions_bp.route('/<id>', methods=['PUT'])
@login_required  # EXTRA-06 FIX: decorator was present but get_current_user() could return None causing 500
def update_emission(id):
    user = get_current_user()
    data = request.get_json()  # EXTRA-03 FIX: removed duplicate call below
    record = Emission.query.filter_by(record_id=id).first() or db.session.get(Emission, int(id) if str(id).isdigit() else -1)  # EXTRA-02 FIX
    
    if not record: return jsonify({'error': 'Not found'}), 404
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and record.facility_id not in allowed_fids:
        return jsonify({'error': 'Unauthorized: Outside your region'}), 403
        # EXTRA-03 FIX: removed second data = request.get_json() (double-read, second returns None)
    
    # Update fields
    if 'year' in data:
        record.year = data['year']
    if 'month' in data:
        record.month = data['month']
    if 'facility_id' in data:
        record.facility_id = data['facility_id']
    if 'process_type' in data:
        record.process_type = data['process_type']
    if 'fuel_type' in data:
        record.fuel_type = data['fuel_type']
    if 'quantity' in data:
        record.quantity = data['quantity']
    if 'unit' in data:
        record.unit = data['unit']
    if 'status' in data:
        record.status = data['status']
    
    # Only recalculate emissions if explicitly requested
    if data.get('recalculate'):
        # BUG-18 FIX: initialize factor_data before the custom factor block
        factor_data = API_FACTORS.get(data.get('fuel') or data.get('fuel_type'), {})
        # Handle Custom Factor in update
        cf_id = data.get('custom_factor_id')
        if cf_id:
            cf = CustomFactor.query.get(cf_id)
            if cf:
                factor_data = {
                    'co2': cf.co2_factor,
                    'ch4': cf.ch4_factor,
                    'n2o': cf.n2o_factor,
                    'co': cf.co_factor,
                    'unit': cf.unit,
                    'hhv': cf.hhv_factor,
                    'type': 'custom',
                    'name': cf.name
                }
                # Uncertainty Handle (Update)
                if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                    factor_data['uncertainty'] = {
                        'co2': float(getattr(cf, 'co2_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,
                        'ch4': float(getattr(cf, 'ch4_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,
                        'n2o': float(getattr(cf, 'n2o_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0
                    }
                elif cf.uncertainty and cf.uncertainty > 0:
                    factor_data['uncertainty'] = {'co2': float(cf.uncertainty or 0)/100.0, 'ch4': float(cf.uncertainty or 0)/100.0, 'n2o': float(cf.uncertainty or 0)/100.0}
                elif cf.parent_fuel:
                    parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                    if 'uncertainty' in parent_factor:
                        factor_data['uncertainty'] = parent_factor['uncertainty']

        gwp_dict = resolve_gwp_dict(user)
        gwp_std = resolve_gwp_standard(user)
        try:
            calculated_em, method = compute_emissions(data, factor_data, gwp_dict=gwp_dict)
            record.co2_emissions = calculated_em['co2']
            record.ch4_emissions = calculated_em['ch4']
            record.n2o_emissions = calculated_em['n2o']
            record.co_emissions = calculated_em.get('co', 0)
            record.co2e_total = calculated_em['totalCo2e']
            record.calc_method = method
            record.gwp_version = gwp_std
            
            # Update record uncertainty
            u_dict = factor_data.get('uncertainty', {})
            record.uncertainty = u_dict.get('co2', None) if isinstance(u_dict, dict) else (u_dict or None)
            record.uncertainty_ch4 = u_dict.get('ch4', None) if isinstance(u_dict, dict) else (u_dict or None)
            record.uncertainty_n2o = u_dict.get('n2o', None) if isinstance(u_dict, dict) else (u_dict or None)
            
            # Override with user-provided uncertainties if they exist
            user_unc = data.get('user_uncertainty')
            if user_unc and isinstance(user_unc, dict):
                if 'co2' in user_unc and user_unc['co2'] not in [None, '']:
                    record.uncertainty = float(user_unc['co2']) / 100.0
                if 'ch4' in user_unc and user_unc['ch4'] not in [None, '']:
                    record.uncertainty_ch4 = float(user_unc['ch4']) / 100.0
                if 'n2o' in user_unc and user_unc['n2o'] not in [None, '']:
                    record.uncertainty_n2o = float(user_unc['n2o']) / 100.0
            
            
        except Exception as e:
            print(f"Error during emission recalculation: {e}")
    
    record.updated_by = user.id
    record.updated_at = datetime.datetime.utcnow()
    
    db.session.flush()

    # --- Audit Log ---
    try:
        # For updates, we could track exactly what changed
        changes = []
        for key in data:
            if key in ['year', 'month', 'facility_id', 'process_type', 'fuel_type', 'quantity', 'unit']:
                changes.append(key)
        
        log_details = f"Updated emission record {id}. Changed fields: {', '.join(changes)}"
        
        log_activity_and_notify(
            action='UPDATE',
            record_id=str(id),
            user=user,
            request=request,
            entity='Emission',
            details=log_details
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
    return jsonify({'message': 'Record updated'})

@emissions_bp.route('/bulk-delete', methods=['POST'])
@login_required  # SEC-01 FIX: was missing
def bulk_delete_emissions():
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400
    
    # SEC-03 FIX: IDOR — non-admins can only bulk-delete their own records
    query = Emission.query.filter(Emission.id.in_(ids))
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(Emission.facility_id.in_(allowed_fids))
    deleted_count = query.delete(synchronize_session=False)
    db.session.flush()

    # --- Audit Log ---
    try:
        log_activity_and_notify(
            action='DELETE',
            record_id='BULK',
            user=user,
            request=request,
            entity='Emission',
            details=f"Bulk deleted {deleted_count} emission records"
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
    return jsonify({'message': f'{deleted_count} records deleted'})

@emissions_bp.route('/import', methods=['POST'])
@login_required  # SEC-01 FIX: was missing
def import_emissions():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    records_data = data.get('records', [])

    if not records_data:
        return jsonify({'error': 'No records provided'}), 400

    imported_count = 0
    errors = []
    
    # Cache for facility lookups to avoid redundant queries
    facility_cache = {}

    for i, rec_data in enumerate(records_data):
        try:
            # 1. Resolve facility_id (could be a name string from CSV)
            f_val = rec_data.get('facility_id')
            facility = None
            
            if isinstance(f_val, str) and not f_val.isdigit():
                # Provided value is a facility name - make it case insensitive and strip whitespace
                f_name_clean = f_val.strip()
                if f_name_clean.lower() in facility_cache:
                    facility = facility_cache[f_name_clean.lower()]
                else:
                    facility = Facility.query.filter(func.lower(Facility.name) == f_name_clean.lower()).first()
                    facility_cache[f_name_clean.lower()] = facility
            else:
                # Provided value is potentially an ID
                try:
                    fid = int(f_val) if f_val else None
                    if fid in facility_cache:
                        facility = facility_cache[fid]
                    else:
                        facility = Facility.query.get(fid)
                        facility_cache[fid] = facility
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility/Region '{f_val}' not found")
                continue

            # Update rec_data with resolved ID and ensure group_name is set for calculation context
            rec_data['facility_id'] = facility.id
            if not rec_data.get('group_name'):
                rec_data['group_name'] = facility.name
            
            # Fill in hierarchy if missing
            rec_data['activity'] = rec_data.get('activity') or facility.activity
            rec_data['division'] = rec_data.get('division') or facility.division
            rec_data['field'] = rec_data.get('field') or facility.field

            # CRITICAL: Sanitize CSV placeholders ('-') to prevent float conversion errors
            # CSV templates use '-' for empty optional fields
            for key in ['ch4_content', 'hhv', 'comp_flare_eff', 'tank_gor', 'tank_api_gravity', 
                        'flare_type', 'pneu_bleed_rate', 'pneu_hours', 'dehy_pump_rate', 
                        'unload_diam', 'unload_depth', 'unload_press', 'comp_duration', 'comp_rate', 'amount']:
                if rec_data.get(key) in ['-', '', None]:
                    rec_data[key] = None
                    
            # Safe float conversion for amount
            if rec_data.get('amount') is not None:
                try:
                    rec_data['amount'] = float(rec_data['amount'])
                except (ValueError, TypeError):
                    errors.append(f"Row {i}: Invalid numeric amount '{rec_data['amount']}'")
                    continue

            # 2. Fetch factor data
            fuel_key = rec_data.get('fuel') or rec_data.get('fuel_type')
            
            # CRITICAL: Fuel name aliasing - handle common variations
            FUEL_ALIASES = {
                'Diesel': 'Diesel (No. 2 Fuel Oil)',
                'No. 2 Diesel': 'Diesel (No. 2 Fuel Oil)',
                'Gasoline': 'Motor Gasoline',
                'Petrol': 'Motor Gasoline',
            }
            
            # Try alias first, then original
            canonical_fuel = FUEL_ALIASES.get(fuel_key, fuel_key)
            rec_data['fuel'] = canonical_fuel # Update to canonical name
            
            factor_data = API_FACTORS.get(canonical_fuel, {})
            if not factor_data and fuel_key != canonical_fuel:
                # Fallback to original if alias didn't work
                factor_data = API_FACTORS.get(fuel_key, {})
                rec_data['fuel'] = fuel_key
            
            # CRITICAL: If no HHV provided in CSV, use factor's HHV or standard defaults
            if not rec_data.get('hhv'):
                # Try to get HHV from the emission factor
                if factor_data.get('hhv'):
                    rec_data['hhv'] = factor_data.get('hhv')
                else:
                    # Hardcoded defaults for common fuels (BTU/unit)
                    FUEL_HHV_DEFAULTS = {
                        'Natural Gas': 1020,  # BTU/scf
                        'Diesel': 138700,  # BTU/gal
                        'Gasoline': 125000,  # BTU/gal
                        'Fuel Oil': 138000,  # BTU/gal
                        'Propane': 91500,  # BTU/gal
                        'Butane': 103000,  # BTU/gal
                    }
                    default_hhv = FUEL_HHV_DEFAULTS.get(fuel_key)
                    if default_hhv:
                        rec_data['hhv'] = default_hhv
            
            # Check for custom factor if provided
            cf_id = rec_data.get('custom_factor_id')
            if cf_id:
                cf = CustomFactor.query.get(cf_id)
                if cf:
                    factor_data = {
                        'co2': cf.co2_factor, 'ch4': cf.ch4_factor, 'n2o': cf.n2o_factor,
                        'co': cf.co_factor, 'unit': cf.unit, 'hhv': cf.hhv_factor,
                        'type': 'custom', 'name': cf.name
                    }
                    # Uncertainty Handling (Import)
                    if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                        factor_data['uncertainty'] = {

                            'co2': float(getattr(cf, 'co2_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,

                            'ch4': float(getattr(cf, 'ch4_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0,

                            'n2o': float(getattr(cf, 'n2o_uncertainty', None) or getattr(cf, 'uncertainty', 0) or 0) / 100.0

                        }
                    elif cf.uncertainty and cf.uncertainty > 0:
                        factor_data['uncertainty'] = {'co2': float(cf.uncertainty or 0)/100.0, 'ch4': float(cf.uncertainty or 0)/100.0, 'n2o': float(cf.uncertainty or 0)/100.0}
                    elif cf.parent_fuel:
                        parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                        if 'uncertainty' in parent_factor:
                            factor_data['uncertainty'] = parent_factor['uncertainty']

            # 3. Compute emissions
            gwp_dict = resolve_gwp_dict(user)
            gwp_std = resolve_gwp_standard(user)
            em_result, method = compute_emissions(rec_data, factor_data, gwp_dict=gwp_dict)
            
            # Fallback for totalCo2e
            if not em_result.get('totalCo2e') or em_result.get('totalCo2e') == 0:
                co2_val = em_result.get('co2', 0)
                ch4_val = em_result.get('ch4', 0)
                n2o_val = em_result.get('n2o', 0)
                em_result['totalCo2e'] = calculate_co2e(co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict)

            # 4. Create record
            record = Emission(
                record_id=f"IMP-{uuid.uuid4().hex[:8]}-{i}",
                year=rec_data.get('year'),
                month=rec_data.get('month'),
                facility_id=facility.id,
                group_name=rec_data['group_name'],
                activity=rec_data['activity'],
                division=rec_data['division'],
                field=rec_data['field'],
                process_type=rec_data.get('process_type') or rec_data.get('type'),
                fuel_type=fuel_key,
                quantity=rec_data.get('amount'),
                unit=rec_data.get('unit'),
                equipment_id=rec_data.get('equipment_id'),
                co2_emissions=em_result.get('co2') if em_result.get('co2') is not None else 0,
                ch4_emissions=em_result.get('ch4') if em_result.get('ch4') is not None else 0,
                n2o_emissions=em_result.get('n2o') if em_result.get('n2o') is not None else 0,
                co_emissions=em_result.get('co') if em_result.get('co') is not None else 0,
                co2e_total=em_result.get('totalCo2e') if em_result.get('totalCo2e') is not None else 0,
                calc_method=method,
                gwp_version=gwp_std,
                source_payload=json.dumps(rec_data),
                created_by=user.id,
                uncertainty=factor_data.get('uncertainty', {}).get('co2', 0) if isinstance(factor_data.get('uncertainty'), dict) else (factor_data.get('uncertainty') or 0),
                status=rec_data.get('status', 'Verified')
            )
            db.session.add(record)
            imported_count += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            errors.append(f"Row {i}: {str(e)}")

    from flask import current_app
    current_app.logger.info(f"Import summary: imported={imported_count}, errors={len(errors)}")
    if errors and imported_count == 0:
        return jsonify({'error': 'Import failed', 'details': errors}), 400
    
    db.session.commit()
    
    return jsonify({'message': f'{imported_count} records imported'})

@emissions_bp.route('/export', methods=['GET'])
@login_required  # SEC-01 FIX: was missing
def export_emissions():
    """Export emissions to JSON format"""
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    query = Emission.query
    
    # BUG-09 FIX: cast query params to int before filtering integer columns
    if request.args.get('facilityId'):
        try:
            query = query.filter(Emission.facility_id == int(request.args.get('facilityId')))
        except (ValueError, TypeError):
            pass
    if request.args.get('year'):
        try:
            query = query.filter(Emission.year == int(request.args.get('year')))
        except (ValueError, TypeError):
            pass
    if request.args.get('process'):
        query = query.filter(Emission.process_type == request.args.get('process'))
    
    emissions = query.all()
    
    export_data = []
    for r in emissions:
        export_data.append({
            'record_id': r.record_id,
            'year': r.year,
            'month': r.month,
            'facility': r.facility.name if r.facility else '',
            'group': r.group_name,
            'process': r.process_type,
            'fuel': r.fuel_type,
            'quantity': r.quantity,
            'unit': r.unit,
            'co2': r.co2_emissions,
            'ch4': r.ch4_emissions,
            'n2o': r.n2o_emissions,
            'co2e_total': r.co2e_total,
            'status': r.status
        })
    
    return jsonify({'data': export_data, 'count': len(export_data)})
