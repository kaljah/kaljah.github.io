"""
EPA Supply Chain Greenhouse Gas Emission Factors v1.3.0 by NAICS-6 (USEEIO v2.2.22-GHG, U.S. GHG data
for 2022, IPCC AR5 100-yr GWPs), kg CO2e per 2022 USD at purchaser price, supply chain factors WITH
margins (the ones for spend data). Source file shipped in data/, downloaded from
https://pasteur.epa.gov/uploads/10.23719/1531143/ (catalog: catalog.data.gov, "Supply Chain Greenhouse
Gas Emission Factors v1.3 by NAICS-6").

The dataset has 1,016 six-digit 2017 NAICS commodities and excludes electricity, government and
households. A code is looked up exactly: the previous table (3-digit codes with values not in the
EPA dataset, and a 350 kg / $1,000 "generic spend" fallback) is replaced.
"""
import csv
import os

_CSV = os.path.join(os.path.dirname(__file__), "data", "SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv")
SOURCE = "EPA Supply Chain GHG Emission Factors v1.3.0 (NAICS-6, 2022 USD, AR5, with margins)"


def _load():
    out = {}
    with open(_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            code = str(row["2017 NAICS Code"]).strip()
            per_usd = float(row["Supply Chain Emission Factors with Margins"])
            out[code] = {"name": row["2017 NAICS Title"].strip(), "kg_co2e_per_usd": per_usd,
                         "kg_co2e_per_1000_usd": round(per_usd * 1000.0, 6), "source": SOURCE}
    return out


EEIO_FACTORS = _load()


def get_eeio_factor(naics_code: str) -> dict:
    """Factor of a six-digit 2017 NAICS code. Raises LookupError for anything else (no fallback)."""
    code = str(naics_code or "").strip()
    row = EEIO_FACTORS.get(code)
    if row is None:
        if not code.isdigit() or len(code) != 6:
            raise LookupError(f"NAICS code '{code}' must be a six-digit 2017 NAICS code (e.g. 331110)")
        raise LookupError(f"NAICS code '{code}' is not in the EPA supply chain factor dataset "
                          "(electricity, government and household codes are not covered)")
    return row


def search_eeio_factors(query: str, limit: int = 25) -> list:
    """Codes whose number starts with, or whose title contains, the query."""
    q = str(query or "").strip().lower()
    if not q:
        return []
    hits = [{"naics": k, **v} for k, v in EEIO_FACTORS.items() if k.startswith(q) or q in v["name"].lower()]
    return hits[:limit]
