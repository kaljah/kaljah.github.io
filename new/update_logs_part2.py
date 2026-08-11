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
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for target, injection in injections:
        if injection not in content:
            content = content.replace(target, target + '\n' + injection)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

# managedata.py (part 2)
managedata_injections = [
    (
        "return jsonify({'message': 'Mitigation project added', 'id': p.id}), 201",
        "    try:\n        log_activity_and_notify('CREATE', p.id, f'Added mitigation project {p.name}', user=get_current_user(), request=request, entity='MitigationProject')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Mitigation project deleted'})",
        "    try:\n        log_activity_and_notify('DELETE', mitigation_id, f'Deleted mitigation project', user=get_current_user(), request=request, entity='MitigationProject')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': f'{imported_count} mitigation projects imported'}), 201",
        "    try:\n        log_activity_and_notify('CREATE', 'bulk', f'Bulk imported {imported_count} mitigation projects', user=get_current_user(), request=request, entity='MitigationProject')\n    except Exception as e:\n        pass"
    )
]
add_logs_to_file(r"C:\Users\samsung\Desktop\H2\new\server\routes\managedata.py", managedata_injections)

# scope2.py
insert_import(r"C:\Users\samsung\Desktop\H2\new\server\routes\scope2.py")
scope2_injections = [
    (
        "return jsonify({'message': 'Scope 2 Emission created successfully', 'id': emission.id}), 201",
        "    try:\n        log_activity_and_notify('CREATE', emission.id, f'Added Scope 2 emission for {emission.month}/{emission.year}', user=get_current_user(), request=request, entity='Scope2Emission')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Scope 2 Emission updated successfully'})",
        "    try:\n        log_activity_and_notify('UPDATE', emission.id, f'Updated Scope 2 emission', user=get_current_user(), request=request, entity='Scope2Emission')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Scope 2 Emission deleted successfully'})",
        "    try:\n        log_activity_and_notify('DELETE', emission_id, f'Deleted Scope 2 emission', user=get_current_user(), request=request, entity='Scope2Emission')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': f'Successfully imported {imported_count} Scope 2 records.'}), 201",
        "    try:\n        log_activity_and_notify('CREATE', 'bulk', f'Bulk imported {imported_count} Scope 2 records', user=get_current_user(), request=request, entity='Scope2Emission')\n    except Exception as e:\n        pass"
    )
]
add_logs_to_file(r"C:\Users\samsung\Desktop\H2\new\server\routes\scope2.py", scope2_injections)

# scope3.py
insert_import(r"C:\Users\samsung\Desktop\H2\new\server\routes\scope3.py")
scope3_injections = [
    (
        "return jsonify({'message': 'Scope 3 record added', 'id': record.id}), 201",
        "    try:\n        log_activity_and_notify('CREATE', record.id, f'Added Scope 3 emission for {record.category}', user=get_current_user(), request=request, entity='Scope3Emission')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Scope 3 record updated'})",
        "    try:\n        log_activity_and_notify('UPDATE', emission.id, f'Updated Scope 3 emission', user=get_current_user(), request=request, entity='Scope3Emission')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': 'Scope 3 record deleted'})",
        "    try:\n        log_activity_and_notify('DELETE', emission_id, f'Deleted Scope 3 emission', user=get_current_user(), request=request, entity='Scope3Emission')\n    except Exception as e:\n        pass"
    ),
    (
        "return jsonify({'message': f'Imported {imported_count} scope 3 records'}), 201",
        "    try:\n        log_activity_and_notify('CREATE', 'bulk', f'Bulk imported {imported_count} Scope 3 records', user=get_current_user(), request=request, entity='Scope3Emission')\n    except Exception as e:\n        pass"
    )
]
add_logs_to_file(r"C:\Users\samsung\Desktop\H2\new\server\routes\scope3.py", scope3_injections)

print("done part 2")
