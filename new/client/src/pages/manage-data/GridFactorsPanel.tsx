import React, { useEffect, useState } from "react";
import { Archive, Check, Plus } from "lucide-react";
import api from "../../api";
import { Badge, Button, Field, Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { useToast } from "../../components/Toast";
import { apiError } from "../../utils/apiError";
import { t } from "../../i18n";

// Dated, cited grid-average electricity factors for the location-based Scope 2 method (GHG Protocol Scope 2 Guidance
// Table 6.2). A superuser or administrator adds one; it is used once someone else approves it (an administrator may
// approve their own). Records use the vintage of their reporting year (GB RY2022 GB-003 / GB-021, D3 / D4).

interface GridFactorRow {
  id: number;
  name: string;
  country: string | null;
  level: string;
  year: number;
  co2: number;
  ch4: number | null;
  n2o: number | null;
  source: string;
  status: string;
  created_by: number | null;
}

const BLANK = { name: "", country: "", level: "national", year: "", co2: "", ch4: "", n2o: "", source: "" };

export const GridFactorsPanel: React.FC<{ user: any }> = ({ user }) => {
  const toast = useToast();
  const [rows, setRows] = useState<GridFactorRow[]>([]);
  const [form, setForm] = useState(BLANK);
  const [busy, setBusy] = useState(false);
  const canEdit = ["admin", "superuser"].includes(user?.role || "");

  const load = () =>
    api.get("/grid-factors").then((r) => setRows(r.data || [])).catch((err) => toast.show(apiError(err), "error"));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const num = (v: string) => (v.trim() === "" ? null : parseFloat(v));

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/grid-factors", {
        name: form.name, country: form.country || null, level: form.level, year: parseInt(form.year, 10),
        co2: num(form.co2), ch4: num(form.ch4), n2o: num(form.n2o), source: form.source,
      });
      toast.show(t("Grid factor added: it is used once approved"), "success");
      setForm(BLANK);
      load();
    } catch (err) {
      toast.show(apiError(err), "error");
    } finally {
      setBusy(false);
    }
  };

  const act = async (row: GridFactorRow, action: "approve" | "archive") => {
    try {
      await api.post(`/grid-factors/${row.id}/${action}`);
      toast.show(action === "approve" ? t("Grid factor approved") : t("Grid factor archived"), "success");
      load();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  const mayApprove = (r: GridFactorRow) => r.status === "Pending" && canEdit && (r.created_by !== user?.id || user?.role === "admin");

  return (
    <div className="mt-6 space-y-3" data-testid="grid-factors-panel">
      <h3 className="text-sm font-semibold text-text">{t("Grid electricity factors (location-based Scope 2)")}</h3>
      <p className="text-xs text-text-secondary">
        {t("Grid averages in kg per kWh, with the year they describe and their source. A record uses the most recent year at or before its reporting year.")}
      </p>
      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-start text-sm border-collapse">
            <thead>
              <tr className="border-b border-border text-xs text-text-secondary">
                <th className="py-2">{t("Grid")}</th>
                <th className="py-2">{t("Country")}</th>
                <th className="py-2">{t("Year")}</th>
                <th className="py-2">CO₂</th>
                <th className="py-2">CH₄</th>
                <th className="py-2">N₂O</th>
                <th className="py-2">{t("Source")}</th>
                <th className="py-2">{t("Status")}</th>
                {canEdit && <th className="py-2 text-end">{t("Action")}</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-border/50">
                  <td className="py-1.5 font-medium">{r.name}<span className="ms-1 text-xs text-text-secondary">({t(r.level)})</span></td>
                  <td className="py-1.5 text-xs">{r.country || "-"}</td>
                  <td className="py-1.5 font-mono text-xs">{r.year}</td>
                  <td className="py-1.5 font-mono text-xs">{r.co2}</td>
                  <td className="py-1.5 font-mono text-xs">{r.ch4 ?? "-"}</td>
                  <td className="py-1.5 font-mono text-xs">{r.n2o ?? "-"}</td>
                  <td className="py-1.5 text-xs text-text-secondary">{r.source}</td>
                  <td className="py-1.5"><Badge>{t(r.status)}</Badge></td>
                  {canEdit && (
                    <td className="py-1.5 text-end whitespace-nowrap">
                      {mayApprove(r) && (
                        <Button variant="secondary" size="sm" onClick={() => act(r, "approve")}
                          aria-label={t("Approve {{name}} {{year}}", { name: r.name, year: r.year })}>
                          <Check className="size-3 me-1" aria-hidden="true" />{t("Approve")}
                        </Button>
                      )}
                      <Button variant="secondary" size="sm" className="ms-1" onClick={() => act(r, "archive")}
                        aria-label={t("Archive {{name}} {{year}}", { name: r.name, year: r.year })} title={t("Archive")}>
                        <Archive className="size-3" aria-hidden="true" />
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {canEdit && (
        <form onSubmit={save} className="grid grid-cols-2 sm:grid-cols-4 gap-2 items-end">
          <Field label={t("Grid name")}><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder={t("e.g. Algeria (IEA)")} required /></Field>
          <Field label={t("Country")}><Input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} placeholder={t("e.g. Algeria")} /></Field>
          <Field label={t("Level")}>
            <NativeSelect value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value })}>
              <option value="national">{t("national")}</option>
              <option value="regional">{t("regional")}</option>
            </NativeSelect>
          </Field>
          <Field label={t("Year described")}><Input type="number" value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} required /></Field>
          <Field label={t("CO₂ (kg/kWh)")}><Input type="number" step="any" min="0" value={form.co2} onChange={(e) => setForm({ ...form, co2: e.target.value })} required /></Field>
          <Field label={t("CH₄ (kg/kWh)")}><Input type="number" step="any" min="0" value={form.ch4} onChange={(e) => setForm({ ...form, ch4: e.target.value })} /></Field>
          <Field label={t("N₂O (kg/kWh)")}><Input type="number" step="any" min="0" value={form.n2o} onChange={(e) => setForm({ ...form, n2o: e.target.value })} /></Field>
          <Field label={t("Source")}><Input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} placeholder={t("e.g. IEA Emissions Factors 2021")} required /></Field>
          <div className="col-span-2 sm:col-span-4 flex justify-end">
            <Button variant="primary" size="sm" type="submit" disabled={busy}>
              <Plus className="size-3.5 me-1" aria-hidden="true" />{t("Add grid factor")}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
};

export default GridFactorsPanel;
