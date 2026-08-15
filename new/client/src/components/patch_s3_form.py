import re

with open('Scope3Form.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add state variables for EEIO calculator
state_code = """  const [baseFactor, setBaseFactor] = useState(0);

  // EEIO Quick Calculator State
  const [showEeioCalc, setShowEeioCalc] = useState(false);
  const [eeioNaics, setEeioNaics] = useState("");
  const [eeioSpend, setEeioSpend] = useState("");
  const [eeioResult, setEeioResult] = useState(null);
  
  const handleCalculateEeio = async () => {
    if (!eeioNaics || !eeioSpend) return;
    try {
      const res = await api.post("/scope3/eeio-calculate", {
        naics_code: eeioNaics,
        spend_usd: eeioSpend
      });
      setEeioResult(res.data);
      // Auto-fill the form
      setCategory("1");
      setActivityType(`Spend: ${res.data.industry_name}`);
      setAmount(eeioSpend);
      setUnit("USD");
      setEmissionFactor(res.data.emission_factor);
    } catch (err) {
      toast.show("Error calculating EEIO emissions", "error");
    }
  };"""

content = content.replace('  const [baseFactor, setBaseFactor] = useState(0);', state_code)


# 2. Add the widget UI right above the "Add Scope 3 Entry" button area
widget_code = """
        {/* EEIO Quick Spend Calculator */}
        <div style={{ marginTop: "20px", marginBottom: "10px", padding: "16px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }} onClick={() => setShowEeioCalc(!showEeioCalc)}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "1.2rem" }}>💰</span>
              <strong style={{ color: "#334155" }}>EEIO Quick Spend Calculator</strong>
              <span style={{ fontSize: "0.8rem", color: "#64748b", marginLeft: "10px" }}>Convert financial spend to CO₂e using NAICS factors</span>
            </div>
            <span>{showEeioCalc ? "▲" : "▼"}</span>
          </div>
          
          {showEeioCalc && (
            <div style={{ marginTop: "16px", display: "flex", gap: "16px", alignItems: "flex-end" }}>
              <div className="input-group" style={{ flex: 1 }}>
                <label>NAICS Code (3-6 digits)</label>
                <input
                  type="text"
                  className="mole-input"
                  placeholder="e.g. 541 (Consulting)"
                  value={eeioNaics}
                  onChange={(e) => setEeioNaics(e.target.value)}
                />
              </div>
              <div className="input-group" style={{ flex: 1 }}>
                <label>Spend Amount (USD)</label>
                <input
                  type="number"
                  className="mole-input"
                  placeholder="0.00"
                  value={eeioSpend}
                  onChange={(e) => setEeioSpend(e.target.value)}
                />
              </div>
              <button 
                className="action-btn" 
                style={{ height: "38px", padding: "0 16px", background: "#3b82f6", color: "white" }}
                onClick={handleCalculateEeio}
              >
                Calculate & Auto-fill
              </button>
            </div>
          )}
          {eeioResult && showEeioCalc && (
            <div style={{ marginTop: "12px", padding: "12px", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.85rem", color: "#1e3a8a" }}>
                <strong>Industry:</strong> {eeioResult.industry_name} <br/>
                <strong>Factor:</strong> {eeioResult.emission_factor} {eeioResult.ef_unit} <br/>
                <strong>Estimated Emissions:</strong> <span style={{ fontSize: "1.1rem", fontWeight: "bold" }}>{eeioResult.co2e.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span> tCO₂e
              </div>
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex","""

content = content.replace("""        <div
          style={{
            display: "flex",""", widget_code)

with open('Scope3Form.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching Scope3Form.jsx")
