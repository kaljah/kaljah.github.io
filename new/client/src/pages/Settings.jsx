import SettingsIPCCGlobalWarming from "./settings/SettingsIPCCGlobalWarming";
import SettingsOGMP20Framework from "./settings/SettingsOGMP20Framework";
import SettingsFacilityLevelOGMPOverrides from "./settings/SettingsFacilityLevelOGMPOverrides";
import SettingsESACopernicusSentinel5P from "./settings/SettingsESACopernicusSentinel5P";
import { Banner } from "../ui";
import { NativeSelect } from "../ui/NativeSelect";
import React, { useState, useEffect } from "react";
import {
  Globe,
  Target,
  Building2,
  SlidersHorizontal,
  Save,
  CheckCircle2,
  Scale,
  ShieldCheck,
  Activity,
  Layers,
  Radio,
  Satellite,
  ExternalLink,
  KeyRound,
  AlertCircle,
  Check,
  HelpCircle } from "lucide-react";
import api from "../api";
import { useToast } from "../components/Toast";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";
import "./Settings.css";
import { GWP_AR4, GWP_AR5, GWP_AR6 } from "../constants";

const GWP_DATA = {
  AR5: {
    name: "IPCC 5th Assessment Report (AR5)",
    year: "2014",
    status: "UNFCCC / EU Standard (Default)",
    ch4_100: GWP_AR5.CH4,
    ch4_20: GWP_AR5.CH4_20,
    n2o_100: GWP_AR5.N2O,
    co2: 1.0,
    description:
      "Standard baseline used by OGMP 2.0, UNFCCC National Inventories, and corporate GHG reporting frameworks." },
  AR6: {
    name: "IPCC 6th Assessment Report (AR6)",
    year: "2021",
    status: "Latest IPCC Physical Science Basis",
    ch4_100: GWP_AR6.CH4,
    ch4_20: GWP_AR6.CH4_20,
    n2o_100: GWP_AR6.N2O,
    co2: 1.0,
    description:
      "Most recent scientific consensus incorporating updated radiative efficiency and tropospheric adjustments." },
  AR4: {
    name: "IPCC 4th Assessment Report (AR4)",
    year: "2007",
    status: "Legacy Regulatory Frameworks",
    ch4_100: GWP_AR4.CH4,
    ch4_20: GWP_AR4.CH4_20,
    n2o_100: GWP_AR4.N2O,
    co2: 1.0,
    description:
      "Historical standard preserved for legacy compliance agreements and multi-decade baseline tracking." } };

