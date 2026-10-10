import React, { useState, useEffect } from "react";
import { Dialog, Button, Field, Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import api from "../../api";
import { useToast } from "../Toast";
import { MARKET_INSTRUMENTS } from "../scope2-form/marketInstruments";
import { apiError } from "../../utils/apiError";
import { t } from "../../i18n";
import { editRequest, editScope } from "./editEmissionRequest";

export interface EditEmissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  emission: any;
  onSuccess?: () => void;
  facilities?: Array<{ id: number | string; name: string; field?: string }>;
}

export const EditEmissionModal: React.FC<EditEmissionModalProps> = ({
  isOpen,
  onClose,
  emission,
  onSuccess,
  facilities = [],
}) => {
  const toast = useToast();
  const [loading, setLoading] = useState<boolean>(false);
  const [formData, setFormData] = useState({
    year: new Date().getFullYear(),
    month: 1,
    facility_id: "",
    process_type: "",
    fuel: "",
    amount: "",
    unit: "",
    // Scope 2 specific
    electricity_kwh: "",
    grid_region: "",
    market_instrument_type: "",
    market_emission_factor: "",
  });

  useEffect(() => {
    if (emission) {
      setFormData({
        year: emission.year || new Date().getFullYear(),
        month: emission.month || 1,
        facility_id: emission.facility_id ? String(emission.facility_id) : "",
        process_type: emission.process_type || "",
        fuel: emission.fuel || emission.fuel_type || "",
        amount: emission.amount ?? emission.quantity ?? "",
        unit: emission.unit || "",
        electricity_kwh: emission.electricity_kwh ?? emission.amount ?? "",
        grid_region: emission.grid_region || "",
        market_instrument_type: emission.market_instrument_type || "",
        market_emission_factor: emission.market_emission_factor ?? "",
      });
    }
  }, [emission]);

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!emission?.id) return;

    setLoading(true);
    try {
      const { url, payload } = editRequest(emission, formData);
      await api.put(url, payload);
      toast.success(t("Emission record updated successfully. Record returned to Pending review for verification."));
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error("Error updating emission record:", err);
      toast.error(apiError(err, t("Failed to update emission record")));
    } finally {
      setLoading(false);
    }
  };

  if (!emission) return null;

  const MONTHS = [
    { value: 1, label: t("January") },
    { value: 2, label: t("February") },
    { value: 3, label: t("March") },
    { value: 4, label: t("April") },
    { value: 5, label: t("May") },
    { value: 6, label: t("June") },
    { value: 7, label: t("July") },
    { value: 8, label: t("August") },
    { value: 9, label: t("September") },
    { value: 10, label: t("October") },
    { value: 11, label: t("November") },
    { value: 12, label: t("December") },
  ];

  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 15 }, (_, i) => currentYear - 10 + i);

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => !open && onClose()}
      title={t("Edit Emission Record #{{id}}", { id: String(emission.id) })}
      description={t("Update activity quantity, fuel/source, unit, or reporting period. Edited records will automatically return to Pending Review for verification.")}
      maxWidth="36rem"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            {t("Cancel")}
          </Button>
          <Button onClick={() => handleSubmit()} loading={loading} disabled={loading}>
            {t("Save Changes")}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label={t("Reporting Year *")}>
            <NativeSelect
              value={formData.year}
              onChange={(e) => handleChange("year", e.target.value)}
            >
              {yearOptions.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </NativeSelect>
          </Field>

          {/* Scope 3 records are yearly */}
          {editScope(emission) !== 3 && (
            <Field label={t("Month *")}>
              <NativeSelect
                value={formData.month}
                onChange={(e) => handleChange("month", e.target.value)}
              >
                {MONTHS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </NativeSelect>
            </Field>
          )}
        </div>

        {facilities.length > 0 && (
          <Field label={t("Facility / Region *")}>
            <NativeSelect
              value={formData.facility_id}
              onChange={(e) => handleChange("facility_id", e.target.value)}
            >
              <option value="">{t("Select Facility")}</option>
              {facilities.map((f) => (
                <option key={f.id} value={f.id}>{f.name} {f.field ? `(${f.field})` : ""}</option>
              ))}
            </NativeSelect>
          </Field>
        )}

        <div className="grid grid-cols-2 gap-4">
          <Field label={t("Category / Process")}>
            <Input
              value={formData.process_type}
              onChange={(e) => handleChange("process_type", e.target.value)}
              placeholder={t("e.g. combustion, flaring")}
            />
          </Field>

          <Field label={t("Fuel / Source")}>
            <Input
              value={formData.fuel}
              onChange={(e) => handleChange("fuel", e.target.value)}
              placeholder={t("e.g. Natural Gas, Diesel")}
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label={t("Activity Quantity *")}>
            <Input
              type="number"
              step="any"
              value={formData.amount}
              onChange={(e) => handleChange("amount", e.target.value)}
              placeholder="0.00"
              required
            />
          </Field>

          <Field label={t("Unit *")}>
            <Input
              value={formData.unit}
              onChange={(e) => handleChange("unit", e.target.value)}
              placeholder={t("e.g. scf, m3, gal, bbl, kWh")}
              required
            />
          </Field>
        </div>

        {(editScope(emission) === 2 || formData.market_instrument_type) && (
          <div className="mt-2 flex flex-col gap-4 border-t border-border pt-4">
            <h4 className="text-sm font-semibold text-text">{t("Scope 2 Dual-Reporting Attributes")}</h4>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t("Market Instrument Type")}>
                <NativeSelect
                  value={formData.market_instrument_type}
                  onChange={(e) => handleChange("market_instrument_type", e.target.value)}
                >
                  {MARKET_INSTRUMENTS.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </NativeSelect>
              </Field>

              <Field label={t("Market Emission Factor (kg CO2e/kWh)")}>
                <Input
                  type="number"
                  step="any"
                  value={formData.market_emission_factor}
                  onChange={(e) => handleChange("market_emission_factor", e.target.value)}
                  placeholder={t("0.000 (0 for certified zero-carbon)")}
                />
              </Field>
            </div>
          </div>
        )}
      </form>
    </Dialog>
  );
};

export default EditEmissionModal;
