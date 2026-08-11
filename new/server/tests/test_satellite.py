from unittest.mock import patch, MagicMock
from services.sentinel5p import sentinel5p_service, Sentinel5PService


def test_sentinel5p_flux_calculation():
    """
    Verifies the physical 1D box model / mass-divergence plume flux estimation.
    """
    # 50 ppb anomaly across a 7km box with 3.5 m/s wind and 1200m PBL
    emission_rate = sentinel5p_service.estimate_emission_rate_from_anomaly(
        delta_ch4_ppb=50.0, wind_speed_m_s=3.5, pbl_height_m=1200.0, box_width_km=7.0
    )
    assert emission_rate > 0.0
    # Zero or negative anomaly must return 0.0 kg/hr
    assert sentinel5p_service.estimate_emission_rate_from_anomaly(0.0) == 0.0
    assert sentinel5p_service.estimate_emission_rate_from_anomaly(-10.0) == 0.0


def test_sentinel5p_layer_config_unauthenticated():
    """
    Layer configuration returns ESA standard legend steps and unauthenticated status when no creds provided.
    """
    config = sentinel5p_service.get_layer_config(credentials=None)
    assert config["connected"] is False
    assert config["product_name"] == "Sentinel-5P TROPOMI Offline Level-3 Methane"
    assert config["unit"] == "ppb (parts per billion)"
    assert len(config["color_scale"]) >= 6


def test_sentinel5p_strict_no_fake_data_when_unconfigured():
    """
    Crucial policy test: Unconfigured / unauthenticated queries MUST return status 'unconfigured'
    with empty observations, NEVER fabricated or random synthetic plume numbers.
    """
    res = sentinel5p_service.query_satellite_observations(
        lat=31.67,
        lon=6.06,
        start_date="2024-01-01",
        end_date="2024-12-31",
        credentials=None,
    )
    assert res["status"] == "unconfigured"
    assert res["authenticated"] is False
    assert res["observations"] == []
    assert res["summary"] is None


def test_sentinel5p_connection_test_mocked_success():
    """
    Tests OAuth2 authentication flow with mock Copernicus Keycloak token endpoint.
    """
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock_jwt_token_12345",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response

        service = Sentinel5PService()
        result = service.test_connection(
            username="copernicus_user@domain.com", password="securePassword123"
        )
        assert result["success"] is True
        assert result["connected"] is True
        assert result["expires_in"] == 3600


def test_sentinel5p_connection_test_mocked_failure():
    """
    Tests OAuth2 rejection handling.
    """
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid user credentials",
        }
        mock_post.return_value = mock_response

        service = Sentinel5PService()
        result = service.test_connection(
            username="copernicus_user@domain.com", password="wrong_password"
        )
        assert result["success"] is False
        assert result["connected"] is False
        assert "Invalid user credentials" in result["message"]
