path = 'new/server/routes/auth_settings.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        # If GWP standard was changed or set, recalculate existing emissions
        if gwp_changed:
            try:
                recalculate_all_emissions_gwp(_app_settings["gwp_standard"], previous=previous_gwp, user=user)
            except Exception as e:
                current_app.logger.error(f"Error recalculating emissions with new GWP: {e}")"""

new_block = """        # If GWP standard was changed or set, log methodology change audit and recalculate existing emissions
        if gwp_changed:
            try:
                log_activity_and_notify(
                    action="METHODOLOGY_CHANGE",
                    record_id="gwp_standard",
                    user=user,
                    request=request,
                    entity="SystemSetting",
                    details=f"Methodology change: active IPCC GWP standard switched from {previous_gwp} to {_app_settings['gwp_standard']}. Triggered full recalculation across Scope 1, Scope 2, and Scope 3.",
                )
            except Exception as e:
                current_app.logger.error(f"Audit log error on GWP methodology change: {e}")
            try:
                recalculate_all_emissions_gwp(_app_settings["gwp_standard"], previous=previous_gwp, user=user)
            except Exception as e:
                current_app.logger.error(f"Error recalculating emissions with new GWP: {e}")"""

content_norm = content.replace('\r\n', '\n')
assert old_block.replace('\r\n', '\n') in content_norm, "old_block not found in auth_settings.py"
content_norm = content_norm.replace(old_block.replace('\r\n', '\n'), new_block.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched auth_settings.py")
