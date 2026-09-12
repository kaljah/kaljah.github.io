import React, { useState, useEffect } from "react";
import {
  Search,
  Book,
  ChevronDown,
  ChevronRight,
  Zap,
  Wind,
  Flame,
  Database,
  Filter,
  Info,
  Star,
  Globe,
  Ruler,
  Percent,
  Activity,
  Settings,
} from "lucide-react";
import api from "../api";
import "./ReferenceData.css";

// Factors now loaded from API

const ReferenceData = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [customFactors, setCustomFactors] = useState([]);
  const [apiFactors, setApiFactors] = useState({});
  const [collapsed, setCollapsed] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [customRes, apiRes] = await Promise.all([
        api.get("/custom-factors"),
        api.get("/emission-factors"),
      ]);
      setCustomFactors(customRes.data);
      setApiFactors(apiRes.data.factors || {});
      setLoading(false);
    } catch (error) {
      console.error("Failed to load factors:", error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const toggleCategory = (cat) => {
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  const filterFactors = (factorsObj) => {
    return Object.entries(factorsObj)
      .filter(([name]) => name.toLowerCase().includes(searchTerm.toLowerCase()))
      .map(([name, data]) => ({
        name,
        ...data,
        usage: data.usage || [],
      }));
  };

  const categories = {
    custom: {
      title: "Custom & Regional Factors",
      icon: <Star size={20} style={{ color: "#10b981" }} />,
      color: "#10b981",
      factors: customFactors
        .filter((f) => f.name?.toLowerCase().includes(searchTerm.toLowerCase()))
        .map((f) => ({
          name: f.name,
          hhv: f.hhv_factor,
          co2: f.co2_factor,
          ch4: f.ch4_factor,
          n2o: f.n2o_factor,
          unit: f.unit,
          usage: f.usage ? [f.usage] : ["Custom"],
          isCustom: true,
        })),
    },
    gases: {
      title: "Gaseous Fuels",
      icon: <Wind size={20} />,
      color: "#3b82f6",
      factors: filterFactors(apiFactors).filter((f) => f.type === "gases"),
    },
    liquids: {
      title: "Liquid Fuels",
      icon: <Database size={20} />,
      color: "#8b5cf6",
      factors: filterFactors(apiFactors).filter((f) => f.type === "liquids"),
    },
    solids: {
      title: "Solid Fuels",
      icon: <Zap size={20} />,
      color: "#f59e0b",
      factors: filterFactors(apiFactors).filter((f) => f.type === "solids"),
    },
    equipment: {
      title: "Equipment & Fugitive Factors",
      icon: <Filter size={20} />,
      color: "#ff6600",
      factors: filterFactors(apiFactors).filter((f) => f.type === "equipment"),
    },
    gwp: {
      title: "Global Warming Potentials (GWPs)",
      icon: <Globe size={20} />,
      color: "#0ea5e9",
      isStatic: true,
      columns: ["Gas", "AR4 (2007)", "AR5 (2013)", "AR6 (2021)"],
      items: [
        { gas: "Carbon Dioxide (CO₂)", ar4: "1", ar5: "1", ar6: "1" },
        { gas: "Methane (CH₄)", ar4: "25", ar5: "28", ar6: "27.9" },
        { gas: "Nitrous Oxide (N₂O)", ar4: "298", ar5: "265", ar6: "273" },
      ],
    },
    conversions: {
      title: "Unit Conversions",
      icon: <Ruler size={20} />,
      color: "#14b8a6",
      isStatic: true,
      columns: ["From Unit", "To Unit", "Multiplier / Factor"],
      items: [
        { from: "1 MJ (Megajoule)", to: "MMBtu", mult: "0.000947817" },
        { from: "1 GJ (Gigajoule)", to: "MMBtu", mult: "0.947817" },
        { from: "1 kWh", to: "MMBtu", mult: "0.003412142" },
        { from: "1 MWh", to: "MMBtu", mult: "3.412142" },
        { from: "1 BTU", to: "MMBtu", mult: "0.000001" },
        { from: "1 BOE (Barrel of Oil Equivalent)", to: "MMBtu", mult: "5.8" },
      ],
    },
    uncertainty: {
      title: "Data Quality & Uncertainty Tiers",
      icon: <Percent size={20} />,
      color: "#ec4899",
      isStatic: true,
      columns: ["Tier", "Condition", "Description"],
      items: [
        {
          tier: "Tier 3 (High)",
          cond: "≤ 5% Uncertainty",
          desc: "High quality data based on direct measurement (e.g. flow meter with ±2.0% calibration).",
        },
        {
          tier: "Tier 2 (Medium)",
          cond: "≤ 15% Uncertainty",
          desc: "Good quality data based on engineering calculations and reliable operational parameters.",
        },
        {
          tier: "Tier 1 (Low)",
          cond: "> 15% Uncertainty",
          desc: "Estimated data based on generic default emission factors and production throughput.",
        },
      ],
    },
    hhv_defaults: {
      title: "Default Fuel Heating Values (HHV)",
      icon: <Flame size={20} />,
      color: "#f97316",
      isStatic: true,
      columns: ["Fuel Type", "Default Heating Value", "Unit", "Usage context"],
      items: [
        {
          fuel: "Natural Gas",
          hhv: "1,020",
          unit: "BTU/scf",
          context: "Fallback for generic gas combustion",
        },
        {
          fuel: "Diesel",
          hhv: "138,700",
          unit: "BTU/gal",
          context: "Fallback for diesel generators/vehicles",
        },
        {
          fuel: "Gasoline",
          hhv: "125,000",
          unit: "BTU/gal",
          context: "Fallback for light vehicles",
        },
        {
          fuel: "Fuel Oil",
          hhv: "138,000",
          unit: "BTU/gal",
          context: "Fallback for heavy heating oil",
        },
        {
          fuel: "Propane",
          hhv: "91,500",
          unit: "BTU/gal",
          context: "Fallback for LPG",
        },
        {
          fuel: "Butane",
          hhv: "103,000",
          unit: "BTU/gal",
          context: "Fallback for LPG",
        },
      ],
    },
    process_types: {
      title: "API Compendium Process Mappings",
      icon: <Activity size={20} />,
      color: "#6366f1",
      isStatic: true,
      columns: ["Process Name", "Category", "API Section", "Description"],
      items: [
        {
          name: "Stationary Combustion",
          cat: "Combustion",
          sec: "Section 5.1",
          desc: "Emissions from stationary fuel combustion sources",
        },
        {
          name: "Flaring",
          cat: "Combustion",
          sec: "Section 5.2",
          desc: "Gas flaring with dual-efficiency model",
        },
        {
          name: "Drilling - Mud Degassing",
          cat: "Vented",
          sec: "Section 6.2",
          desc: "CH₄ emissions from drilling mud degassing",
        },
        {
          name: "Well Completions & Workovers",
          cat: "Vented",
          sec: "Section 6.3",
          desc: "Flowback emissions during well completion",
        },
        {
          name: "Liquids Unloading",
          cat: "Vented",
          sec: "Section 6.4",
          desc: "Gas venting during liquids unloading operations",
        },
        {
          name: "Storage Tanks",
          cat: "Vented",
          sec: "Section 6.8",
          desc: "Flash emissions from crude oil and condensate storage",
        },
        {
          name: "Glycol Dehydrator",
          cat: "Vented",
          sec: "Section 6.11",
          desc: "CH₄ emissions from glycol dehydrators",
        },
        {
          name: "Acid Gas Removal (AGR)",
          cat: "Vented",
          sec: "Section 6.12",
          desc: "CO₂ venting from AGR units",
        },
        {
          name: "Wellhead Fugitive Emissions",
          cat: "Fugitive",
          sec: "Section 7.2.2",
          desc: "Equipment leaks from wellheads (oil/gas)",
        },
        {
          name: "Gathering & Boosting",
          cat: "Fugitive",
          sec: "Section 7.2.3",
          desc: "Fugitive emissions from gathering and boosting facilities",
        },
        {
          name: "Natural Gas Processing",
          cat: "Fugitive",
          sec: "Section 7.3",
          desc: "Emissions from gas processing plants",
        },
        {
          name: "Refinery Gas Systems",
          cat: "Fugitive",
          sec: "Section 7.4.1",
          desc: "Fugitive emissions from refinery gas systems",
        },
        {
          name: "Chemical Production (Process CO₂)",
          cat: "Process",
          sec: "Section 6 (Table 6-167)",
          desc: "Process CO₂ from chemical manufacturing",
        },
      ],
    },
    scope2_defaults: {
      title: "Scope 2 & 3 Methodological Defaults",
      icon: <Settings size={20} />,
      color: "#8b5cf6",
      isStatic: true,
      columns: ["Category", "Parameter", "Default Value", "Source / Rationale"],
      items: [
        {
          cat: "Scope 2 (Indirect Steam)",
          param: "Boiler Emission Factor",
          val: "53.06 kg CO₂/MMBtu",
          src: "API standard for generic natural gas fired boilers",
        },
        {
          cat: "Scope 2 (Overall)",
          param: "Normative Uncertainty",
          val: "± 30%",
          src: "GHG Protocol Value Chain default assigned when specific data is missing",
        },
        {
          cat: "Scope 3 (Overall)",
          param: "Normative Uncertainty",
          val: "± 30%",
          src: "GHG Protocol Value Chain default assigned when specific data is missing",
        },
      ],
    },
  };

  const visibleCategories = Object.entries(categories).filter(([key, cat]) => {
    const matchesType = categoryFilter === "all" || categoryFilter === key;

    if (cat.isStatic) {
      cat.filteredItems = cat.items;
      if (searchTerm) {
        cat.filteredItems = cat.items.filter((item) =>
          Object.values(item).some((v) =>
            v.toString().toLowerCase().includes(searchTerm.toLowerCase()),
          ),
        );
      }
      return matchesType && cat.filteredItems.length > 0;
    }

    const hasFactors = cat.factors.length > 0;
    return matchesType && hasFactors;
  });

  return (
    <div className="reference-data">
      <header
        className="top-bar"
        style={{
          padding: "0 0 30px 0",
          border: "none",
          background: "transparent",
        }}
      >
        <div className="breadcrumbs">
          <Book
            size={14}
            style={{ marginRight: "8px", color: "var(--text-secondary)" }}
          />
          <span>Resource Center</span>
          <span style={{ margin: "0 8px", color: "var(--text-secondary)" }}>
            /
          </span>
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
            Reference Data Library
          </span>
        </div>
      </header>

      <div style={{ marginBottom: "40px" }}>
        <h1
          style={{
            fontSize: "2.5rem",
            fontWeight: 800,
            color: "#1e293b",
            margin: "0 0 10px 0",
          }}
        >
          Reference Data Library
        </h1>
        <p style={{ fontSize: "1.1rem", color: "#64748b", maxWidth: "800px" }}>
          Centralized repository for emission factors, global warming potentials
          (GWPs), unit conversions, and data quality tiers. Custom regional
          factors tagged with <Star size={14} className="custom-star" />{" "}
          override global defaults.
        </p>
      </div>

      <div className="search-bar-container">
        <div className="search-input-wrapper">
          <Search
            className="search-icon"
            size={18}
            style={{
              position: "absolute",
              left: "16px",
              top: "50%",
              transform: "translateY(-50%)",
              opacity: 0.4,
            }}
          />
          <input
            type="text"
            className="search-input-field"
            placeholder="Search by name, fuel type, code, or value..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <select
          className="filter-select"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="all">All Categories</option>
          <option value="hhv_defaults">Default Heating Values</option>
          <option value="process_types">API Process Mappings</option>
          <option value="scope2_defaults">Scope 2 & 3 Defaults</option>
          <option value="gwp">Global Warming Potentials</option>
          <option value="conversions">Unit Conversions</option>
          <option value="uncertainty">Data Quality Tiers</option>
          <option value="custom">Custom & Regional</option>
          <option value="gases">Gases</option>
          <option value="liquids">Liquids</option>
          <option value="solids">Solids</option>
          <option value="equipment">Equipment</option>
        </select>
      </div>

      {loading ? (
        <div
          style={{ textAlign: "center", padding: "100px", color: "#64748b" }}
        >
          Loading Library Assets...
        </div>
      ) : (
        <div className="factors-list">
          {visibleCategories.map(([key, cat]) => (
            <div
              key={key}
              className="category-section"
              style={{ borderLeftColor: cat.color }}
            >
              <div
                className="category-header"
                onClick={() => toggleCategory(key)}
              >
                <div className="category-title">
                  {cat.icon}
                  {cat.title}
                  <span
                    className="count-badge"
                    style={{ background: cat.color }}
                  >
                    {cat.isStatic
                      ? cat.filteredItems.length
                      : cat.factors.length}
                  </span>
                </div>
                {collapsed[key] ? (
                  <ChevronRight size={20} />
                ) : (
                  <ChevronDown size={20} />
                )}
              </div>

              {!collapsed[key] && (
                <div className="factors-table-container">
                  <table className="factors-table">
                    <thead>
                      <tr>
                        {cat.isStatic ? (
                          cat.columns.map((col, cIdx) => (
                            <th key={cIdx}>{col}</th>
                          ))
                        ) : (
                          <>
                            <th>Name</th>
                            {key !== "equipment" ? (
                              <>
                                <th>HHV</th>
                                <th>CO₂</th>
                                <th>CH₄</th>
                                <th>N₂O</th>
                                <th>Unit</th>
                              </>
                            ) : (
                              <>
                                <th>CH₄ Factor</th>
                                <th>Unit</th>
                                <th>Description</th>
                              </>
                            )}
                            <th>Usage</th>
                          </>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {cat.isStatic
                        ? cat.filteredItems.map((item, idx) => (
                            <tr key={idx}>
                              {Object.values(item).map((val, i) => (
                                <td
                                  key={i}
                                  style={
                                    i === 0
                                      ? { fontWeight: 600, color: "#1e293b" }
                                      : {}
                                  }
                                >
                                  {val}
                                </td>
                              ))}
                            </tr>
                          ))
                        : cat.factors.map((f, idx) => (
                            <tr key={idx}>
                              <td className="factor-name">
                                {f.name}
                                {f.isCustom && (
                                  <Star size={14} className="custom-star" />
                                )}
                              </td>
                              {key !== "equipment" ? (
                                <>
                                  <td>{f.hhv || "-"}</td>
                                  <td>{f.co2 || "-"}</td>
                                  <td>{f.ch4 || "-"}</td>
                                  <td>{f.n2o || "-"}</td>
                                  <td>{f.unit}</td>
                                </>
                              ) : (
                                <>
                                  <td>{f.ch4 || "-"}</td>
                                  <td>{f.unit}</td>
                                  <td>{f.description}</td>
                                </>
                              )}
                              <td>
                                <div style={{ display: "flex", gap: "6px" }}>
                                  {f.usage.map((u, uIdx) => (
                                    <span
                                      key={uIdx}
                                      className={`usage-badge usage-${u.toLowerCase()}`}
                                    >
                                      {u}
                                    </span>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
          {visibleCategories.length === 0 && (
            <div
              style={{
                textAlign: "center",
                padding: "60px",
                background: "rgba(255,255,255,0.4)",
                borderRadius: "16px",
                border: "1px dashed rgba(0,0,0,0.1)",
              }}
            >
              <Info
                size={40}
                style={{ color: "#94a3b8", marginBottom: "16px" }}
              />
              <h3 style={{ color: "#1e293b", marginBottom: "8px" }}>
                No factors found
              </h3>
              <p style={{ color: "#64748b" }}>
                Try adjusting your search term or category filter.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReferenceData;
