"""
Health Check & Diagnostic Endpoints (Item 4.3)
==============================================
Provides production-grade liveness, readiness, and deep system diagnostics:
- Database connectivity & query latency
- Host memory utilization
- Filesystem disk capacity
"""
import os
import time
import shutil
import datetime
from flask import Blueprint, jsonify, current_app
from extensions import db
from sqlalchemy import text

health_bp = Blueprint("health", __name__)

_START_TIME = time.time()


@health_bp.route("/health", methods=["GET"])
@health_bp.route("/api/health", methods=["GET"])
def health_summary():
    """Comprehensive diagnostic endpoint checking database, memory, and disk health."""
    db_ok = False
    db_latency_ms = None
    db_error = None
    
    t0 = time.perf_counter()
    try:
        db.session.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_ok = True
    except Exception as e:
        db_error = str(e)

    # Memory utilization
    memory_info = {}
    try:
        import psutil
        mem = psutil.virtual_memory()
        memory_info = {
            "status": "warning" if mem.percent > 90 else "ok",
            "used_pct": round(mem.percent, 1),
            "available_mb": round(mem.available / (1024 * 1024), 1),
            "total_mb": round(mem.total / (1024 * 1024), 1),
        }
    except Exception:
        memory_info = {"status": "unmonitored"}

    # Disk capacity
    disk_info = {}
    try:
        root_dir = os.path.abspath(os.path.dirname(__file__))
        usage = shutil.disk_usage(root_dir)
        disk_used_pct = round((usage.used / usage.total) * 100, 1)
        disk_info = {
            "status": "warning" if disk_used_pct > 90 else "ok",
            "used_pct": disk_used_pct,
            "free_gb": round(usage.free / (1024 * 1024 * 1024), 2),
            "total_gb": round(usage.total / (1024 * 1024 * 1024), 2),
        }
    except Exception:
        disk_info = {"status": "unmonitored"}

    uptime_sec = int(time.time() - _START_TIME)
    is_healthy = db_ok and (memory_info.get("status") != "critical")

    backend_name = db.engine.url.get_backend_name()
    # Mask connection details in production
    db_backend = "sqlite" if "sqlite" in backend_name.lower() else "postgresql"

    payload = {
        "status": "healthy" if is_healthy else "unhealthy",
        "version": current_app.config.get("APP_VERSION", "1.0.0"),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "uptime_seconds": uptime_sec,
        "checks": {
            "database": {
                "status": "connected" if db_ok else "unreachable",
                "backend": db_backend,
                "latency_ms": db_latency_ms,
                "error": db_error if not db_ok else None,
            },
            "memory": memory_info,
            "disk": disk_info,
        }
    }

    status_code = 200 if is_healthy else 503
    return jsonify(payload), status_code


@health_bp.route("/api/health/live", methods=["GET"])
def health_liveness():
    """Kubernetes / Docker shallow liveness probe."""
    return jsonify({
        "status": "alive",
        "version": current_app.config.get("APP_VERSION", "1.0.0")
    }), 200


@health_bp.route("/api/health/ready", methods=["GET"])
def health_readiness():
    """Kubernetes / Docker deep readiness probe verifying DB pool readiness."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "ready",
            "database": "connected",
            "version": current_app.config.get("APP_VERSION", "1.0.0")
        }), 200
    except Exception as e:
        current_app.logger.error(f"Readiness probe failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "database": "unreachable",
            "error": "Database connectivity check failed"
        }), 503
