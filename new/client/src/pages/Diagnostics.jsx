import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import "./Diagnostics.css";

const Diagnostics = () => {
  const { user } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [diagnostics, setDiagnostics] = useState(null);

  useEffect(() => {
    runDiagnostics();
  }, []);

  const runDiagnostics = async () => {
    setLoading(true);
    try {
      const [emissionsRes, facilitiesRes, factorsRes] = await Promise.all([
        api.get("/emissions"),
        api.get("/facilities"),
        api.get("/custom-factors"),
      ]);

      const emissions = emissionsRes.data.emissions || emissionsRes.data || [];
      const facilities = facilitiesRes.data || [];
      const factors = factorsRes.data || [];

      const results = analyzeData(emissions, facilities, factors);
      setDiagnostics(results);
    } catch (error) {
      console.error("Diagnostics failed:", error);
      toast.error("Failed to run diagnostics");
    } finally {
      setLoading(false);
    }
  };

  const analyzeData = (emissions, facilities, factors) => {
    const issues = [];
    const warnings = [];
    const suggestions = [];

    // Check for missing data
    const missingFacility = emissions.filter((e) => !e.facility_id).length;
    const missingFuel = emissions.filter(
      (e) => !e.fuel_type && !e.source_type,
    ).length;
    const missingAmount = emissions.filter(
      (e) => !e.amount || e.amount === 0,
    ).length;

    if (missingFacility > 0) {
      issues.push({
        type: "error",
        title: "Missing Facility Data",
        description: `${missingFacility} emission records lack facility assignment`,
        impact: "High",
      });
    }

    if (missingFuel > 0) {
      warnings.push({
        type: "warning",
        title: "Missing Fuel/Source Type",
        description: `${missingFuel} records missing fuel or source type`,
        impact: "Medium",
      });
    }

    if (missingAmount > 0) {
      warnings.push({
        type: "warning",
        title: "Zero or Missing Amounts",
        description: `${missingAmount} records have zero or missing amount values`,
        impact: "Medium",
      });
    }

    // Check for data quality
    const recentRecords = emissions.filter((e) => {
      const recordDate = new Date(e.date);
      const daysSince = (new Date() - recordDate) / (1000 * 60 * 60 * 24);
      return daysSince <= 30;
    }).length;

    if (recentRecords === 0 && emissions.length > 0) {
      warnings.push({
        type: "warning",
        title: "No Recent Data",
        description: "No emissions recorded in the last 30 days",
        impact: "Low",
      });
    }

    // Check facilities
    const facilitiesWithoutData = facilities.filter(
      (f) => !emissions.some((e) => e.facility_id === f.id),
    ).length;

    if (facilitiesWithoutData > 0) {
      suggestions.push({
        type: "info",
        title: "Unused Facilities",
        description: `${facilitiesWithoutData} facilities have no emission records`,
        impact: "Low",
      });
    }

    // Check custom factors
    if (factors.length === 0) {
      suggestions.push({
        type: "info",
        title: "No Custom Factors",
        description:
          "Consider adding custom emission factors for better accuracy",
        impact: "Low",
      });
    }

    // Calculate completeness score
    const totalFields = emissions.length * 8; // 8 key fields per record
    const completedFields = emissions.reduce((sum, e) => {
      let count = 0;
      if (e.facility_id) count++;
      if (e.fuel_type || e.source_type) count++;
      if (e.amount && e.amount > 0) count++;
      if (e.unit) count++;
      if (e.date) count++;
      if (e.co2_emissions !== null) count++;
      if (e.ch4_emissions !== null) count++;
      if (e.n2o_emissions !== null) count++;
      return sum + count;
    }, 0);

    const completeness =
      totalFields > 0 ? (completedFields / totalFields) * 100 : 100;

    return {
      completeness: Math.round(completeness),
      totalRecords: emissions.length,
      totalFacilities: facilities.length,
      totalFactors: factors.length,
      recentRecords,
      issues,
      warnings,
      suggestions,
    };
  };

  if (loading) {
    return <LoadingSpinner fullScreen message="Running diagnostics..." />;
  }

  if (!diagnostics) {
    return (
      <div className="diagnostics">
        <div className="empty-state">No data to analyze</div>
      </div>
    );
  }

  const {
    completeness,
    totalRecords,
    totalFacilities,
    totalFactors,
    recentRecords,
    issues,
    warnings,
    suggestions,
  } = diagnostics;
  const healthScore = Math.max(
    0,
    completeness - issues.length * 10 - warnings.length * 5,
  );

  return (
    <div className="diagnostics">
      <header className="top-bar">
        <div className="breadcrumbs">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ marginRight: "8px" }}
          >
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
          <span>Dashboard</span>
          <span style={{ margin: "0 8px", color: "var(--text-secondary)" }}>
            /
          </span>
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
            Diagnostics
          </span>
        </div>
        <div className="top-actions">
          <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>
            {user?.fullName || "User"}
          </span>
        </div>
      </header>

      <div className="diagnostics-container">
        <div
          style={{
            marginBottom: "30px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h2
              className="section-title"
              style={{ color: "#f59e0b", marginBottom: "5px" }}
            >
              Data Quality Diagnostics
            </h2>
            <p style={{ color: "var(--text-secondary)" }}>
              System health checks and data validation
            </p>
          </div>
          <button
            className="btn-refresh"
            onClick={runDiagnostics}
            style={{
              background: "rgba(245, 158, 11, 0.08)",
              color: "#f59e0b",
              border: "1px solid rgba(245, 158, 11, 0.2)",
              padding: "8px 16px",
              borderRadius: "10px",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
            </svg>
            Run Again
          </button>
        </div>

        {/* Health Score */}
        <div className="health-card">
          <div className="health-icon">
            {healthScore >= 80 ? "✅" : healthScore >= 60 ? "⚠️" : "❌"}
          </div>
          <div className="health-content">
            <div className="health-label">Overall Health Score</div>
            <div
              className="health-score"
              style={{
                color:
                  healthScore >= 80
                    ? "#10b981"
                    : healthScore >= 60
                      ? "#f59e0b"
                      : "#ef4444",
              }}
            >
              {healthScore}%
            </div>
            <div className="health-bar">
              <div
                className="health-progress"
                style={{
                  width: `${healthScore}%`,
                  background:
                    healthScore >= 80
                      ? "#10b981"
                      : healthScore >= 60
                        ? "#f59e0b"
                        : "#ef4444",
                }}
              />
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Total Records</div>
            <div className="stat-value">{totalRecords}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Data Completeness</div>
            <div className="stat-value">{completeness}%</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Recent Activity</div>
            <div className="stat-value">{recentRecords}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Active Facilities</div>
            <div className="stat-value">{totalFacilities}</div>
          </div>
        </div>

        {/* Issues */}
        {issues.length > 0 && (
          <div className="issues-section">
            <h3 className="issues-title error">
              🚨 Critical Issues ({issues.length})
            </h3>
            <div className="issues-list">
              {issues.map((issue, idx) => (
                <div key={idx} className="issue-card error">
                  <div className="issue-header">
                    <span className="issue-title">{issue.title}</span>
                    <span
                      className={`issue-badge ${issue.impact.toLowerCase()}`}
                    >
                      {issue.impact} Impact
                    </span>
                  </div>
                  <p className="issue-description">{issue.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="issues-section">
            <h3 className="issues-title warning">
              ⚠️ Warnings ({warnings.length})
            </h3>
            <div className="issues-list">
              {warnings.map((warning, idx) => (
                <div key={idx} className="issue-card warning">
                  <div className="issue-header">
                    <span className="issue-title">{warning.title}</span>
                    <span
                      className={`issue-badge ${warning.impact.toLowerCase()}`}
                    >
                      {warning.impact} Impact
                    </span>
                  </div>
                  <p className="issue-description">{warning.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div className="issues-section">
            <h3 className="issues-title info">
              💡 Suggestions ({suggestions.length})
            </h3>
            <div className="issues-list">
              {suggestions.map((suggestion, idx) => (
                <div key={idx} className="issue-card info">
                  <div className="issue-header">
                    <span className="issue-title">{suggestion.title}</span>
                    <span
                      className={`issue-badge ${suggestion.impact.toLowerCase()}`}
                    >
                      {suggestion.impact} Impact
                    </span>
                  </div>
                  <p className="issue-description">{suggestion.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* All Clear */}
        {issues.length === 0 &&
          warnings.length === 0 &&
          suggestions.length === 0 && (
            <div className="all-clear">
              <div className="all-clear-icon">✨</div>
              <h3>All Systems Operational</h3>
              <p>Your data quality is excellent. No issues detected.</p>
            </div>
          )}
      </div>
    </div>
  );
};

export default Diagnostics;
