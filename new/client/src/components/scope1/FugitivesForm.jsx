import React, { useState } from "react";
import CustomDropdown from "../CustomDropdown";

const FugitivesForm = ({ data, onChange }) => {
  const [method, setMethod] = useState(data.fugitive_method || "average");

  const handleMethodChange = (val) => {
    setMethod(val);
    onChange("fugitive_method", val);
  };

  return (
    <div className="fugitives-form">
      <h4 style={{ color: "var(--accent-color)", marginBottom: "15px" }}>
        Fugitive Emissions
      </h4>

      <div className="input-group">
        <label>Method</label>
        <div
          className="toggle-container"
          style={{
            background: "#f3f4f6",
            padding: "4px",
            borderRadius: "8px",
            display: "flex",
            gap: "5px",
            marginBottom: "15px",
            width: "100%",
          }}
        >
          <button
            className={`btn-toggle ${method === "average" ? "active" : ""}`}
            onClick={() => handleMethodChange("average")}
            style={{
              flex: 1,
              padding: "6px 12px",
              borderRadius: "6px",
              border: "none",
              background:
                method === "average" ? "var(--accent-color)" : "transparent",
              color: method === "average" ? "white" : "#6b7280",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Average (Count)
          </button>
          <button
            className={`btn-toggle ${method === "screening" ? "active" : ""}`}
            onClick={() => handleMethodChange("screening")}
            style={{
              flex: 1,
              padding: "6px 12px",
              borderRadius: "6px",
              border: "none",
              background:
                method === "screening" ? "var(--accent-color)" : "transparent",
              color: method === "screening" ? "white" : "#6b7280",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Screening (PPM)
          </button>
          <button
            className={`btn-toggle ${method === "pipeline" ? "active" : ""}`}
            onClick={() => handleMethodChange("pipeline")}
            style={{
              flex: 1,
              padding: "6px 12px",
              borderRadius: "6px",
              border: "none",
              background:
                method === "pipeline" ? "var(--accent-color)" : "transparent",
              color: method === "pipeline" ? "white" : "#6b7280",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Pipeline
          </button>
        </div>
      </div>

      {/* Component Type & Service Type removed as per request - handled by Emission Factor selection */}

      {method === "average" && (
        <div className="input-group">
          <label>Count (Number of Sources)</label>
          <input
            type="number"
            className="mole-input"
            value={data.amount || ""}
            onChange={(e) => onChange("amount", e.target.value)}
            placeholder="Count"
          />
        </div>
      )}

      {method === "screening" && (
        <>
          <div className="input-group">
            <label>Count (Number of Sources)</label>
            <input
              type="number"
              className="mole-input"
              value={data.amount || ""}
              onChange={(e) => onChange("amount", e.target.value)}
              placeholder="Count"
            />
          </div>
          <div className="input-group">
            <label>Screening Value (ppm)</label>
            <input
              type="number"
              className="mole-input"
              value={data.fugitive_ppm || ""}
              onChange={(e) => onChange("fugitive_ppm", e.target.value)}
              placeholder="e.g. 500"
            />
          </div>
        </>
      )}

      {method === "pipeline" && (
        <div className="input-group">
          <label>Length (km)</label>
          <input
            type="number"
            className="mole-input"
            value={data.amount || ""}
            onChange={(e) => onChange("amount", e.target.value)}
            placeholder="Length"
          />
        </div>
      )}
    </div>
  );
};

export default FugitivesForm;
