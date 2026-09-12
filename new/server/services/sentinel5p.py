"""
Sentinel-5P (TROPOMI) Satellite Methane Service
Connects to ESA Copernicus Data Space Ecosystem (CDSE) / Open Data STAC / OData API
and Google Earth Engine (COPERNICUS/S5P/OFFL/L3_CH4) dataset.

STRICT INTEGRITY POLICY:
Zero fake / synthetic numbers. If unauthenticated or offline, the service returns explicit
unconfigured/error statuses with no fabricated plume measurements.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

# Copernicus Data Space Ecosystem (CDSE) Endpoints
CDSE_AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CDSE_STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
CDSE_WMS_URL = "https://sh.dataspace.copernicus.eu/ogc/wms"

# Default ESA Sentinel-5P Methane Product Code
# S5P Offline Level-2/3 Methane (Total Column Mixing Ratio Dry Air)
S5P_CH4_PRODUCT_TYPE = "S5P_OFFL_L2__CH4___"
GEE_DATASET_ID = "COPERNICUS/S5P/OFFL/L3_CH4"

# Quality filtering threshold recommended by ESA/TROPOMI user manual (0.5 removes cloudy scenes)
DEFAULT_QA_THRESHOLD = 0.5

# Physical Constants for Plume Box Flux Calculation
MOLAR_MASS_CH4 = 16.042  # g/mol
AIR_MOLAR_MASS = 28.97  # g/mol
STD_AIR_DENSITY_SURFACE = 1.225  # kg/m3


class Sentinel5PService:
    """
    Service for querying ESA Copernicus Sentinel-5P TROPOMI methane measurements.
    """

    def __init__(self):
        self._token_cache: Dict[str, Any] = {}

    def test_connection(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tests authentication against Copernicus Data Space Ecosystem Keycloak endpoint.
        Supports both Resource Owner Password Credentials and Client Credentials OAuth2.
        """
        if not (username and password) and not (client_id and client_secret):
            return {
                "success": False,
                "connected": False,
                "message": "Missing credentials. Provide Copernicus Email & Password or Client ID & Secret.",
            }

        try:
            payload = {}
            if client_id and client_secret:
                payload = {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
            else:
                # Direct user login (cdse-public client ID)
                payload = {
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                    "client_id": "cdse-public",
                }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(
                CDSE_AUTH_URL, data=payload, headers=headers, timeout=12
            )

            if response.status_code == 200:
                token_data = response.json()
                expires_in = token_data.get("expires_in", 300)
                return {
                    "success": True,
                    "connected": True,
                    "message": "Successfully authenticated with Copernicus Data Space Ecosystem.",
                    "expires_in": expires_in,
                    "token_type": token_data.get("token_type", "Bearer"),
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                error_desc = "Authentication failed"
                try:
                    err_json = response.json()
                    error_desc = (
                        err_json.get("error_description")
                        or err_json.get("error")
                        or str(response.status_code)
                    )
                except Exception:
                    error_desc = response.text[:200]

                return {
                    "success": False,
                    "connected": False,
                    "message": f"Copernicus CDSE rejected credentials: {error_desc}",
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "connected": False,
                "message": "Connection to Copernicus Data Space timed out. Check network access to dataspace.copernicus.eu.",
            }
        except Exception as e:
            logger.error(f"[Sentinel5P] Connection test error: {e}", exc_info=True)
            return {
                "success": False,
                "connected": False,
                "message": f"Connection error: {str(e)}",
            }

    def get_token(self, credentials: Dict[str, Any]) -> Optional[str]:
        """
        Retrieves a valid JWT access token from Copernicus CDSE with caching.
        """
        username = credentials.get("copernicus_username") or credentials.get("username")
        password = credentials.get("copernicus_password") or credentials.get("password")
        client_id = credentials.get("copernicus_client_id") or credentials.get(
            "client_id"
        )
        client_secret = credentials.get("copernicus_client_secret") or credentials.get(
            "client_secret"
        )

        cache_key = f"{username or client_id}"
        if not cache_key:
            return None

        # Check existing valid token in cache
        cached = self._token_cache.get(cache_key)
        if cached:
            now_ts = datetime.now(timezone.utc).timestamp()
            if now_ts < cached.get("expires_at", 0) - 30:
                return cached.get("access_token")

        # Request new token
        res = self.test_connection(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
        )
        if not res.get("connected"):
            return None

        # If success, re-fetch full token payload to store access token
        try:
            if client_id and client_secret:
                payload = {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
            else:
                payload = {
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                    "client_id": "cdse-public",
                }
            r = requests.post(
                CDSE_AUTH_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            if r.status_code == 200:
                d = r.json()
                token = d.get("access_token")
                exp = d.get("expires_in", 300)
                self._token_cache[cache_key] = {
                    "access_token": token,
                    "expires_at": datetime.now(timezone.utc).timestamp() + exp,
                }
                return token
        except Exception as e:
            logger.error(f"[Sentinel5P] Error caching token: {e}")

        return None

    def get_layer_config(
        self, credentials: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Returns tile layer configuration, color ramps, and metadata for Leaflet.
        """
        has_creds = bool(
            credentials
            and (
                credentials.get("copernicus_username")
                or credentials.get("copernicus_client_id")
            )
        )

        return {
            "dataset": GEE_DATASET_ID,
            "product_name": "Sentinel-5P TROPOMI Offline Level-3 Methane",
            "provider": "ESA / Copernicus / DLR",
            "resolution": "5.5 km x 7 km",
            "revisit_time": "~2 days",
            "variable": "CH4_column_volume_mixing_ratio_dry_air",
            "unit": "ppb (parts per billion)",
            "qa_threshold_default": DEFAULT_QA_THRESHOLD,
            "connected": has_creds,
            "tile_layer_template": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/Sentinel-5P_TROPOMI_Tropospheric_Methane_Total_Column/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png",
            # Legend color steps matching standard ESA TROPOMI visualizers (1750 ppb to 1950+ ppb)
            "color_scale": [
                {
                    "value": 1750,
                    "color": "#313695",
                    "label": "< 1750 ppb (Clean Background)",
                },
                {"value": 1800, "color": "#4575b4", "label": "1800 ppb"},
                {
                    "value": 1850,
                    "color": "#74add1",
                    "label": "1850 ppb (Nominal Baseline)",
                },
                {"value": 1880, "color": "#e0f3f8", "label": "1880 ppb"},
                {
                    "value": 1900,
                    "color": "#fee090",
                    "label": "1900 ppb (Elevated Concentration)",
                },
                {
                    "value": 1925,
                    "color": "#fdae61",
                    "label": "1925 ppb (Plume Indicator)",
                },
                {
                    "value": 1950,
                    "color": "#f46d43",
                    "label": "1950 ppb (High Emission)",
                },
                {
                    "value": 1980,
                    "color": "#d73027",
                    "label": "> 1980 ppb (Super-Emitter Anomaly)",
                },
            ],
            "wms_url": CDSE_WMS_URL,
            "stac_url": CDSE_STAC_URL,
        }

    def query_satellite_observations(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        credentials: Optional[Dict[str, Any]] = None,
        qa_threshold: float = DEFAULT_QA_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Queries Copernicus STAC/OData API for real Sentinel-5P methane data around (lat, lon).
        Returns unconfigured status if credentials are not provided. Never outputs fake synthetic numbers.
        """
        if not credentials:
            return {
                "status": "unconfigured",
                "authenticated": False,
                "message": "Copernicus CDSE account not configured in Settings. Please provide credentials to query live satellite rasters.",
                "observations": [],
                "summary": None,
            }

        token = self.get_token(credentials)
        if not token:
            return {
                "status": "auth_failed",
                "authenticated": False,
                "message": "Failed to authenticate with Copernicus Data Space. Verify your credentials in Settings.",
                "observations": [],
                "summary": None,
            }

        # Build bounding box around facility (approx +/- 0.15 deg = ~15 km radius)
        delta = 0.15
        min_lon, min_lat = lon - delta, lat - delta
        max_lon, max_lat = lon + delta, lat + delta

        # Spatial filter polygon in WKT format
        wkt_polygon = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"

        try:
            # Query Copernicus OData Products catalog (ordered newest first)
            filter_parts = [
                "Collection/Name eq 'SENTINEL-5P'",
                "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'L2__CH4___')",
                f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt_polygon}')",
            ]
            if start_date:
                filter_parts.append(f"ContentDate/Start ge {start_date}T00:00:00.000Z")
            if end_date:
                filter_parts.append(f"ContentDate/End le {end_date}T23:59:59.999Z")

            odata_filter = " and ".join(filter_parts)

            params = {
                "$filter": odata_filter,
                "$orderby": "ContentDate/Start desc",
                "$top": 10,
            }
            headers = {"Authorization": f"Bearer {token}"}

            res = requests.get(
                CDSE_ODATA_URL, params=params, headers=headers, timeout=15
            )
            if res.status_code != 200:
                logger.warning(
                    f"[Sentinel5P] OData query returned HTTP {res.status_code}: {res.text[:200]}"
                )
                return {
                    "status": "query_error",
                    "authenticated": True,
                    "message": f"Copernicus catalog error (HTTP {res.status_code})",
                    "observations": [],
                    "summary": None,
                }

            data = res.json()
            products = data.get("value", [])

            observations = []
            for p in products:
                prod_id = p.get("Id")
                name = p.get("Name")
                date_start = p.get("ContentDate", {}).get("Start", "")

                observations.append(
                    {
                        "product_id": prod_id,
                        "product_name": name,
                        "sensing_time": date_start,
                        "footprint": p.get("Footprint"),
                        "qa_threshold": qa_threshold,
                        "source": "ESA Copernicus Data Space Ecosystem",
                    }
                )

            latest_obs = observations[0] if observations else {}
            raw_sensing = latest_obs.get("sensing_time", "")
            latest_date = (
                raw_sensing[:10]
                if raw_sensing
                else datetime.now(timezone.utc).strftime("%Y-%m-%d")
            )
            latest_time = raw_sensing[11:16] + " UTC" if len(raw_sensing) >= 16 else ""
            latest_prod_name = latest_obs.get("product_name", "")
            is_nrti = "NRTI" in latest_prod_name

            num_obs = len(observations)
            if num_obs == 0:
                return {
                    "status": "no_acquisitions",
                    "authenticated": True,
                    "facility_coordinates": {"latitude": lat, "longitude": lon},
                    "total_acquisitions_found": 0,
                    "observations": [],
                    "summary": None,
                    "message": "No Sentinel-5P TROPOMI methane overpasses found in Copernicus catalog for these coordinates.",
                }

            # Per Decision D-06: Zero synthetic/fabricated numbers. Return catalog observation metadata.
            return {
                "status": "metadata_only",
                "authenticated": True,
                "facility_coordinates": {"latitude": lat, "longitude": lon},
                "bounding_box": {
                    "min_lat": min_lat,
                    "min_lon": min_lon,
                    "max_lat": max_lat,
                    "max_lon": max_lon,
                },
                "total_acquisitions_found": len(observations),
                "observations": observations,
                "summary": None,
                "message": "Sentinel-5P observations found in Copernicus catalog. Quantitative pixel raster retrieval is not configured (metadata only).",
                "date_range": {
                    "start": start_date or "latest",
                    "end": end_date or latest_date,
                },
            }

        except Exception as e:
            logger.error(f"[Sentinel5P] Query error: {e}", exc_info=True)
            return {
                "status": "error",
                "authenticated": True,
                "message": f"Failed to retrieve satellite observations: {str(e)}",
                "observations": [],
                "summary": None,
            }

    @staticmethod
    def estimate_emission_rate_from_anomaly(
        delta_ch4_ppb: float,
        wind_speed_m_s: float = 3.5,
        pbl_height_m: float = 1200.0,
        box_width_km: float = 7.0,
    ) -> float:
        """
        Estimates methane mass emission rate (kg CH4/hr) from a Sentinel-5P column concentration anomaly (delta ppb)
        using the integrated mass-balance / 1D Gauss-box flux approach.

        Formula:
          Q = Delta_X (ppb) * 10^-9 * (P_surface / (R_spec_air * T)) * (M_CH4 / M_air) * Box_Width * Wind_Speed * PBL_Height
        """
        if delta_ch4_ppb <= 0:
            return 0.0

        # Molar mass ratio of CH4 to dry air
        mass_ratio = MOLAR_MASS_CH4 / AIR_MOLAR_MASS  # ~ 0.5537

        # Volume mixing ratio fraction
        vmr_fraction = delta_ch4_ppb * 1e-9

        # Column mass density anomaly (kg CH4 / m2 in boundary layer)
        # Delta_Mass_CH4 = vmr_fraction * mass_ratio * Air_Density_Surface * PBL_Height
        delta_column_mass_kg_m2 = (
            vmr_fraction * mass_ratio * STD_AIR_DENSITY_SURFACE * pbl_height_m
        )

        # Flux across downwind cross-section = Column_Mass * Box_Width_m * Wind_Speed_m_s (kg/s)
        box_width_m = box_width_km * 1000.0
        emission_rate_kg_s = delta_column_mass_kg_m2 * box_width_m * wind_speed_m_s

        # Convert to kg/hr
        emission_rate_kg_hr = emission_rate_kg_s * 3600.0
        return round(emission_rate_kg_hr, 2)


# Global singleton instance
sentinel5p_service = Sentinel5PService()
