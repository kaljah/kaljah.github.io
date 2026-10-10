import SettingsIPCCGlobalWarming from "./settings/SettingsIPCCGlobalWarming";
import SettingsOGMP20Framework from "./settings/SettingsOGMP20Framework";
import SettingsFacilityLevelOGMPOverrides, { type FacilityItem, type FacilityEdit } from "./settings/SettingsFacilityLevelOGMPOverrides";
import { Badge, Banner, Button, Card, Tabs, TabsContent, TabsList, TabsTrigger } from "../ui";
import React, { useState, useEffect } from "react";
import { Building2, Globe, Save, SlidersHorizontal, Target } from "lucide-react";
import api from "../api";
import { useToast } from "../components/Toast";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";
import { GWP_AR4, GWP_AR5, GWP_AR6 } from "../constants";
import { t } from "../i18n";

const GWP_DATA = {
  AR5: {
    name: t("IPCC 5th Assessment Report (AR5)"),
    year: "2014",
    status: t("UNFCCC / EU Standard (Default)"),
    ch4_100: GWP_AR5.CH4,
    ch4_20: GWP_AR5.CH4_20,
    n2o_100: GWP_AR5.N2O,
    co2: 1.0,
    description:
      t("Standard baseline used by OGMP 2.0, UNFCCC National Inventories, and corporate GHG reporting frameworks."),
  },
  AR6: {
    name: t("IPCC 6th Assessment Report (AR6)"),
    year: "2021",
    status: t("Latest IPCC Physical Science Basis"),
    ch4_100: GWP_AR6.CH4,
    ch4_20: GWP_AR6.CH4_20,
    n2o_100: GWP_AR6.N2O,
    co2: 1.0,
    description:
      t("Most recent scientific consensus. Methane uses the fossil value (29.8 over 100 years, 82.5 over 20), which applies to oil and gas sources."),
  },
  AR4: {
    name: t("IPCC 4th Assessment Report (AR4)"),
    year: "2007",
    status: t("Legacy Regulatory Frameworks"),
    ch4_100: GWP_AR4.CH4,
    ch4_20: GWP_AR4.CH4_20,
    n2o_100: GWP_AR4.N2O,
    co2: 1.0,
    description:
      t("Historical standard preserved for legacy compliance agreements and multi-decade baseline tracking."),
  },
};

