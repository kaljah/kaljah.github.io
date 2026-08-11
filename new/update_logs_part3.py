import re
import os

def add_logs_to_file(file_path, injections):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for target, injection in injections:
        if injection not in content:
            content = content.replace(target, target + '\n' + injection)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

managedata_injections = [
    (
        "return jsonify({'message': f'{imported_count} production records imported'}), 201",
        "    try:\n        log_activity_and_notify('CREATE', 'bulk', f'Bulk imported {imported_count} production records', user=get_current_user(), request=request, entity='ProductionData')\n    except Exception as e:\n        pass"
    )
]
add_logs_to_file(r"C:\Users\samsung\Desktop\H2\new\server\routes\managedata.py", managedata_injections)

print("done part 3")
