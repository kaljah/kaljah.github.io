import sys
import json
import os

sys.path.insert(0, os.path.abspath('new/server'))
from app import app
from models import db, User

app.config['TESTING'] = True
client = app.test_client()

with app.app_context():
    user = User.query.filter_by(role='admin').first()
    if not user:
        user = User.query.first()
    admin_id = user.id if user else 1
    admin_sv = user.session_version if (user and hasattr(user, 'session_version')) else 1

endpoints = []
for rule in app.url_map.iter_rules():
    if not rule.rule.startswith('/api'):
        continue
    methods = [m for m in rule.methods if m in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')]
    endpoints.append((rule.rule, methods))

endpoints.sort()
print(f"Sweeping {len(endpoints)} API rules...")

extreme_payloads = [
    ('empty_dict', {}),
    ('empty_list', []),
    ('null_literal', 'null'),
    ('extreme_numbers', {'quantity': 1e30, 'year': 999999, 'month': -1, 'fuel': 'gas'}),
    ('extreme_negatives', {'quantity': -500.0, 'operating_hours': -100}),
    ('sqli_strings', {'name': "' OR 1=1 --", 'fuel': "' UNION SELECT * FROM users --"}),
    ('xss_strings', {'facility_name': '<script>alert(1)</script>', 'description': '<img src=x onerror=alert(1)>'}),
    ('types_mismatch', {'quantity': 'not_a_number', 'year': 'invalid_year'}),
    ('malformed_json_str', '{bad_json: "unterminated}'),
]

findings = []
total_calls = 0

for rule_str, methods in endpoints:
    test_path = rule_str
    for part in rule_str.split('/'):
        if part.startswith('<') and part.endswith('>'):
            test_path = test_path.replace(part, '1')

    for m in methods:
        total_calls += 1
        # 1. Unauthenticated test
        try:
            if m == 'GET':
                resp = client.get(test_path)
            elif m == 'POST':
                resp = client.post(test_path, json={})
            elif m == 'PUT':
                resp = client.put(test_path, json={})
            elif m == 'DELETE':
                resp = client.delete(test_path)
            else:
                resp = client.open(test_path, method=m)

            if resp.status_code == 500:
                findings.append({
                    'endpoint': test_path,
                    'method': m,
                    'status': 500,
                    'condition': 'unauthenticated basic request',
                    'data': resp.get_json(silent=True) or resp.data.decode('utf-8', errors='ignore')[:300]
                })
        except Exception as e:
            findings.append({
                'endpoint': test_path,
                'method': m,
                'status': 'CRASH',
                'condition': 'unauthenticated exception',
                'data': str(e)
            })

        # 2. Authenticated tests
        try:
            with client.session_transaction() as sess:
                sess['user_id'] = admin_id
                sess['sv'] = admin_sv

            if m == 'GET':
                resp = client.get(test_path)
                if resp.status_code == 500:
                    findings.append({
                        'endpoint': test_path,
                        'method': m,
                        'status': 500,
                        'condition': 'authenticated GET',
                        'data': resp.get_json(silent=True) or resp.data.decode('utf-8', errors='ignore')[:300]
                    })
            elif m in ('POST', 'PUT', 'PATCH'):
                for p_name, payload in extreme_payloads:
                    total_calls += 1
                    try:
                        with client.session_transaction() as sess:
                            sess['user_id'] = admin_id
                            sess['sv'] = admin_sv

                        if p_name == 'malformed_json_str':
                            resp = client.open(test_path, method=m, data=payload, content_type='application/json')
                        elif p_name == 'null_literal':
                            resp = client.open(test_path, method=m, data='null', content_type='application/json')
                        elif p_name == 'empty_list':
                            resp = client.open(test_path, method=m, data='[]', content_type='application/json')
                        else:
                            resp = client.open(test_path, method=m, json=payload)

                        if resp.status_code == 500:
                            findings.append({
                                'endpoint': test_path,
                                'method': m,
                                'status': 500,
                                'condition': f'authenticated_{p_name}',
                                'data': resp.get_json(silent=True) or resp.data.decode('utf-8', errors='ignore')[:300]
                            })
                    except Exception as e:
                        findings.append({
                            'endpoint': test_path,
                            'method': m,
                            'status': 'CRASH',
                            'condition': f'exception_{p_name}',
                            'data': str(e)
                        })
        except Exception as e:
            findings.append({
                'endpoint': test_path,
                'method': m,
                'status': 'CRASH',
                'condition': 'authenticated setup exception',
                'data': str(e)
            })

print(f"Total API calls executed: {total_calls}")
print(f"Found {len(findings)} HTTP 500 errors or unhandled crashes!")

os.makedirs('audit/automated_sweep', exist_ok=True)
with open('audit/automated_sweep/api_endpoint_sweep.json', 'w', encoding='utf-8') as f:
    json.dump(findings, f, indent=2)

for fd in findings[:30]:
    print(f"[{fd['status']}] {fd['method']} {fd['endpoint']} ({fd['condition']})")