const Settings = () => {
  const toast = useToast();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [facilities, setFacilities] = useState([]);
  const [activeTab, setActiveTab] = useState("gwp");

  // Settings state
  const [gwpStandard, setGwpStandard] = useState("AR5");
  const [defaultBaseYear, setDefaultBaseYear] = useState(2023);
  const [globalThreshold, setGlobalThreshold] = useState(20.0);
  const [upstreamTarget, setUpstreamTarget] = useState(0.2);
  const [midstreamTarget, setMidstreamTarget] = useState(0.05);
  const [unitSystem, setUnitSystem] = useState("metric");
  const [autoFlagDiscrepancy, setAutoFlagDiscrepancy] = useState(true);

  // Copernicus Sentinel-5P Satellite Integration States
  const [copernicusUsername, setCopernicusUsername] = useState("");
  const [copernicusPassword, setCopernicusPassword] = useState("");
  const [copernicusClientId, setCopernicusClientId] = useState("");
  const [copernicusClientSecret, setCopernicusClientSecret] = useState("");
  const [copernicusQaThreshold, setCopernicusQaThreshold] = useState(0.5);
  const [copernicusEnabled, setCopernicusEnabled] = useState(false);
  const [authMode, setAuthMode] = useState("password"); // 'password' or 'oauth_client'
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null); // { success: bool, message: str, expires_in?: int }
  const [showGuide, setShowGuide] = useState(false);

  // Facility specific overrides
  const [facilityEdits, setFacilityEdits] = useState({});

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [settingsRes, facRes] = await Promise.all([
        api.get("/auth/settings").catch(() => ({ data: {} })),
        api.get("/facilities").catch(() => ({ data: [] })),
      ]);

      const settings = settingsRes.data;
      if (settings) {
        if (settings.gwp_standard) setGwpStandard(settings.gwp_standard);
        if (settings.ogmp_default_base_year)
          setDefaultBaseYear(settings.ogmp_default_base_year);
        if (settings.reconciliation_threshold)
          setGlobalThreshold(settings.reconciliation_threshold);
        if (settings.ogmp_upstream_target_pct !== undefined)
          setUpstreamTarget(Number(settings.ogmp_upstream_target_pct));
        if (settings.ogmp_midstream_target_pct !== undefined)
          setMidstreamTarget(Number(settings.ogmp_midstream_target_pct));
        if (settings.copernicus_username)
          setCopernicusUsername(settings.copernicus_username);
        if (settings.copernicus_password)
          setCopernicusPassword(settings.copernicus_password);
        if (settings.copernicus_client_id) {
          setCopernicusClientId(settings.copernicus_client_id);
          setAuthMode("oauth_client");
        }
        if (settings.copernicus_client_secret)
          setCopernicusClientSecret(settings.copernicus_client_secret);
        if (settings.copernicus_qa_threshold !== undefined)
          setCopernicusQaThreshold(Number(settings.copernicus_qa_threshold));
        if (settings.copernicus_enabled !== undefined)
          setCopernicusEnabled(Boolean(settings.copernicus_enabled));
        // light theme only
        document.documentElement.removeAttribute("data-theme");
        if (settings.unit_system) setUnitSystem(settings.unit_system);
        if (settings.auto_flag_discrepancy !== undefined)
          setAutoFlagDiscrepancy(settings.auto_flag_discrepancy);
      }

      const facList = facRes.data;
      if (facList && Array.isArray(facList)) {
        setFacilities(facList);
        const initialMap = {};
        facList.forEach((f) => {
          initialMap[f.id] = {
            operator_status: f.operator_status || "operated",
            country: f.country || "Algeria",
            ogmp_membership_year: f.ogmp_membership_year || 2023,
            reconciliation_threshold: f.reconciliation_threshold || 20.0 };
        });
        setFacilityEdits(initialMap);
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
      toast.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  };


  const isAdmin =
    user?.role === "admin" ||
    user?.role === "superuser" ||
    user?.role === "it_admin";

  const handleSaveGlobal = async () => {
    if (!isAdmin) {
      toast.error("Administrator privileges required to modify system settings.");
      return;
    }
    try {
      setSaving(true);
      const payload = {
        gwp_standard: gwpStandard,
        ogmp_default_base_year: Number(defaultBaseYear),
        reconciliation_threshold: Number(globalThreshold),
        ogmp_upstream_target_pct: Number(upstreamTarget),
        ogmp_midstream_target_pct: Number(midstreamTarget),
        copernicus_username: copernicusUsername,
        copernicus_client_id: copernicusClientId,
        copernicus_qa_threshold: Number(copernicusQaThreshold),
        copernicus_enabled: Boolean(copernicusEnabled),
        theme: "light",
        unit_system: unitSystem,
        auto_flag_discrepancy: autoFlagDiscrepancy };
      if (copernicusPassword && copernicusPassword !== "********") {
        payload.copernicus_password = copernicusPassword;
      }
      if (copernicusClientSecret && copernicusClientSecret !== "********") {
        payload.copernicus_client_secret = copernicusClientSecret;
      }
      await api.post("/auth/settings", payload);
      toast.success(
        "System settings and Copernicus credentials saved successfully!",
      );
    } catch (err) {
      console.error("Save failed:", err);
      toast.error(err?.response?.data?.message || err?.response?.data?.error || "Error saving settings");
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      setTestingConnection(true);
      setConnectionStatus(null);
      const payload =
        authMode === "password"
          ? {
              copernicus_username: copernicusUsername,
              ...(copernicusPassword && copernicusPassword !== "********"
                ? { copernicus_password: copernicusPassword }
                : {}) }
          : {
              copernicus_client_id: copernicusClientId,
              ...(copernicusClientSecret && copernicusClientSecret !== "********"
                ? { copernicus_client_secret: copernicusClientSecret }
                : {}) };

      const res = await api.post(
        "/satellite/sentinel5p/test-connection",
        payload,
      );
      if (res.data && res.data.connected) {
        setConnectionStatus({
          success: true,
          message: res.data.message,
          expires_in: res.data.expires_in });
        toast.success(
          "Copernicus Data Space connection verified successfully!",
        );
      } else {
        setConnectionStatus({
          success: false,
          message: res.data.message || "Connection failed" });
        toast.error(
          res.data.message || "Authentication rejected by Copernicus CDSE",
        );
      }
    } catch (err) {
      const msg =
        err.response?.data?.message ||
        err.message ||
        "Failed to connect to Copernicus CDSE";
      setConnectionStatus({ success: false, message: msg });
      toast.error(msg);
    } finally {
      setTestingConnection(false);
    }
  };

  const handleFacilityChange = (facId, field, value) => {
    setFacilityEdits((prev) => ({
      ...prev,
      [facId]: {
        ...prev[facId],
        [field]: value } }));
  };

  const handleSaveFacility = async (facId) => {
    if (user?.role === "it_admin" || (user?.role !== "admin" && user?.role !== "superuser")) {
      toast.error("Administrator privileges required to update facility settings.");
      return;
    }
    try {
      const fac = facilities.find((f) => f.id === facId);
      const data = { ...(fac || {}), ...(facilityEdits[facId] || {}) };
      await api.put(`/facilities/${facId}`, {
        operator_status: data.operator_status,
        country: data.country,
        ogmp_membership_year: Number(data.ogmp_membership_year || 2021),
        reconciliation_threshold: Number(data.reconciliation_threshold || 20) });
      toast.success("Facility OGMP settings updated!");
    } catch (err) {
      console.error("Facility save failed:", err);
      toast.error(err?.response?.data?.message || err?.response?.data?.error || "Failed to update facility");
    }
  };

  if (loading) {
    return (
      <div className="[display:flex] [justify-content:center] [align-items:center] [min-height:60vh]">
        <LoadingSpinner message="Loading Standards & System Preferences..." />
      </div>
    );
  }


  return (
    <div className="[padding:32px] [max-width:1600px] [margin:0_auto] [display:flex] [flex-direction:column] [gap:24px] [animation:settingsFadeIn_0.35s_ease-out] [font-family:inherit] [color:var(--text-primary,_var(--color-ink-900))]">
      {/* Header */}
      <div className="settings-hero-card">
        <div className="[display:flex] [justify-content:space-between] [align-items:flex-start] [gap:24px] [flex-wrap:wrap]">
          <div className="[display:flex] [flex-direction:column] [gap:6px] [max-width:850px]">
            <div className="settings-badge">
              <SlidersHorizontal size={14} />
              <span>STANDARDS & METHODOLOGIES</span>
            </div>
            <h1 className="[font-size:var(--text-xl)] [font-weight:700] [color:var(--text-primary,_var(--color-ink-900))] [margin:0] [letter-spacing:-0.02em]">System Settings & Protocols</h1>
            <p className="[font-size:var(--text-md)] [color:var(--text-secondary,_var(--color-ink-500))] [margin:0] [line-height:1.5]">
              Configure IPCC Global Warming Potential (GWP) conversion factors,
              OGMP 2.0 Gold Standard compliance parameters, and
              facility-specific reconciliation tolerances.
            </p>
          </div>
          <div className="[display:flex] [align-items:center] [gap:12px]">
            <button
              className="btn-save-primary"
              onClick={handleSaveGlobal}
              disabled={saving || !isAdmin}
              title={!isAdmin ? "Administrator privileges required to modify settings" : "Save changes"}
              id="save-settings-btn"
            >
              {saving ? (
                <>
                  <span className="spinner-small"></span>
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save size={16} />
                  <span>Save All Changes</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="[display:flex] [gap:8px] [border-top:1px_solid_var(--border-color,_var(--color-ink-200))] [padding-top:4px] [overflow-x:auto]" role="tablist" aria-label="Settings sections">
          <button
            role="tab"
            aria-selected={activeTab === "gwp"}
            className={`settings-tab-btn ${activeTab === "gwp" ? "active" : ""}`}
            onClick={() => setActiveTab("gwp")}
            id="tab-gwp"
          >
            <Globe size={17} className="[flex-shrink:0]" />
            <span>IPCC GWP Standards</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "ogmp"}
            className={`settings-tab-btn ${activeTab === "ogmp" ? "active" : ""}`}
            onClick={() => setActiveTab("ogmp")}
            id="tab-ogmp"
          >
            <Target size={17} className="[flex-shrink:0]" />
            <span>OGMP 2.0 Baseline & Thresholds</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "facilities"}
            className={`settings-tab-btn ${activeTab === "facilities" ? "active" : ""}`}
            onClick={() => setActiveTab("facilities")}
            id="tab-facilities"
          >
            <Building2 size={17} className="[flex-shrink:0]" />
            <span>Facility Overrides ({facilities.length})</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "satellite"}
            className={`settings-tab-btn ${activeTab === "satellite" ? "active" : ""}`}
            onClick={() => setActiveTab("satellite")}
            id="tab-satellite"
          >
            <Satellite size={17} className="[flex-shrink:0]" />
            <span>Copernicus Satellite (S5P)</span>
          </button>
        </div>
      </div>

      {!isAdmin && (
        <Banner tone="info" title="Read-only mode" className="mb-5">
          System methodologies (IPCC GWP standards, OGMP reconciliation parameters, and Copernicus satellite
          credentials) are centrally managed. Updates require an Administrator account.
        </Banner>
      )}

      {/* TAB CONTENT: GWP Standards */}
      {activeTab === "gwp" && (
        <SettingsIPCCGlobalWarming
        GWP_DATA={GWP_DATA}
        gwpStandard={gwpStandard}
        isAdmin={isAdmin}
        setGwpStandard={setGwpStandard}
      />
      )}

      {/* TAB CONTENT: OGMP 2.0 Baseline & Thresholds */}
      {activeTab === "ogmp" && (
        <SettingsOGMP20Framework
        defaultBaseYear={defaultBaseYear}
        globalThreshold={globalThreshold}
        handleSaveGlobal={handleSaveGlobal}
        isAdmin={isAdmin}
        midstreamTarget={midstreamTarget}
        saving={saving}
        setDefaultBaseYear={setDefaultBaseYear}
        setGlobalThreshold={setGlobalThreshold}
        setMidstreamTarget={setMidstreamTarget}
        setUpstreamTarget={setUpstreamTarget}
        upstreamTarget={upstreamTarget}
      />
      )}

      {/* TAB CONTENT: Facility-Level Overrides */}
      {activeTab === "facilities" && (
        <SettingsFacilityLevelOGMPOverrides
        facilities={facilities}
        facilityEdits={facilityEdits}
        handleFacilityChange={handleFacilityChange}
        handleSaveFacility={handleSaveFacility}
        isAdmin={isAdmin}
        user={user}
      />
      )}

      {/* TAB CONTENT: Copernicus Sentinel-5P Satellite Integration */}
      {activeTab === "satellite" && (
        <SettingsESACopernicusSentinel5P
        authMode={authMode}
        connectionStatus={connectionStatus}
        copernicusClientId={copernicusClientId}
        copernicusClientSecret={copernicusClientSecret}
        copernicusEnabled={copernicusEnabled}
        copernicusPassword={copernicusPassword}
        copernicusQaThreshold={copernicusQaThreshold}
        copernicusUsername={copernicusUsername}
        handleSaveGlobal={handleSaveGlobal}
        handleTestConnection={handleTestConnection}
        isAdmin={isAdmin}
        saving={saving}
        setAuthMode={setAuthMode}
        setCopernicusClientId={setCopernicusClientId}
        setCopernicusClientSecret={setCopernicusClientSecret}
        setCopernicusEnabled={setCopernicusEnabled}
        setCopernicusPassword={setCopernicusPassword}
        setCopernicusQaThreshold={setCopernicusQaThreshold}
        setCopernicusUsername={setCopernicusUsername}
        setShowGuide={setShowGuide}
        showGuide={showGuide}
        testingConnection={testingConnection}
      />
      )}
    </div>
  );
};

export default Settings;
