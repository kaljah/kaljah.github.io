"""Dashboard cache invalidation across workers (hardening plan, phase 3).

/api/dashboard/batch-all caches its whole result per process. Another worker invalidates by
bumping a shared epoch; this worker must look at that epoch on every request, including
requests that would be answered from its own cache, or it serves stale data until the TTL.
"""
import pytest

from app import app
from tests.audit_helpers import login, make_user


@pytest.fixture()
def admin_client():
    from routes import dashboard as dash

    dash.DASHBOARD_CACHE.clear()
    admin = make_user("admin")
    client = app.test_client()
    login(client, admin)
    yield client
    dash.DASHBOARD_CACHE.clear()


URL = "/api/dashboard/batch-all?year=all"


def _batch_keys(dash):
    return [k for k in list(dash.DASHBOARD_CACHE.keys()) if isinstance(k, tuple) and k and k[0] == "batch_all"]


def test_cache_hit_still_consults_the_shared_epoch(admin_client, monkeypatch):
    from routes import dashboard as dash

    assert admin_client.get(URL).status_code == 200  # fills the cache
    assert _batch_keys(dash), "batch-all result was not cached"

    calls = []
    real = dash._get_global_cache_epoch

    def spy():
        calls.append(1)
        return real()

    monkeypatch.setattr(dash, "_get_global_cache_epoch", spy)
    assert admin_client.get(URL).status_code == 200  # answered from the cache
    assert calls, "a cache hit must still check whether another worker invalidated the cache"


def test_invalidation_from_another_worker_drops_the_cached_result(admin_client, monkeypatch):
    from routes import dashboard as dash

    assert admin_client.get(URL).status_code == 200
    (key,) = _batch_keys(dash)
    dash.DASHBOARD_CACHE[key] = {"sentinel": "stale"}

    # What _get_global_cache_epoch does when another worker has bumped the epoch.
    def other_worker_invalidated():
        dash.DASHBOARD_CACHE.clear()
        return 0.0

    monkeypatch.setattr(dash, "_get_global_cache_epoch", other_worker_invalidated)
    body = admin_client.get(URL).get_json()
    assert "sentinel" not in body
    assert "summary" in body or "years" in body


def test_cache_still_serves_hits_when_nothing_changed(admin_client):
    from routes import dashboard as dash

    assert admin_client.get(URL).status_code == 200
    (key,) = _batch_keys(dash)
    dash.DASHBOARD_CACHE[key] = {"sentinel": "cached"}
    assert admin_client.get(URL).get_json() == {"sentinel": "cached"}


def test_cache_stats_count_hits_and_misses(admin_client):
    from routes import dashboard as dash

    dash.reset_cache_stats()
    admin_client.get(URL)
    admin_client.get(URL)
    stats = dash.cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 1
