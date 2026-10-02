import React, { useState } from "react";
import { NativeSelect } from "../ui/NativeSelect";
import { X, PlusCircle, CheckCircle2, AlertCircle, FileText } from "lucide-react";
import api from "../api";
import { useToast } from "./Toast";

const QuickAddCustomFactorModal = ({
  isOpen,
  onClose,
  onFactorCreated,
  processType = "combustion",
  defaultParentFuel = "",
}) => {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    factor_name: "",
    unit: "kg/MMBtu",
    co2_factor: "",
    ch4_factor: "",
    n2o_factor: "",
    hhv_factor: "",
    uncertainty: "7.0", // Tier 2 default ±7%
    parent_fuel: defaultParentFuel || "",
    source: "",
    description: "",
  });

  if (!isOpen) return null;

  const handleChange = (field, val) => {
    setFormData((prev) => ({ ...prev, [field]: val }));
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.factor_name.trim()) {
      setError("Please provide a factor name (e.g. 'Skikda Refinery Off-Gas 2026')");
      return;
    }
    if (!formData.co2_factor && !formData.ch4_factor) {
      setError("At least one emission factor (CO₂ or CH₄) is required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        factor_name: formData.factor_name.trim(),
        unit: formData.unit,
        co2_factor: formData.co2_factor ? parseFloat(formData.co2_factor) : 0,
        ch4_factor: formData.ch4_factor ? parseFloat(formData.ch4_factor) : 0,
        n2o_factor: formData.n2o_factor ? parseFloat(formData.n2o_factor) : 0,
        hhv_factor: formData.hhv_factor ? parseFloat(formData.hhv_factor) : undefined,
        uncertainty: formData.uncertainty ? parseFloat(formData.uncertainty) : 7.0,
        usage: processType || "combustion",
        parent_fuel: formData.parent_fuel || undefined,
        source: formData.source.trim() || "Facility Laboratory GC / Delivery Analysis",
        description: formData.description.trim() || undefined,
      };

      const res = await api.post("/custom-factors", payload);
      toast.success("Tier 2 custom factor registered successfully");
      const createdFactor = res.data?.factor || {
        id: res.data?.id,
        factor_name: formData.factor_name.trim(),
        ...payload,
      };

      if (onFactorCreated) {
        onFactorCreated(createdFactor);
      }
      onClose();
    } catch (err) {
      console.error("Failed to create custom factor:", err);
      const errMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        "Failed to create custom factor. Please verify inputs.";
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(17, 24, 39, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        className="modal-card"
        style={{
          background: "#ffffff",
          borderRadius: "12px",
          width: "100%",
          maxWidth: "560px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
          border: "1px solid #e5e7eb",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid #e5e7eb",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "#f9fafb",
          }}
        >
          <div className="flex! items-center! gap-[8px]!">
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(255, 102, 0, 0.1)",
                color: "var(--color-link)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <PlusCircle size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 600, color: "#111827" }}>
                Register Tier 2 Custom Factor
              </h3>
              <p style={{ margin: 0, fontSize: "0.75rem", color: "#6b7280" }}>
                Add a site-calibrated or supplier emission factor without leaving this form
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{
              border: "none",
              background: "transparent",
              color: "#9ca3af",
              cursor: "pointer",
              padding: "4px",
              borderRadius: "4px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: "20px" }}>
          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 12px",
                backgroundColor: "#fef2f2",
                border: "1px solid #fee2e2",
                borderRadius: "6px",
                color: "#b91c1c",
                fontSize: "0.8rem",
                marginBottom: "16px",
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="flex! flex-col! gap-[14px]!">
            {/* Factor Name */}
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "#374151",
                  marginBottom: "4px",
                }}
              >
                Factor Name <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <input
                type="text"
                className="mole-input"
                style={{ width: "100%", padding: "8px 10px", fontSize: "0.85rem" }}
                placeholder="e.g. Hassi R'Mel Fuel Gas 2026, Skikda Distillate"
                value={formData.factor_name}
                onChange={(e) => handleChange("factor_name", e.target.value)}
                required
              />
            </div>

            {/* Units & Base Fuel */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "#374151",
                    marginBottom: "4px",
                  }}
                >
                  Factor Unit <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <NativeSelect
                  className="mole-input"
                  style={{ width: "100%", padding: "8px 10px", fontSize: "0.85rem" }}
                  value={formData.unit}
                  onChange={(e) => handleChange("unit", e.target.value)}
                >
                  <option value="kg/MMBtu">kg / MMBtu (Energy basis)</option>
                  <option value="kg/m3">kg / m³ (Volumetric gas)</option>
                  <option value="kg/scf">kg / scf (Volumetric gas)</option>
                  <option value="kg/liter">kg / Liter (Liquid fuel)</option>
                  <option value="kg/gal">kg / Gallon (Liquid fuel)</option>
                  <option value="kg/kg">kg / kg (Mass basis)</option>
                  <option value="tonne/tonne">tonne / tonne (Mass basis)</option>
                </NativeSelect>
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "#374151",
                    marginBottom: "4px",
                  }}
                >
                  Parent / Reference Fuel
                </label>
                <input
                  type="text"
                  className="mole-input"
                  style={{ width: "100%", padding: "8px 10px", fontSize: "0.85rem" }}
                  placeholder="e.g. Natural Gas, Diesel"
                  value={formData.parent_fuel}
                  onChange={(e) => handleChange("parent_fuel", e.target.value)}
                />
              </div>
            </div>

            {/* Gas Emission Factors */}
            <div
              style={{
                background: "#f9fafb",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                padding: "12px",
              }}
            >
              <div
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "#4b5563",
                  marginBottom: "8px",
                  textTransform: "uppercase",
                  letterSpacing: "0.025em",
                }}
              >
                Emission Factors ({formData.unit})
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.7rem",
                      color: "#6b7280",
                      marginBottom: "2px",
                    }}
                  >
                    CO₂ Factor
                  </label>
                  <input
                    type="number"
                    step="any"
                    className="mole-input"
                    style={{ width: "100%", padding: "6px 8px", fontSize: "0.85rem" }}
                    placeholder="e.g. 53.06"
                    value={formData.co2_factor}
                    onChange={(e) => handleChange("co2_factor", e.target.value)}
                  />
                </div>
                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.7rem",
                      color: "#6b7280",
                      marginBottom: "2px",
                    }}
                  >
                    CH₄ Factor
                  </label>
                  <input
                    type="number"
                    step="any"
                    className="mole-input"
                    style={{ width: "100%", padding: "6px 8px", fontSize: "0.85rem" }}
                    placeholder="e.g. 0.001"
                    value={formData.ch4_factor}
                    onChange={(e) => handleChange("ch4_factor", e.target.value)}
                  />
                </div>
                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.7rem",
                      color: "#6b7280",
                      marginBottom: "2px",
                    }}
                  >
                    N₂O Factor
                  </label>
                  <input
                    type="number"
                    step="any"
                    className="mole-input"
                    style={{ width: "100%", padding: "6px 8px", fontSize: "0.85rem" }}
                    placeholder="e.g. 0.0001"
                    value={formData.n2o_factor}
                    onChange={(e) => handleChange("n2o_factor", e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* HHV & Uncertainty */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "#374151",
                    marginBottom: "4px",
                  }}
                >
                  Heating Value (HHV)
                </label>
                <input
                  type="number"
                  step="any"
                  className="mole-input"
                  style={{ width: "100%", padding: "8px 10px", fontSize: "0.85rem" }}
                  placeholder="e.g. 1085 (Btu/scf)"
                  value={formData.hhv_factor}
                  onChange={(e) => handleChange("hhv_factor", e.target.value)}
                />
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "#374151",
                    marginBottom: "4px",
                  }}
                >
                  Factor Uncertainty (±%)
                </label>
                <div className="relative!">
                  <input
                    type="number"
                    step="0.1"
                    className="mole-input"
                    style={{ width: "100%", padding: "8px 10px", fontSize: "0.85rem" }}
                    placeholder="7.0"
                    value={formData.uncertainty}
                    onChange={(e) => handleChange("uncertainty", e.target.value)}
                  />
                  <span
                    style={{
                      position: "absolute",
                      right: "10px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      fontSize: "0.75rem",
                      color: "#9ca3af",
                    }}
                  >
                    % (Tier 2 default: ±7%)
                  </span>
                </div>
              </div>
            </div>

            {/* Audit Reference / Source */}
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "#374151",
                  marginBottom: "4px",
                }}
              >
                Data Source / Lab Certificate Reference
              </label>
              <input
                type="text"
                className="mole-input"
                style={{ width: "100%", padding: "8px 10px", fontSize: "0.85rem" }}
                placeholder="e.g. Sonatrach Analysis Certificate #2026-GC-041, Naftal Slip"
                value={formData.source}
                onChange={(e) => handleChange("source", e.target.value)}
              />
            </div>
          </div>

          {/* Footer Actions */}
          <div
            style={{
              marginTop: "20px",
              paddingTop: "14px",
              borderTop: "1px solid #e5e7eb",
              display: "flex",
              justifyContent: "flex-end",
              gap: "10px",
            }}
          >
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
              style={{ padding: "8px 16px", fontSize: "0.85rem" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{
                padding: "8px 20px",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              {loading ? (
                "Saving..."
              ) : (
                <>
                  <CheckCircle2 size={16} />
                  <span>Save & Apply Factor</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuickAddCustomFactorModal;
