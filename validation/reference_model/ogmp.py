"""
Independent OGMP 2.0 Classification and Reconciliation Model.
Source of Truth: UNEP / OGMP 2.0 Framework Guidance.
Zero production dependencies.
"""

class IndependentOGMPModel:
    @staticmethod
    def classify_source_level(factor_source="default", calc_method="generic"):
        fs = str(factor_source or "").lower().strip()
        cm = str(calc_method or "").lower().strip()

        if fs in ("specific", "site_specific", "engineering", "cems", "direct_measurement") or cm in ("direct_measurement", "tier3", "engineering", "specific", "cems"):
            return 4
        if fs in ("custom", "api_table", "basin_specific", "component") or cm in ("tier2", "component_count", "custom_factor"):
            return 3
        if fs in ("default", "generic", "standard", "epa_table") or cm in ("tier1", "generic", "standard", "default"):
            return 2
        return 2

    @staticmethod
    def reconcile_survey(bottom_up_tch4, top_down_tch4, threshold=20.0):
        bu = float(bottom_up_tch4 or 0.0)
        td = float(top_down_tch4 or 0.0)
        t = float(threshold or 20.0)

        if bu > 0 and td > 0:
            variance_pct = ((td - bu) / bu) * 100.0
            variance_flag = abs(variance_pct) > t
            status = "Discrepancy Flagged" if variance_flag else "Reconciled"
            ratio = td / bu
        elif td > 0 and bu == 0:
            variance_pct = None
            variance_flag = True
            status = "Discrepancy Flagged"
            ratio = None
        elif bu > 0 and td == 0:
            variance_pct = None
            variance_flag = False
            status = "Bottom-Up Only"
            ratio = None
        else:
            variance_pct = None
            variance_flag = False
            status = "No Activity"
            ratio = None

        return {
            "bottom_up_tch4": bu,
            "top_down_tch4": td,
            "variance_pct": variance_pct,
            "variance_flag": variance_flag,
            "reconciliation_status": status,
            "ratio": ratio,
        }

    @staticmethod
    def classify_facility_level(bottom_up_tch4, top_down_tch4, bottom_up_source_level=3, threshold=20.0):
        recon = IndependentOGMPModel.reconcile_survey(bottom_up_tch4, top_down_tch4, threshold)
        td = float(top_down_tch4 or 0.0)
        bu = float(bottom_up_tch4 or 0.0)
        bu_lvl = int(bottom_up_source_level or 3)

        if td > 0 and recon["variance_pct"] is not None and abs(recon["variance_pct"]) <= float(threshold):
            return 5
        elif td > 0:
            return 4  # Top-down exists but variance > threshold
        elif bu_lvl >= 4:
            return 4
        elif bu_lvl >= 3 or bu > 0:
            return 3
        return 2
