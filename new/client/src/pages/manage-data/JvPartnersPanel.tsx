import React, { useEffect, useState } from "react";
import { Archive, Check, Edit2, Plus, RotateCcw, X } from "lucide-react";
import api from "../../api";
import { Button, Field, Input } from "../../ui";
import { useToast } from "../../components/Toast";
import { apiError } from "../../utils/apiError";
import { t } from "../../i18n";

// Administrators enter the real JV partners (they were a fixed demo list): add, rename, archive and restore,
// every change audited by the server (D9, GB RY2022 GB-028)

export interface JvPartner {
  id: number;
  name: string;
  code: string;
  country: string | null;
  is_operator?: boolean;
  is_archived?: boolean;
}

const BLANK = { name: "", code: "", country: "", is_operator: false };

export const JvPartnersPanel: React.FC<{ onChanged: () => void }> = ({ onChanged }) => {
  const toast = useToast();
  const [rows, setRows] = useState<JvPartner[]>([]);
  const [form, setForm] = useState<typeof BLANK & { id?: number }>(BLANK);
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.get("/equity/partners", { params: { include_archived: 1 } })
      .then((r) => setRows(r.data || []))
      .catch((err) => toast.show(apiError(err), "error"));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.code.trim()) {
      toast.show(t("Partner name and code are required"), "warning");
      return;
    }
    setBusy(true);
    try {
      const body = { name: form.name.trim(), code: form.code.trim(), country: form.country.trim() || null,
        is_operator: form.is_operator };
      if (form.id) await api.put(`/equity/partners/${form.id}`, body);
      else await api.post("/equity/partners", body);
      toast.show(form.id ? t("Partner updated") : t("Partner added"), "success");
      setForm(BLANK);
      await load();
      onChanged();
    } catch (err) {
      toast.show(apiError(err), "error");
    } finally {
      setBusy(false);
    }
  };

  const archive = async (p: JvPartner, restore: boolean) => {
    try {
      await api.post(`/equity/partners/${p.id}/archive`, { restore });
      toast.show(restore ? t("Partner restored") : t("Partner archived"), "success");
      await load();
      onChanged();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  return (
    <div className="pt-3 border-t border-border space-y-3" data-testid="jv-partners-panel">
      <h4 className="text-xs font-semibold text-text uppercase tracking-wide">{t("JV partners")}</h4>
      <table className="w-full text-start text-sm border-collapse">
        <tbody>
          {rows.map((p) => (
            <tr key={p.id} className={`border-b border-border/50 ${p.is_archived ? "opacity-60" : ""}`}>
              <td className="py-1.5 font-medium">
                {p.name}
                {p.is_operator && <span className="ms-2 text-xs text-text-secondary">{t("Operator")}</span>}
                {p.is_archived && <span className="ms-2 text-xs text-text-secondary">{t("Archived")}</span>}
              </td>
              <td className="py-1.5 font-mono text-xs">{p.code}</td>
              <td className="py-1.5 text-xs text-text-secondary">{p.country || "-"}</td>
              <td className="py-1.5 text-end whitespace-nowrap">
                <Button variant="secondary" size="sm" aria-label={t("Edit {{name}}", { name: p.name })} title={t("Edit")}
                  onClick={() => setForm({ id: p.id, name: p.name, code: p.code, country: p.country || "",
                    is_operator: Boolean(p.is_operator) })}>
                  <Edit2 className="size-3" aria-hidden="true" />
                </Button>
                {p.is_archived ? (
                  <Button variant="secondary" size="sm" className="ms-1" aria-label={t("Restore {{name}}", { name: p.name })}
                    title={t("Restore")} onClick={() => archive(p, true)}>
                    <RotateCcw className="size-3" aria-hidden="true" />
                  </Button>
                ) : (
                  <Button variant="secondary" size="sm" className="ms-1" aria-label={t("Archive {{name}}", { name: p.name })}
                    title={t("Archive")} onClick={() => archive(p, false)}>
                    <Archive className="size-3" aria-hidden="true" />
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <form onSubmit={save} className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-end">
        <Field label={t("Partner name")}>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label={t("Code")}>
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
        </Field>
        <Field label={t("Country")}>
          <Input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
        </Field>
        <div className="flex gap-2 items-center pb-1">
          <label className="text-xs flex items-center gap-1">
            <input type="checkbox" checked={form.is_operator}
              onChange={(e) => setForm({ ...form, is_operator: e.target.checked })} />
            {t("Operator")}
          </label>
          <Button variant="primary" size="sm" type="submit" disabled={busy}>
            {form.id ? <Check className="size-3.5 me-1" aria-hidden="true" /> : <Plus className="size-3.5 me-1" aria-hidden="true" />}
            {form.id ? t("Save") : t("Add")}
          </Button>
          {form.id && (
            <Button variant="secondary" size="sm" onClick={() => setForm(BLANK)} aria-label={t("Cancel")}>
              <X className="size-3.5" aria-hidden="true" />
            </Button>
          )}
        </div>
      </form>
    </div>
  );
};

export default JvPartnersPanel;
