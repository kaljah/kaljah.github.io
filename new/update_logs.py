import re
import os

def insert_import(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    if 'log_activity_and_notify' not in content:
        content = content.replace('from utils import', 'from utils import log_activity_and_notify,')
        with open(file_path, 'w') as f:
            f.write(content)

def add_logs_to_file(file_path, injections):
    with open(file_path, 'r') as f:
        content = f.read()

    for target, injection in injections:
        if injection not in content:
            content = content.replace(target, target + '\n' + injection)
            
    with open(file_path, 'w') as f:
        f.write(content)

# managedata.py
insert_import(r"C:\Users\samsung\Desktop\H2\new\server\routes\managedata.py")
managedata_injections = [
    (
        "return jsonify({'message': 'Source added', 'id': source.id}), 201",
        "    try:\n        log_activity_and_notify('CREATE', source.id, f'Added emission source {source.name}', user=get_current_user(), request=request, entity='EmissionSource')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Source deleted'})",
        "    try:\n        log_activity_and_notify('DELETE', source_id, f'Deleted emission source', user=get_current_user(), request=request, entity='EmissionSource')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': f'{imported_count} sources imported'}), 201",
        "    try:\n        log_activity_and_notify('CREATE', 'bulk', f'Bulk imported {imported_count} emission sources', user=get_current_user(), request=request, entity='EmissionSource')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Settings saved successfully'})",
        "    try:\n        log_activity_and_notify('UPDATE', data.get('year'), f'Updated reporting metadata for {data.get(\"year\")}', user=get_current_user(), request=request, entity='ReportingMetadata')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': f'Goal for {data.get(\"year\")} saved successfully'})",
        "    try:\n        log_activity_and_notify('CREATE', data.get('year'), f'Saved goal for {data.get(\"year\")}', user=get_current_user(), request=request, entity='Goal')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Goal deleted'})",
        "    try:\n        log_activity_and_notify('DELETE', year, f'Deleted goal for {year}', user=get_current_user(), request=request, entity='Goal')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Base year locked', 'year': data.get('year')})",
        "    try:\n        log_activity_and_notify('CREATE', data.get('year'), f'Locked base year {data.get(\"year\")}', user=get_current_user(), request=request, entity='BaseYear')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Base year deleted'})",
        "    try:\n        log_activity_and_notify('DELETE', rec_id, f'Deleted base year {rec_id}', user=get_current_user(), request=request, entity='BaseYear')\n    except Exception as e:\n        pass"
    )
]
add_logs_to_file(r"C:\Users\samsung\Desktop\H2\new\server\routes\managedata.py", managedata_injections)

print("done")