const Settings: React.FC = () => {
  const toast = useToast();
  const { user } = useAuth();
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [activeTab, setActiveTab] = useState<string>("gwp");

  // Settings state
  const [gwpStandard, setGwpStandard] = useState<string>("AR5");
  const [defaultBaseYear, setDefaultBaseYear] = useState<number>(2023);
  const [globalThreshold, setGlobalThreshold] = useState<number>(20.0);
  const [upstreamTarget, setUpstreamTarget] = useState<number>(0.2);
  const [midstreamTarget, setMidstreamTarget] = useState<number>(0.05);
  const [unitSystem, setUnitSystem] = useState<string>("metric");
  const [autoFlagDiscrepancy, setAutoFlagDiscrepancy] = useState<boolean>(true);

  // Facility specific overrides
  const [facilityEdits, setFacilityEdits] = useState<Record<string | number, FacilityEdit>>({});

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
          setDefaultBaseYear(Number(settings.ogmp_default_base_year));
        if (settings.reconciliation_threshold)
          setGlobalThreshold(Number(settings.reconciliation_threshold));
        if (settings.ogmp_upstream_target_pct !== undefined)
          setUpstreamTarget(Number(settings.ogmp_upstream_target_pct));
        if (settings.ogmp_midstream_target_pct !== undefined)
          setMidstreamTarget(Number(settings.ogmp_midstream_target_pct));
        // light theme only
        document.documentElement.removeAttribute("data-theme");
        if (settings.unit_system) setUnitSystem(settings.unit_system);
        if (settings.auto_flag_discrepancy !== undefined)
          setAutoFlagDiscrepancy(Boolean(settings.auto_flag_discrepancy));
      }

      const facList: FacilityItem[] = facRes.data;
      if (facList && Array.isArray(facList)) {
        setFacilities(facList);
        const initialMap: Record<string | number, FacilityEdit> = {};
        facList.forEach((f) => {
          initialMap[f.id] = {
            operator_status: f.operator_status || "operated",
            country: f.country || "Algeria",
            ogmp_membership_year: f.ogmp_membership_year || 2023,
            reconciliation_threshold: f.reconciliation_threshold || 20.0,
          };
        });
        setFacilityEdits(initialMap);
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
      toast.error(t("Failed to load settings"));
    } finally {
      setLoading(false);
    }
  };

  // same rule as PUT /api/auth/settings: organisation-wide settings are admin only
  const isAdmin = user?.role === "admin";

  const handleSaveGlobal = async () => {
    if (!isAdmin) {
      toast.error(t("Administrator privileges required to modify system settings."));
      return;
    }
    try {
      setSaving(true);
      const payload: Record<string, any> = {
        gwp_standard: gwpStandard,
        ogmp_default_base_year: Number(defaultBaseYear),
        reconciliation_threshold: Number(globalThreshold),
        ogmp_upstream_target_pct: Number(upstreamTarget),
        ogmp_midstream_target_pct: Number(midstreamTarget),
        theme: "light",
        unit_system: unitSystem,
        auto_flag_discrepancy: autoFlagDiscrepancy,
      };
      await api.post("/auth/settings", payload);
      toast.success(t("System settings saved successfully!"));
    } catch (err: any) {
      console.error("Save failed:", err);
      toast.error(err?.response?.data?.message || err?.response?.data?.error || t("Error saving settings"));
    } finally {
      setSaving(false);
    }
  };

  const handleFacilityChange = (facId: number | string, field: string, value: any) => {
    setFacilityEdits((prev) => ({
      ...prev,
      [facId]: {
        ...prev[facId],
        [field]: value,
      },
    }));
  };

  const handleSaveFacility = async (facId: number | string) => {
    if (user?.role === "it_admin" || (user?.role !== "admin" && user?.role !== "superuser")) {
      toast.error(t("Administrator privileges required to update facility settings."));
      return;
    }
    try {
      const fac = facilities.find((f) => f.id === facId);
      const data = { ...(fac || {}), ...(facilityEdits[facId] || {}) };
      await api.put(`/facilities/${facId}`, {
        operator_status: data.operator_status,
        country: data.country,
        ogmp_membership_year: Number(data.ogmp_membership_year || 2021),
        reconciliation_threshold: Number(data.reconciliation_threshold || 20),
      });
      toast.success(t("Facility OGMP settings updated!"));
    } catch (err: any) {
      console.error("Facility save failed:", err);
      toast.error(err?.response?.data?.message || err?.response?.data?.error || t("Failed to update facility"));
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner message={t("Loading Standards & System Preferences...")} />
      </div>
    );
  }

  const TABS = [
    { value: "gwp", icon: Globe, label: t("IPCC GWP Standards") },
    { value: "ogmp", icon: Target, label: t("OGMP 2.0 Baseline & Thresholds") },
    { value: "facilities", icon: Building2, label: t("Facility Overrides ({{count}})", { count: facilities.length }) },
  ];

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="mx-auto w-full max-w-[1600px] gap-6 p-4 sm:p-8">
      <Card className="flex flex-col gap-5 border-t-4 border-t-brand-500 px-8 pb-0 pt-7">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex max-w-[850px] flex-col gap-1.5">
            <Badge tone="brand" className="mb-0.5 w-fit gap-1.5 px-3 py-1 uppercase tracking-wide">
              <SlidersHorizontal className="size-3.5" aria-hidden="true" />{" "}{t("Standards & Methodologies")}
            </Badge>
            <h1 className="m-0 text-xl font-bold text-text">{t("System Settings & Protocols")}</h1>
            <p className="m-0 text-md leading-normal text-text-secondary">
              {t("Configure IPCC Global Warming Potential (GWP) conversion factors, OGMP 2.0 Gold Standard compliance parameters, and facility-specific reconciliation tolerances.")}
            </p>
          </div>
          {/* only an admin can change these settings: other roles see them read-only, with no save button */}
          {isAdmin && (
            <Button onClick={handleSaveGlobal} loading={saving} disabled={saving} title={t("Save changes")} id="save-settings-btn">
              <Save className="size-4" aria-hidden="true" />
              {saving ? t("Saving...") : t("Save All Changes")}
            </Button>
          )}
        </div>

        <TabsList aria-label={t("Settings sections")} className="border-b-0">
          {TABS.map(({ value, icon: Icon, label }) => (
            <TabsTrigger key={value} value={value}>
              <Icon className="size-[17px] shrink-0" aria-hidden="true" /> {label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Card>

      {!isAdmin && (
        <Banner tone="info" title={t("Read-only mode")}>
          {t("System methodologies (IPCC GWP standards and OGMP reconciliation parameters) are centrally managed. Updates require an Administrator account.")}
        </Banner>
      )}

      <TabsContent value="gwp" className="pt-0">
        <SettingsIPCCGlobalWarming GWP_DATA={GWP_DATA} gwpStandard={gwpStandard} isAdmin={isAdmin} setGwpStandard={setGwpStandard} />
      </TabsContent>

      <TabsContent value="ogmp" className="pt-0">
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
      </TabsContent>

      <TabsContent value="facilities" className="pt-0">
        <SettingsFacilityLevelOGMPOverrides
          facilities={facilities}
          facilityEdits={facilityEdits}
          handleFacilityChange={handleFacilityChange}
          handleSaveFacility={handleSaveFacility}
          isAdmin={isAdmin}
          user={user}
        />
      </TabsContent>

    </Tabs>
  );
};

export default Settings;
