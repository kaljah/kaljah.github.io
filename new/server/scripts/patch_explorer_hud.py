path = 'new/client/src/pages/explorer/ExplorerHud.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        <Metric label={t("Monitored assets")}>{metrics.activeAssets}</Metric>
        <Metric label={viewMode === "methane" ? t("Regional methane") : t("Regional GHG")} tone="accent">
          {formatCompact(regional)} t
        </Metric>
        <Metric label={t("Mean loss intensity")}>
          {metrics.avgMethaneIntensity} <span className="text-xs font-medium text-text-secondary">kg/boe</span>
        </Metric>
        <Metric label={t("Super-emitters")} tone={(metrics.superEmitters ?? 0) > 0 ? "alert" : undefined}>
          {metrics.superEmitters}
        </Metric>"""

new_block = """        <Metric label={t("Monitored assets")}>{metrics.activeAssets}</Metric>
        <Metric label={viewMode === "methane" ? t("Geolocated methane (On Map)") : t("Geolocated GHG (On Map)")} tone="accent">
          {formatCompact(regional)} t
        </Metric>
        <Metric label={t("Mean loss intensity")}>
          {metrics.avgMethaneIntensity} <span className="text-xs font-medium text-text-secondary">kg/boe</span>
        </Metric>
        <Metric label={t("Super-emitters")} tone={(metrics.superEmitters ?? 0) > 0 ? "alert" : undefined}>
          {metrics.superEmitters} of {metrics.activeAssets}
        </Metric>"""

content_norm = content.replace('\r\n', '\n')
assert old_block.replace('\r\n', '\n') in content_norm, "old_block not found in ExplorerHud.tsx"
content_norm = content_norm.replace(old_block.replace('\r\n', '\n'), new_block.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched ExplorerHud.tsx")
