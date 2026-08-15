import re

with open('Scope3ImportWizard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add mode selection state
state_code = """  const [uploadProgress, setUploadProgress] = useState(null);
  const [importMode, setImportMode] = useState("activity"); // "activity" or "eeio"
  const fileInputRef = useRef(null);"""
content = content.replace('  const [uploadProgress, setUploadProgress] = useState(null);\n  const fileInputRef = useRef(null);', state_code)

# 2. Modify field groups to be dynamic based on mode
fields_code = """// ─── ALL field definitions with grouping + tooltips ────────────────────────
const FIELD_GROUPS_ACTIVITY = [
  {
    id: "identity",
    label: "Location & Identity",
    IconComp: Icon.Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column" },
    ],
  },
  {
    id: "classification",
    label: "GHG Protocol Classification",
    IconComp: Icon.Globe,
    fields: [
      { key: "category",      label: "Category",      required: true,  hint: "e.g. 1, 2, 3... or 'Category 11'" },
      { key: "sub_category",  label: "Sub Category",  required: false, hint: "e.g. Purchased Goods" },
      { key: "notes",         label: "Description / Notes", required: false, hint: "Description of the emission source" },
    ],
  },
  {
    id: "measurement",
    label: "Activity & Emissions",
    IconComp: Icon.Settings,
    fields: [
      { key: "amount",          label: "Activity Data Amount", required: true, hint: "Quantity of the activity" },
      { key: "unit",            label: "Activity Unit",        required: true, hint: "e.g. kg, USD, miles" },
      { key: "emission_factor", label: "Emission Factor",      required: false, hint: "Custom EF. If empty, the system will try to resolve it." },
      { key: "ef_unit",         label: "EF Unit",              required: false, hint: "e.g. kgCO2e/unit. Defaults to kg." },
      { key: "co2e",            label: "Total CO2e",           required: false, hint: "Provide direct CO2e to skip calculations" },
    ],
  }
];

const FIELD_GROUPS_EEIO = [
  {
    id: "identity",
    label: "Location & Identity",
    IconComp: Icon.Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12" },
    ],
  },
  {
    id: "measurement",
    label: "Spend & NAICS",
    IconComp: Icon.Settings,
    fields: [
      { key: "naics_code",      label: "NAICS Code",      required: true,  hint: "3-to-6 digit NAICS industry code" },
      { key: "spend_usd",       label: "Spend (USD)",     required: true,  hint: "Amount spent in USD" },
      { key: "notes",           label: "Description / Notes", required: false, hint: "Optional supplier or purchase description" },
    ],
  }
];"""

content = re.sub(
    r'// ─── ALL field definitions with grouping \+ tooltips ────────────────────────\nconst FIELD_GROUPS = \[.*?\];\n',
    fields_code + '\n',
    content,
    flags=re.DOTALL
)

# 3. Add import mode selector to step 1
mode_select = """              </div>
              
              <div className="s1w-mode-selector" style={{ marginTop: '24px', padding: '16px', border: '1px solid #e2e8f0', borderRadius: '8px', background: '#f8fafc' }}>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#334155' }}>Select Calculation Mode</h4>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input 
                      type="radio" 
                      name="importMode" 
                      value="activity" 
                      checked={importMode === 'activity'}
                      onChange={(e) => setImportMode(e.target.value)}
                    />
                    <span style={{ fontSize: '0.9rem', color: '#1e293b', fontWeight: importMode === 'activity' ? 600 : 400 }}>Activity-Based (Standard)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input 
                      type="radio" 
                      name="importMode" 
                      value="eeio" 
                      checked={importMode === 'eeio'}
                      onChange={(e) => setImportMode(e.target.value)}
                    />
                    <span style={{ fontSize: '0.9rem', color: '#1e293b', fontWeight: importMode === 'eeio' ? 600 : 400 }}>Spend-Based (EEIO NAICS)</span>
                  </label>
                </div>
              </div>

            </>
"""
content = content.replace('              </div>\n            </>', mode_select)

# 4. Handle dynamic FIELD_GROUPS rendering
content = content.replace('const flatRequired = FIELD_GROUPS.flatMap', 'const FIELD_GROUPS = importMode === "eeio" ? FIELD_GROUPS_EEIO : FIELD_GROUPS_ACTIVITY;\n    const flatRequired = FIELD_GROUPS.flatMap')
content = content.replace('{FIELD_GROUPS.map((group) => (', '{(importMode === "eeio" ? FIELD_GROUPS_EEIO : FIELD_GROUPS_ACTIVITY).map((group) => (')
content = content.replace('          const flatRequired = FIELD_GROUPS.flatMap((g)', '          const FIELD_GROUPS = importMode === "eeio" ? FIELD_GROUPS_EEIO : FIELD_GROUPS_ACTIVITY;\n          const flatRequired = FIELD_GROUPS.flatMap((g)')


# 5. Pass scope parameter in handleFinalUpload
submit_code = """      formData.append("scope", importMode === "eeio" ? "3_eeio" : "3");
      formData.append("global_factor_type", "auto");"""
content = content.replace('      formData.append("scope", "3");\n      formData.append("global_factor_type", "auto");', submit_code)


with open('Scope3ImportWizard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching Scope3ImportWizard.jsx for EEIO mode")
