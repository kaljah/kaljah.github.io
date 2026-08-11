--
--
--
--
    from flask import request, jsonify, session
    data = request.get_json() or {}
    record_id = data.get('id')
    facility_id = data.get('facility_id') or data.get('facilityId')
    year = int(data.get('year', 2026))
    month = int(data.get('month', 1))
    product_name = (data.get('product_name') or data.get('productName') or '').strip()
    cn_code = (data.get('cn_code') or data.get('cnCode') or '').strip()
        traceback.print_exc()
--
