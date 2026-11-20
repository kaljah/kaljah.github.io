"""Organisational boundary: the share of each facility's emissions the organisation reports (GHG Protocol Corporate
Standard ch. 3), one helper for every total.

The facilities carried `operator_status`, `equity_share_pct` and time-sliced `facility_equity_shares`, but no total
read them: every facility counted 100 % (audit 2026-11 F-AGG-01, Critical). The organisation-wide setting
`consolidation_approach` chooses:

- ``operational_control`` (default): 100 % of the facilities it operates, 0 % of the others;
- ``equity_share``: the organisation's equity share of each facility, time-weighted over the year from the share
  slices of the operator partner (the reporting company), else the facility's `equity_share_pct`.

A facility with the defaults (operated, 100 %) counts 100 % under both, so totals of a single-operator organisation
are unchanged.
"""

APPROACHES = ("operational_control", "equity_share")
DEFAULT_APPROACH = "operational_control"


def current_approach():
    from routes.auth_settings import _app_settings

    v = str(_app_settings.get("consolidation_approach") or DEFAULT_APPROACH).strip().lower()
    return v if v in APPROACHES else DEFAULT_APPROACH


class Weights:
    """weight(facility_id, year) -> fraction of the facility-year the organisation reports."""

    def __init__(self, approach=None):
        self.approach = approach or current_approach()
        self._fac = {}
        self._cache = {}

    def _facility(self, fid):
        if fid not in self._fac:
            from extensions import db
            from models import Facility

            self._fac[fid] = db.session.get(Facility, int(fid)) if fid not in (None, "total") else None
        return self._fac[fid]

    def __call__(self, fid, year=None):
        key = (fid, year)
        if key in self._cache:
            return self._cache[key]
        fac = self._facility(fid)
        if fac is None:
            w = 1.0
        elif self.approach == "operational_control":
            w = 0.0 if str(fac.operator_status or "operated").strip().lower() in ("non_operated", "non-operated",
                                                                                   "nonoperated") else 1.0
        else:
            w = self._equity(fac, year) / 100.0
        self._cache[key] = w
        return w

    @staticmethod
    def _equity(fac, year):
        """The reporting company's equity % for the year (time-weighted slices of the operator partner)."""
        from models import FacilityEquityShare, JvPartner
        from utils import tenant_matches

        default = float(100.0 if fac.equity_share_pct is None else fac.equity_share_pct)
        if year in (None, "", "all"):
            return default
        operator = (JvPartner.query.filter_by(is_operator=True)
                    .filter(tenant_matches(JvPartner.tenant_id, getattr(fac, "tenant_id", None) or "default")).first())
        if operator is None:
            return default
        slices = FacilityEquityShare.query.filter_by(facility_id=fac.id, partner_id=operator.id).all()
        if not slices:
            return default
        from routes.equity_routes import effective_share_pct

        pct = effective_share_pct(slices, int(year), None)
        return default if pct is None else float(pct)


def weighted(value, fid, year, weights):
    return float(value or 0.0) * weights(fid, year)
