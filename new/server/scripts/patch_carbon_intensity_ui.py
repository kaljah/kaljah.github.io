path = 'new/client/src/pages/carbon-intensity/CarbonIntensityCarbonIntensity.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_line = '<ProdItem label={t("Total Flared (All Inventory Sources)")} value={`${formatNumber(stats.totalFlaringVolume, 0)} m³`} accent="text-brand-600" />'
new_line = '<ProdItem label={t("Total Flared Gas (Decree 21-330 Streams)")} value={`${formatNumber(stats.totalFlaringVolume, 0)} m³`} accent="text-brand-600" />'

content = content.replace(old_line, new_line, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched CarbonIntensityCarbonIntensity.tsx")
