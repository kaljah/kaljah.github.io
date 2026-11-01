path = 'new/client/src/pages/methane-intensity/MethaneIntensityOGMP20Level.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """  const hasDiscrepancy = ogmpSurveys.some((s) => {
    const status = (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase();
    const variance = s.variance_pct ?? s.reconciliation_variance_pct;
    return status.includes("discrepancy") || (variance !== null && Math.abs(variance) > (globalThreshold || 20.0));
  });

  const allReconciled = ogmpSurveys.length > 0 && !hasDiscrepancy && ogmpSurveys.every((s) => {
    const status = (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase();
    return status.includes("reconciled") && !status.includes("pending");
  });

  const badgeText = hasDiscrepancy
    ? t("Gold Standard Pathway: Level 5 Discrepancy Detected")
    : allReconciled
      ? t("Gold Standard Pathway: Level 5 Reconciled")
      : t("Gold Standard Pathway: Reconciliation Pending");"""

new_block = """  const hasDiscrepancy = ogmpSurveys.some((s) => {
    const status = (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase();
    const variance = s.variance_pct ?? s.reconciliation_variance_pct;
    const bu = Number(s.bottom_up_tch4 ?? s.bottomUpTch4 ?? 0);
    return status.includes("discrepancy") || s.variance_flag === true || (variance !== null && Math.abs(variance) > (globalThreshold || 20.0)) || bu === 0;
  });

  const allReconciled = ogmpSurveys.length > 0 && !hasDiscrepancy && ogmpSurveys.every((s) => {
    const status = (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase();
    return status.includes("reconciled") && !status.includes("pending");
  });

  const badgeText = hasDiscrepancy
    ? t("Gold Standard Pathway: Level 4 Discrepancy Detected")
    : allReconciled
      ? t("Gold Standard Pathway: Level 5 Reconciled")
      : t("Gold Standard Pathway: Reconciliation Pending");"""

content_norm = content.replace('\r\n', '\n')
assert old_block.replace('\r\n', '\n') in content_norm, "old_block not found in MethaneIntensityOGMP20Level.tsx"
content_norm = content_norm.replace(old_block.replace('\r\n', '\n'), new_block.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched MethaneIntensityOGMP20Level.tsx")
