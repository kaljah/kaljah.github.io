import SettingsIPCCGlobalWarming from "./settings/SettingsIPCCGlobalWarming";
import SettingsOGMP20Framework from "./settings/SettingsOGMP20Framework";
import SettingsFacilityLevelOGMPOverrides, { type FacilityItem, type FacilityEdit } from "./settings/SettingsFacilityLevelOGMPOverrides";
import { Badge, Banner, Button, Card, Tabs, TabsContent, TabsList, TabsTrigger } from "../ui";
import React, { useState, useEffect, useRef, useMemo } from "react";
import { AlertTriangle, Building2, Globe, Save, SlidersHorizontal, Target } from "lucide-react";
import api from "../api";
import { useToast } from "../components/Toast";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";
import Modal from "../components/Modal";
import { GWP_AR4, GWP_AR5, GWP_AR6 } from "../constants";
import { GovernanceNavTabs } from "../components/NavigationTabs";
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
  const [savingFacilities, setSavingFacilities] = useState<boolean>(false);
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

  // Pending GWP change awaiting confirmation
  const [pendingGwp, setPendingGwp] = useState<string | null>(null);

  // Facility specific overrides
  const [facilityEdits, setFacilityEdits] = useState<Record<string | number, FacilityEdit>>({});

  // Baseline snapshots for dirty state tracking
  const initialGlobalRef = useRef({
    gwpStandard: "AR5",
    defaultBaseYear: 2023,
    globalThreshold: 20.0,
    upstreamTarget: 0.2,
    midstreamTarget: 0.05,
    unitSystem: "metric",
    autoFlagDiscrepancy: true,
  });
  const initialFacilityMapRef = useRef<Record<string | number, FacilityEdit>>({});

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
        const std = settings.gwp_standard || "AR5";
        const yr = settings.ogmp_default_base_year ? Number(settings.ogmp_default_base_year) : 2023;
        const thresh = settings.reconciliation_threshold ? Number(settings.reconciliation_threshold) : 20.0;
        const up = settings.ogmp_upstream_target_pct !== undefined ? Number(settings.ogmp_upstream_target_pct) : 0.2;
        const mid = settings.ogmp_midstream_target_pct !== undefined ? Number(settings.ogmp_midstream_target_pct) : 0.05;
        const us = settings.unit_system || "metric";
        const af = settings.auto_flag_discrepancy !== undefined ? Boolean(settings.auto_flag_discrepancy) : true;

        setGwpStandard(std);
        setDefaultBaseYear(yr);
        setGlobalThreshold(thresh);
        setUpstreamTarget(up);
        setMidstreamTarget(mid);
        setUnitSystem(us);
        setAutoFlagDiscrepancy(af);

        initialGlobalRef.current = {
          gwpStandard: std,
          defaultBaseYear: yr,
          globalThreshold: thresh,
          upstreamTarget: up,
          midstreamTarget: mid,
          unitSystem: us,
          autoFlagDiscrepancy: af,
        };

        // light theme only
        document.documentElement.removeAttribute("data-theme");
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
        initialFacilityMapRef.current = JSON.parse(JSON.stringify(initialMap));
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

  const isGlobalDirty = useMemo(() => {
    const init = initialGlobalRef.current;
    return (
      gwpStandard !== init.gwpStandard ||
      Number(defaultBaseYear) !== Number(init.defaultBaseYear) ||
      Number(globalThreshold) !== Number(init.globalThreshold) ||
      Number(upstreamTarget) !== Number(init.upstreamTarget) ||
      Number(midstreamTarget) !== Number(init.midstreamTarget) ||
      unitSystem !== init.unitSystem ||
      autoFlagDiscrepancy !== init.autoFlagDiscrepancy
    );
  }, [gwpStandard, defaultBaseYear, globalThreshold, upstreamTarget, midstreamTarget, unitSystem, autoFlagDiscrepancy]);

  const dirtyFacilityIds = useMemo(() => {
    const dirty = new Set<string | number>();
    for (const fac of facilities) {
      const init = initialFacilityMapRef.current[fac.id] || {};
      const curr = facilityEdits[fac.id] || {};
      if (
        (curr.operator_status || "operated") !== (init.operator_status || "operated") ||
        (curr.country || "Algeria") !== (init.country || "Algeria") ||
        Number(curr.ogmp_membership_year || 2023) !== Number(init.ogmp_membership_year || 2023) ||
        Number(curr.reconciliation_threshold || 20) !== Number(init.reconciliation_threshold || 20)
      ) {
        dirty.add(fac.id);
      }
    }
    return dirty;
  }, [facilities, facilityEdits]);

  // Unsaved changes browser guard
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isGlobalDirty || dirtyFacilityIds.size > 0) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isGlobalDirty, dirtyFacilityIds.size]);

  const handleSaveGlobal = async (overrides?: Record<string, any>) => {
    if (!isAdmin) {
      toast.error(t("Administrator privileges required to modify system settings."));
      return;
    }
    try {
      setSaving(true);
      const standard = overrides?.gwp_standard || gwpStandard;
      const yr = overrides?.ogmp_default_base_year !== undefined ? overrides.ogmp_default_base_year : defaultBaseYear;
      const thresh = overrides?.reconciliation_threshold !== undefined ? overrides.reconciliation_threshold : globalThreshold;
      const up = overrides?.ogmp_upstream_target_pct !== undefined ? overrides.ogmp_upstream_target_pct : upstreamTarget;
      const mid = overrides?.ogmp_midstream_target_pct !== undefined ? overrides.ogmp_midstream_target_pct : midstreamTarget;

      const payload: Record<string, any> = {
        gwp_standard: standard,
        ogmp_default_base_year: Number(yr),
        reconciliation_threshold: Number(thresh),
        ogmp_upstream_target_pct: Number(up),
        ogmp_midstream_target_pct: Number(mid),
        theme: "light",
        unit_system: unitSystem,
        auto_flag_discrepancy: autoFlagDiscrepancy,
        ...overrides,
      };
      await api.post("/auth/settings", payload);
      initialGlobalRef.current = {
        gwpStandard: standard,
        defaultBaseYear: Number(yr),
        globalThreshold: Number(thresh),
        upstreamTarget: Number(up),
        midstreamTarget: Number(mid),
        unitSystem,
        autoFlagDiscrepancy,
      };
      toast.success(t("System settings saved successfully!"));
    } catch (err: any) {
      console.error("Save failed:", err);
      toast.error(err?.response?.data?.message || err?.response?.data?.error || t("Error saving settings"));
    } finally {
      setSaving(false);
    }
  };

  const handleRequestChangeGwp = (newStandard: string) => {
    if (newStandard === gwpStandard) return;
    setPendingGwp(newStandard);
  };

  const handleConfirmGwpChange = async () => {
    if (!pendingGwp) return;
    const target = pendingGwp;
    setPendingGwp(null);
    setGwpStandard(target);
    await handleSaveGlobal({ gwp_standard: target });
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
      initialFacilityMapRef.current[facId] = { ...facilityEdits[facId] };
      toast.success(t("Facility OGMP settings updated!"));
    } catch (err: any) {
      console.error("Facility save failed:", err);
      toast.error(err?.response?.data?.message || err?.response?.data?.error || t("Failed to update facility"));
    }
  };

  const handleSaveAllDirtyFacilities = async () => {
    if (user?.role === "it_admin" || (user?.role !== "admin" && user?.role !== "superuser")) {
      toast.error(t("Administrator privileges required to update facility settings."));
      return;
    }
    const idsToSave = Array.from(dirtyFacilityIds);
    if (idsToSave.length === 0) return;
    try {
      setSavingFacilities(true);
      await Promise.all(
        idsToSave.map(async (facId) => {
          const fac = facilities.find((f) => f.id === facId);
          const data = { ...(fac || {}), ...(facilityEdits[facId] || {}) };
          return api.put(`/facilities/${facId}`, {
            operator_status: data.operator_status,
            country: data.country,
            ogmp_membership_year: Number(data.ogmp_membership_year || 2021),
            reconciliation_threshold: Number(data.reconciliation_threshold || 20),
          });
        })
      );
      idsToSave.forEach((id) => {
        initialFacilityMapRef.current[id] = { ...facilityEdits[id] };
      });
      toast.success(t("All {{count}} modified facilities updated successfully!", { count: idsToSave.length }));
    } catch (err: any) {
      console.error("Batch facility save failed:", err);
      toast.error(t("Failed to update some facilities"));
    } finally {
      setSavingFacilities(false);
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
    <div className="mx-auto w-full max-w-[1600px] p-4 sm:p-8 flex flex-col gap-6">
      <GovernanceNavTabs />
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full gap-6">
        <Card className="flex flex-col gap-5 border-t-4 border-t-brand-500 px-8 pb-0 pt-7">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex max-w-[850px] flex-col gap-1.5">
            <Badge tone="brand" className="mb-0.5 w-fit gap-1.5 px-2.5 py-0.5 font-medium">
              <SlidersHorizontal className="size-3.5" aria-hidden="true" />{" "}{t("Standards & Methodologies")}
            </Badge>
            <h1 className="m-0 text-xl font-bold text-text">{t("System Settings & Protocols")}</h1>
            <p className="m-0 text-md leading-normal text-text-secondary">
              {t("Configure IPCC Global Warming Potential (GWP) conversion factors, OGMP 2.0 Gold Standard compliance parameters, and facility-specific reconciliation tolerances.")}
            </p>
          </div>
          {/* only an admin can change these settings: other roles see them read-only, with no save button */}
          {isAdmin && (
            <div className="flex flex-wrap items-center gap-2.5">
              {isGlobalDirty && (
                <Badge tone="warning" className="gap-1.5 py-1 px-2.5 font-medium">
                  <span className="size-2 rounded-full bg-amber-500 animate-pulse" />
                  {t("Unsaved System Settings")}
                </Badge>
              )}
              {dirtyFacilityIds.size > 0 && activeTab === "facilities" && (
                <Badge tone="warning" className="gap-1.5 py-1 px-2.5 font-medium">
                  <span className="size-2 rounded-full bg-amber-500 animate-pulse" />
                  {t("{{count}} Unsaved Facilities", { count: dirtyFacilityIds.size })}
                </Badge>
              )}
              <Button
                onClick={() => handleSaveGlobal()}
                loading={saving}
                disabled={saving || !isGlobalDirty}
                variant={isGlobalDirty ? "primary" : "secondary"}
                title={isGlobalDirty ? t("Save modified system settings") : t("No unsaved system settings")}
                id="save-settings-btn"
                className="gap-2"
              >
                <Save className="size-4" aria-hidden="true" />
                {saving ? t("Saving...") : t("Save System Settings")}
              </Button>
            </div>
          )}
        </div>

        {/* Active Policy Status Strip */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-xl border border-border bg-ink-50/60 p-3.5">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-text-secondary">
              {t("Active GWP Standard")}
            </span>
            <span className="text-sm font-bold text-text mt-0.5">
              IPCC {gwpStandard} (100-yr)
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-text-secondary">
              {t("Default Base Year")}
            </span>
            <span className="text-sm font-bold text-text mt-0.5">
              {defaultBaseYear}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-text-secondary">
              {t("Methane Intensity Target")}
            </span>
            <span className="text-sm font-bold text-text mt-0.5">
              {upstreamTarget}% {t("(Upstream)")}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-text-secondary">
              {t("Reconciliation Tolerance")}
            </span>
            <span className="text-sm font-bold text-text mt-0.5">
              ±{globalThreshold}%
            </span>
          </div>
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
        <SettingsIPCCGlobalWarming
          GWP_DATA={GWP_DATA}
          gwpStandard={gwpStandard}
          isAdmin={isAdmin}
          setGwpStandard={setGwpStandard}
          onRequestChangeStandard={handleRequestChangeGwp}
        />
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
          dirtyFacilityIds={dirtyFacilityIds}
          handleSaveAllDirtyFacilities={handleSaveAllDirtyFacilities}
          savingFacilities={savingFacilities}
          isAdmin={isAdmin}
          user={user}
        />
      </TabsContent>

    </Tabs>

      {pendingGwp && (
        <Modal
          title={t("Confirm GWP Standard Recalculation")}
          onClose={() => setPendingGwp(null)}
          maxWidth="560px"
        >
          <div className="flex flex-col gap-4 p-4">
            <div className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-3.5 text-sm text-amber-900 shadow-xs">
              <AlertTriangle className="size-5 shrink-0 text-amber-600 mt-0.5" />
              <div className="flex flex-col gap-1.5">
                <p className="m-0 font-semibold">
                  {t("Recalculate All GHG Outputs (IPCC {{prev}} → {{next}})", { prev: gwpStandard, next: pendingGwp })}
                </p>
                <p className="m-0 text-xs text-amber-800 leading-relaxed">
                  {t("Switching the active GWP standard will recalculate stored CO₂e emissions across all historical and current Scope 1, Scope 2, and Scope 3 records. An immutable entry will be recorded in the system audit trail.")}
                </p>
              </div>
            </div>
            <p className="text-sm text-text-secondary">
              {t("Are you sure you want to change the corporate calculation methodology from IPCC {{prev}} to IPCC {{next}}?", { prev: gwpStandard, next: pendingGwp })}
            </p>
            <div className="flex justify-end gap-2.5 pt-3 border-t border-border">
              <Button variant="secondary" onClick={() => setPendingGwp(null)}>
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleConfirmGwpChange} loading={saving}>
                {t("Confirm & Recalculate")}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default Settings;
