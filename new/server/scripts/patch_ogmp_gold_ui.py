path = 'new/client/src/pages/methane-intensity/MethaneIntensityOGMP20Gold.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """            const matchedSurvey = ogmpSurveys.find(
              (s) =>
                String(s.facilityId || s.facility_id) ===
                  String(fac.facility_id || fac.id) ||
                (s.facility_name || s.facilityName) === facName,
            );
            const threshold = Number(
              fac.reconciliation_threshold ?? globalThreshold ?? 20.0,
            );
            const variancePct =
              fac.reconciliation_variance_pct ??
              fac.variance_pct ??
              (matchedSurvey
                ? (matchedSurvey.reconciliation_variance_pct ?? matchedSurvey.variance_pct ?? null)
                : null);
            const passThreshold =
              variancePct !== null
                ? Math.abs(variancePct) <= threshold
                : false;

            const highestLevel =
              fac.highest_ogmp_level ||
              fac.current_ogmp_level ||
              (matchedSurvey && passThreshold ? 5 : matchedSurvey ? 4 : 3);
            const isReconciled =
              fac.is_reconciled !== undefined
                ? fac.is_reconciled
                : (highestLevel >= 5 && passThreshold);

            let statusBadgeClass = "ontrack";
            let statusText = yearsLeft > 0
              ? t("On Track ({{years}} yrs to Level 5)", { years: yearsLeft })
              : t("On Track (Target Year)");
            if (isReconciled && highestLevel >= 5) {
              statusBadgeClass = "achieved";
              statusText = t("Gold Standard Achieved (Level 5)");
            } else if (yearsLeft < 0) {
              statusBadgeClass = "action";
              statusText = t("Action Plan Required (Overdue)");
            } else if (yearsLeft === 0) {
              statusBadgeClass = "ontrack";
              statusText = t("Target Milestone Year (Level 5 Due)");
            }"""

new_block = """            const matchedSurveys = ogmpSurveys.filter(
              (s) =>
                String(s.facilityId || s.facility_id) ===
                  String(fac.facility_id || fac.id) ||
                (s.facility_name || s.facilityName) === facName,
            );
            const threshold = Number(
              fac.reconciliation_threshold ?? globalThreshold ?? 20.0,
            );
            const hasSurveyDiscrepancy = (fac.reconciliation_status || "").toLowerCase().includes("discrepancy") ||
              fac.variance_flag === true ||
              matchedSurveys.some((s) => {
                const status = (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase();
                const variance = s.variance_pct ?? s.reconciliation_variance_pct;
                const bu = Number(s.bottom_up_tch4 ?? s.bottomUpTch4 ?? 0);
                return status.includes("discrepancy") || s.variance_flag === true || (variance !== null && Math.abs(variance) > threshold) || bu === 0;
              });

            const hasSurveyReconciled = !hasSurveyDiscrepancy && (
              (fac.reconciliation_status || "").toLowerCase() === "reconciled" ||
              (matchedSurveys.length > 0 && matchedSurveys.some((s) => (s.reconciliationStatus || s.reconciliation_status || "").toLowerCase().includes("reconciled")))
            );

            const highestLevel = hasSurveyDiscrepancy
              ? Math.min(4, Number(fac.highest_ogmp_level || fac.current_ogmp_level || 4))
              : hasSurveyReconciled
                ? 5
                : Number(fac.highest_ogmp_level || fac.current_ogmp_level || 3);

            const isReconciled = hasSurveyReconciled && highestLevel >= 5;

            let statusBadgeClass = "ontrack";
            let statusText = yearsLeft > 0
              ? t("On Track ({{years}} yrs to Level 5)", { years: yearsLeft })
              : t("On Track (Target Year)");

            if (hasSurveyDiscrepancy) {
              statusBadgeClass = "action";
              statusText = t("Discrepancy Detected (Level 4 - Action Required)");
            } else if (isReconciled && highestLevel >= 5) {
              statusBadgeClass = "achieved";
              statusText = t("Gold Standard Achieved (Level 5)");
            } else if (yearsLeft < 0) {
              statusBadgeClass = "action";
              statusText = t("Action Plan Required (Overdue)");
            } else if (yearsLeft === 0) {
              statusBadgeClass = "ontrack";
              statusText = t("Target Milestone Year (Level 5 Due)");
            }"""

content_norm = content.replace('\r\n', '\n')
assert old_block.replace('\r\n', '\n') in content_norm, "old_block not found in MethaneIntensityOGMP20Gold.tsx"
content_norm = content_norm.replace(old_block.replace('\r\n', '\n'), new_block.replace('\r\n', '\n'), 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully patched MethaneIntensityOGMP20Gold.tsx")
