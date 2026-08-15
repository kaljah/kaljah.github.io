import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { Chart, registerables } from "chart.js";
import { DEFAULT_GWP } from "../constants";

Chart.register(...registerables);

// Sonatrach Brand Colors (White Theme)
const THEME = {
  primary: [255, 255, 255], // White
  secondary: [248, 250, 252], // Slate 50
  accent: [255, 107, 0], // Sonatrach Orange
  dark: [15, 23, 42], // Slate 900
  text: [30, 41, 59], // Slate 800
  textMuted: [100, 116, 139], // Slate 500
  gold: [218, 165, 32], // Subtle Gold accent
  // Chart Palette
  chart: {
    orange: [255, 107, 0],
    slate: [15, 23, 42],
    teal: [20, 184, 166],
    indigo: [79, 70, 229],
    amber: [245, 158, 11],
    emerald: [16, 185, 129],
    red: [239, 68, 68],
    blue: [59, 130, 246],
  },
};

const toRgba = (c, a = 0.85) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${a})`;

// --- HELPER: Load Image ---
function loadImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "Anonymous";
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      resolve(canvas.toDataURL("image/jpeg"));
    };
    img.onerror = () => resolve(null);
    img.src = url;
  });
}

export async function generateModernPDF(api, filters) {
  const { year, scope, regionId, processType, comparisonYear, exclusionCriteria = 'None provided', verificationStatus = 'Not externally verified', personResponsible = 'Logged In User' } = filters;
  const selectedYear = year && year !== "all" ? year : new Date().getFullYear();
  const isComparison = comparisonYear && comparisonYear !== "none";

  // 1. Comprehensive Data Fetching
  // NOTE: When regionId is an array (multi-select), do NOT send facility_id param —
  // fetch all data then filter client-side (the API only accepts a single facility_id).
  const params = {
    limit: 5000, // Hard cap client-side; use /api/reports/export for full dataset
    // Omit year param entirely if 'all' is selected to fetch all historical data
    year: year && year !== "all" ? year : undefined,
    scope: scope && scope !== "all" ? scope : undefined,
    facility_id:
      regionId && regionId !== "all" && !Array.isArray(regionId)
        ? regionId
        : undefined,
    process_type:
      processType && processType !== "all" ? processType : undefined,
  };

  if (import.meta.env.DEV)
    console.log(
      "[Report] Fetching emissions with params:",
      params,
      "| regionId:",
      regionId,
    );

  try {
    const subFetchYear = year && year !== "all" ? year : undefined; // Omit for aggregation

    const [
      emissionsRes,
      facilitiesRes,
      mitigationRes,
      prodRes,
      goalRes,
      uncertaintyRes,
      baseYearRes,
      exclusionsRes,
      settingsRes,
      profileImg,
    ] = await Promise.all([
      api.get("/emissions", { params }),
      api.get("/facilities").catch(() => ({ data: [] })),
      api
        .get("/dashboard/mitigation", { params: { year: subFetchYear } })
        .catch(() => ({ data: [] })),
      api
        .get("/dashboard/intensity-stats", { params: { year: subFetchYear } })
        .catch(() => ({ data: [] })),
      api
        .get(`/dashboard/goals/${subFetchYear || new Date().getFullYear()}`)
        .catch(() => ({ data: null })),
      api
        .get("/dashboard/uncertainty", { params: { year: subFetchYear } })
        .catch(() => ({ data: null })),
      api.get("/dashboard/base-year").catch(() => ({ data: null })),
      api
        .get("/dashboard/exclusions", { params: { year: subFetchYear } })
        .catch(() => ({ data: [] })),
      api.get("/auth/settings").catch(() => ({ data: { gwp_standard: 'IPCC AR5' } })),
      loadImage("/company_profile.jpg").catch(() => null),
    ]);

    let reportData =
      emissionsRes.data.emissions ||
      emissionsRes.data.data ||
      emissionsRes.data ||
      [];
    if (!Array.isArray(reportData)) reportData = [];

    if (reportData.length >= 5000) {
      console.warn(
        "[ReportGenerator] Dataset capped at 5000 records. " +
          "Use server-side export for complete dataset.",
      );
    }

    if (import.meta.env.DEV)
      console.log(
        `[Report] Raw emissions fetched: ${reportData.length} records for year ${selectedYear}`,
      );

    const allFacilities = facilitiesRes.data || [];
    const mitigationData = mitigationRes.data || [];
    const productionData = prodRes.data || [];
    const specificGoal = goalRes.data;
    const uncertaintyData = uncertaintyRes.data;
    const baseYearData = baseYearRes.data;
    const exclusionsData = exclusionsRes.data || [];
    const settingsData = settingsRes.data || { gwp_standard: 'IPCC AR5' };
    const gwpStandard = settingsData.gwp_standard || 'IPCC AR5';

    // Client-side filtering by selected region array
    if (Array.isArray(regionId) && regionId.length > 0) {
      reportData = reportData.filter((r) =>
        regionId.includes(String(r.facility_id)),
      );
      if (import.meta.env.DEV)
        console.log(
          `[Report] After region filter (${regionId.length} regions): ${reportData.length} records`,
        );
    }

    let reportFacilities = [];
    if (Array.isArray(regionId) && regionId.length > 0) {
      reportFacilities = allFacilities.filter((f) =>
        regionId.includes(String(f.id)),
      );
    } else if (regionId && regionId !== "all") {
      reportFacilities = allFacilities.filter(
        (f) => String(f.id) === String(regionId),
      );
    } else {
      reportFacilities = allFacilities;
    }

    const fullData = await fetchAllReportData(
      api,
      selectedYear,
      reportData,
      params,
      productionData,
    );

    // Comparison Data
    let compData = null;
    if (isComparison) {
      const compParams = { ...params, year: comparisonYear };
      try {
        const cRes = await api.get("/emissions", { params: compParams });
        let cReportData = cRes.data.emissions || cRes.data || [];
        if (Array.isArray(regionId)) {
          cReportData = cReportData.filter((r) =>
            regionId.includes(String(r.facility_id)),
          );
        }
        const cProdRes = await api.get("/dashboard/intensity-stats", {
          params: { year: comparisonYear },
        });
        compData = await fetchAllReportData(
          api,
          comparisonYear,
          cReportData,
          compParams,
          cProdRes.data || [],
        );
      } catch (e) {
        console.warn("Comparison Fetch Failed", e);
      }
    }

    // Initialize PDF
    const doc = new jsPDF("p", "mm", "a4");
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;

    // --- HELPERS ---
    function drawBackground() {
      doc.setFillColor(255, 255, 255);
      doc.rect(0, 0, pageWidth, pageHeight, "F");
    }

    function drawFooter(pageNumberOverride = null) {
      const pageNumber = pageNumberOverride || doc.internal.getNumberOfPages();
      doc.setFillColor(250, 250, 250);
      doc.rect(0, pageHeight - 15, pageWidth, 15, "F"); // Light footer bg
      doc.setFontSize(8);
      doc.setTextColor(...THEME.textMuted);
      doc.text(
        `Sonatrach GHG Inventory ${year === "all" ? "Historical" : selectedYear} | ISO 14064-1 Compliant`,
        margin,
        pageHeight - 6,
      );
      doc.text(`Page ${pageNumber}`, pageWidth - margin - 10, pageHeight - 6, {
        align: "right",
      });
    }

    function addSectionHeader(
      number,
      title,
      yOverride = null,
      newPage = false,
    ) {
      let y = yOverride || 30;
      if (newPage || (yOverride && y > pageHeight - 40)) {
        doc.addPage();
        drawBackground();
        y = 30;
      }
      doc.setFillColor(...THEME.accent);
      doc.rect(margin, y - 5, 2, 10, "F");
      doc.setFontSize(14);
      doc.setTextColor(...THEME.accent);
      doc.setFont("helvetica", "bold");
      doc.text(`${number}. ${title}`, margin + 5, y + 2);
      doc.setDrawColor(230, 230, 230);
      doc.setLineWidth(0.2);
      doc.line(margin, y + 8, pageWidth - margin, y + 8);
      return y + 18;
    }

    function checkPageBreak(currentY, requiredSpace = 30) {
      if (currentY + requiredSpace > pageHeight - margin) {
        doc.addPage();
        drawBackground();
        drawFooter();
        return 30; // New curY
      }
      return currentY;
    }

    function addTextBlock(text, y, fontSize = 10, color = THEME.text) {
      doc.setFontSize(fontSize);
      doc.setTextColor(...color);
      doc.setFont("helvetica", "normal");
      const splitText = doc.splitTextToSize(text, pageWidth - margin * 2);
      y = checkPageBreak(y, splitText.length * 5 + 10);
      doc.text(splitText, margin, y);
      return y + splitText.length * 5 + 5;
    }

    // --- HELPER: Modern Table Styles ---
    const cleanTableTheme = {
      theme: "grid", // Cleaner grid
      headStyles: {
        fillColor: [255, 255, 255],
        textColor: THEME.text,
        fontStyle: "bold",
        lineColor: [200, 200, 200],
        lineWidth: { bottom: 0.5, top: 0, left: 0, right: 0 },
        halign: "left",
      },
      bodyStyles: {
        textColor: [70, 75, 85],
        lineColor: [240, 240, 240],
        lineWidth: { bottom: 0.5, top: 0, left: 0, right: 0 },
      },
      alternateRowStyles: { fillColor: [252, 253, 255] },
      columnStyles: {}, // First col bold
    };

    // --- INTERPRETATION GENERATORS ---
    function getScopeInterpretation(data) {
      if (!data.totalEmissions || data.totalEmissions === 0) {
        return "No emissions data available for the selected period.";
      }
      const scopes = Object.keys(data).filter(
        (k) => k.includes("Total") && k !== "totalScale" && k.includes("scope"),
      );
      if (scopes.length === 0) return "No emissions data available.";

      const maxScope = scopes.reduce((a, b) => (data[a] > data[b] ? a : b));
      const maxVal = data[maxScope] || 0;
      // BUG-UI-11 FIX: Guard against division by zero producing "Infinity%"
      const pct =
        data.totalEmissions > 0
          ? ((maxVal / data.totalEmissions) * 100).toFixed(1)
          : "0.0";
      const scopeName = maxScope
        .replace("Total", "")
        .replace("scope", "Scope ");
      return `The inventory is dominated by ${scopeName} emissions, accounting for ${pct}% (${maxVal.toFixed(1)} tCO2e) of the total footprint. This highlights the critical need for targeted reduction strategies in this area.`;
    }

    function getTrendInterpretation(data) {
      if (!data.monthlyData || Object.keys(data.monthlyData).length === 0) {
        return "No monthly data available to analyze trends.";
      }
      // Find peak month
      const peakMonth = Object.keys(data.monthlyData).reduce((a, b) =>
        data.monthlyData[a] > data.monthlyData[b] ? a : b,
      );
      const peakVal = data.monthlyData[peakMonth];
      const monthName = new Date(0, peakMonth - 1).toLocaleString("default", {
        month: "long",
      });
      return `Monthly analysis reveals a peak in ${monthName} with ${peakVal.toFixed(1)} tCO2e. Seasonal variations may be attributed to operational fluctuations, heating/cooling demands, or specific maintenance activities during this period.`;
    }

    // Generate Charts with High Res
    const charts = await generateReportCharts(fullData, compData, isComparison);

    /**
     * =========================================================
     * PAGE 1: COVER [WHITE THEME]
     * =========================================================
     */
    drawBackground();
    doc.setFillColor(...THEME.accent);
    doc.rect(0, 0, pageWidth, 8, "F");
    doc.setGState(new doc.GState({ opacity: 0.1 }));
    doc.triangle(
      pageWidth,
      pageHeight * 0.4,
      pageWidth,
      pageHeight,
      pageWidth * 0.4,
      pageHeight,
      "F",
    );
    doc.setGState(new doc.GState({ opacity: 1.0 }));

    const coverTitleY = pageHeight * 0.45;
    doc.setFontSize(140);
    doc.setTextColor(240, 240, 240);
    doc.text(
      `${year === "all" ? "DATA" : selectedYear}`,
      pageWidth - 20,
      coverTitleY + 30,
      { align: "right" },
    );

    doc.setFontSize(72);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("GHG", 25, coverTitleY);
    doc.setFontSize(32);
    doc.setTextColor(...THEME.text);
    doc.text("INVENTORY REPORT", 25, coverTitleY + 18);
    doc.setFontSize(22);
    doc.setTextColor(...THEME.textMuted);
    doc.text(
      `${year === "all" ? "All Historical Records" : "FISCAL YEAR " + selectedYear}`,
      25,
      coverTitleY + 32,
    );

    doc.setFontSize(9);
    doc.setTextColor(...THEME.textMuted);
    doc.text(
      `CONSOLIDATED REPORT | PHASE 1 DATA | ${reportFacilities.length} ASSETS`,
      25,
      pageHeight - 55,
    );
    doc.text(
      "API COMPENDIUM 2021 / ISO 14064-1 COMPLIANT",
      25,
      pageHeight - 50,
    );

    // KPI Banner
    doc.setFillColor(...THEME.dark);
    doc.rect(0, pageHeight - 40, pageWidth, 40, "F");
    const overlayY = pageHeight - 28;
    doc.setFontSize(8);
    doc.setTextColor(150, 160, 180);
    doc.text("TOTAL CO2e", 30, overlayY);
    doc.setFontSize(16);
    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.text(`${fullData.totalScale} t`, 30, overlayY + 12);
    doc.setFontSize(8);
    doc.setTextColor(150, 160, 180);
    doc.text("INTENSITY", 100, overlayY);
    doc.setFontSize(16);
    doc.setTextColor(255, 255, 255);
    doc.text(`${fullData.intensityMetrics.avgCo2}`, 100, overlayY + 12);
    doc.setFontSize(8);
    doc.setTextColor(150, 160, 180);
    doc.text("PROJECTS", 160, overlayY);
    doc.setFontSize(16);
    doc.setTextColor(255, 255, 255);
    doc.text(`${mitigationData.length}`, 160, overlayY + 12);

    /**
     * =========================================================
     * PAGE 2: CAUTIONARY STATEMENT
     * =========================================================
     */
    doc.addPage();
    drawBackground();

    doc.setFontSize(16);
    doc.setTextColor(...THEME.dark);
    doc.setFont("helvetica", "bold");
    const title = "CAUTIONARY STATEMENT ABOUT THE GHG EMISSIONS ESTIMATES";
    const splitTitle = doc.splitTextToSize(title, pageWidth - margin * 2);
    doc.text(splitTitle, margin, 40);

    const lineY = 40 + splitTitle.length * 6; // Dynamic line Y
    doc.setDrawColor(...THEME.accent);
    doc.setLineWidth(0.5);
    doc.line(margin, lineY, margin + 120, lineY);

    let cautionY = lineY + 15;

    // Dynamic Region Name
    let regionName = "Sonatrach Corporate";
    if (reportFacilities.length === 1) {
      regionName = reportFacilities[0].name;
    } else if (regionId !== "all" && !Array.isArray(regionId)) {
      // Try to find if filtered by 1 but logic above handles reportFacilities length
    }

    // Dynamic Scope Text
    let scopeText =
      "This report aimed to estimate both direct GHG emissions (Scope 1)";
    if (fullData.scope2Total > 0)
      scopeText +=
        " and indirect emissions (Scope 2) associated with purchased electricity used in our operations";
    if (fullData.scope3Total > 0)
      scopeText += " and Scope 3 when data is available";
    scopeText += ".";

    const cautionText = `The estimated greenhouse gas emissions (GHG) described in this report for the reporting years in the "${regionName}" Region are derived from a combination of measured and estimated data using the best available information obtained.

Industry standards and best practices for estimating GHG emissions, including guidelines from the Intergovernmental Panel on Climate Change (IPCC), the United States Environmental Protection Agency (EPA), the American Petroleum Institute (API), Sonatrach, and ISO 14064 have been applied.

Conservative assumptions regarding the number and type of emitting equipment have been used, and they will be refined as more comprehensive emission inventories are developed. The uncertainty associated with emission estimates depends on the variation of processes and operations, the availability of sufficient representative data, the quality of available data, and the methodologies used for measurement and estimation.

${scopeText}`;

    cautionY = addTextBlock(cautionText, cautionY, 11, THEME.text);

    drawFooter();

    /**
     * =========================================================
     * PAGE 3: EXECUTIVE SUMMARY (Now Page 3 per Modern Structure)
     * =========================================================
     */
    doc.addPage();
    drawBackground();
    let curY = 30;

    doc.setFontSize(24);
    doc.setTextColor(...THEME.dark);
    doc.setFont("helvetica", "bold");
    doc.text("EXECUTIVE SUMMARY", margin, curY);
    doc.setDrawColor(...THEME.accent);
    doc.setLineWidth(1);
    doc.line(margin, curY + 4, margin + 80, curY + 4);

    curY += 20;

    let narrative = `The ${year === "all" ? "comprehensive" : selectedYear} GHG Inventory consolidates emissions from ${reportFacilities.length} facilities. Represents a precise accounting of direct and indirect greenhouse gas emissions in adherence to international standards. ${fullData.primaryDriver} has been identified as the significant emission source over the reporting period.`;
    if (isComparison && compData) {
      const diff = fullData.totalEmissions - compData.totalEmissions;
      const pct =
        compData.totalEmissions > 0
          ? ((diff / compData.totalEmissions) * 100).toFixed(1)
          : 0;
      narrative += ` Year-over-year performance shows a ${diff < 0 ? "decrease" : "increase"} of ${Math.abs(pct)}% (${Math.abs(diff).toFixed(0)} tCO2e).`;
    }
    curY = addTextBlock(narrative, curY);

    // Cards
    curY += 15;
    const summTileW = (pageWidth - margin * 2 - 15) / 3;
    // Tile 1 Methane
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(margin, curY, summTileW, 30, 2, 2, "F");
    doc.setFontSize(8);
    doc.setTextColor(...THEME.textMuted);
    doc.text("METHANE (CH4)", margin + 5, curY + 10);
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.text(`${fullData.ch4Total.toFixed(1)} t`, margin + 5, curY + 22);

    // Tile 2 Primary
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(margin + summTileW + 5, curY, summTileW, 30, 2, 2, "F");
    doc.setFontSize(8);
    doc.setTextColor(...THEME.textMuted);
    doc.text("PRIMARY DRIVER", margin + summTileW + 10, curY + 10);
    doc.setFontSize(14);
    doc.setTextColor(...THEME.text);
    doc.text(`${fullData.primaryDriver}`, margin + summTileW + 10, curY + 22);

    // Tile 3 Target
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(
      margin + summTileW * 2 + 10,
      curY,
      summTileW,
      30,
      2,
      2,
      "F",
    );
    doc.setFontSize(8);
    doc.setTextColor(...THEME.textMuted);
    doc.text("TARGET STATUS", margin + summTileW * 2 + 15, curY + 10);
    const statusText = specificGoal
      ? fullData.totalEmissions <= specificGoal.target_amount
        ? "ON TRACK"
        : "AT RISK"
      : "NO TARGET";
    doc.setFontSize(14);
    doc.setTextColor(
      statusText === "ON TRACK" ? 16 : 239,
      statusText === "ON TRACK" ? 185 : 68,
      statusText === "ON TRACK" ? 129 : 68,
    );
    doc.text(statusText, margin + summTileW * 2 + 15, curY + 22);

    drawFooter();

    /**
     * =========================================================
     * PAGE 4: COMPANY PROFILE
     * =========================================================
     */
    if (profileImg) {
      doc.addPage();
      drawBackground();
      let curY = 30;

      doc.setFontSize(24);
      doc.setTextColor(...THEME.dark);
      doc.setFont("helvetica", "bold");
      doc.text("ABOUT SONATRACH", margin, curY);
      doc.setDrawColor(...THEME.accent);
      doc.setLineWidth(1);
      doc.line(margin, curY + 4, margin + 80, curY + 4);

      curY += 20;

      const profileW = 80;
      const profileH = 80;
      doc.addImage(profileImg, "JPEG", margin, curY, profileW, profileH);

      const textX = margin + profileW + 15;
      const textW = pageWidth - margin - textX;

      doc.setFontSize(11);
      doc.setTextColor(...THEME.text);
      doc.setFont("helvetica", "normal");

      const companyDesc = `Sonatrach is the national state-owned oil company of Algeria. Founded in 1963, it is known today as the largest company in Africa with 154 subsidiaries, and often referred to as the first African major. In 2021, Sonatrach was the seventh largest gas company in the world.

As a major global player, we are integrating sustainability into every aspect of our value chain. Our strategy prioritizes significant greenhouse gas (GHG) emission reductions, methane abatement, and energy efficiency.`;
      
      const splitDesc = doc.splitTextToSize(companyDesc, textW);
      doc.text(splitDesc, textX, curY + 5);

      drawFooter();
    }

    /**
     * =========================================================
     * CHAPTER 1: GENERAL DESCRIPTION
     * =========================================================
     */
    doc.addPage();
    drawBackground();
    curY = 30;
    
    doc.setFontSize(16);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("1. GENERAL DESCRIPTION", margin, curY);
    doc.setDrawColor(200, 200, 200);
    doc.setLineWidth(0.5);
    doc.line(margin, curY + 4, pageWidth - margin, curY + 4);
    curY += 15;

    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Description of the Reporting Organization", margin, curY);
    curY += 6;
    curY = addTextBlock("Sonatrach is committed to leading the low-carbon energy transition. As a major global player, we are integrating sustainability into every aspect of our value chain. Our strategy prioritizes significant greenhouse gas (GHG) emission reductions, methane abatement, and energy efficiency.", curY);

    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Person or Entity Responsible for the Report", margin, curY);
    curY += 6;
    let personText = "Logged In User";
    if (typeof personResponsible === 'object') {
        personText = `Name: ${personResponsible.fullName || personResponsible.user_name || "N/A"}
Job Title: ${personResponsible.jobTitle || "N/A"}
Department: ${personResponsible.department || "N/A"}
Email: ${personResponsible.email || "N/A"}`;
    } else {
        personText = personResponsible;
    }
    curY = addTextBlock(personText, curY);
    
    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Reporting Period", margin, curY);
    curY += 6;
    curY = addTextBlock(`The reporting period is for the year ${selectedYear}.`, curY);

    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("GWP Values Used", margin, curY);
    curY += 6;
    curY = addTextBlock(`The Global Warming Potential (GWP) values used in the calculations are sourced from: IPCC AR5.`, curY);

    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Verification Status & Statement of Compliance", margin, curY);
    curY += 6;
    curY = addTextBlock(`Verification Status: ${verificationStatus}\nStatement of Compliance: This GHG report has been prepared in accordance with the ISO 14064-1:2018 standard.`, curY);
    
    drawFooter();

    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Principles of the MRV System", margin, curY);
    curY += 6;
    curY = addTextBlock("This inventory adheres to the core MRV principles (TECCI):\n- Transparency: Assumptions and methodologies are clearly explained.\n- Accuracy: Emissions are estimated precisely, minimizing systematic biases.\n- Consistency: Methodologies are consistent across reporting years.\n- Comparability: Results are structured to allow comparison with other entities.\n- Completeness: All relevant emission sources, sinks, and greenhouse gases within the defined boundaries are included.", curY);
    
    /**
     * =========================================================
     * CHAPTER 2: ORGANIZATIONAL BOUNDARIES
     * =========================================================
     */
    curY = addSectionHeader(2, "ORGANIZATIONAL BOUNDARIES", null, true);
    
    const uniqueBoundaries = [...new Set(reportFacilities.map(f => f.boundary_type || "Operational Control"))].join(" and ");
    
    curY = addTextBlock(`The consolidation approach used for organizational boundaries is: ${uniqueBoundaries}.`, curY);
    curY += 5;
    curY = addTextBlock(`This inventory includes ${reportFacilities.length} facilities within the specified boundaries:`, curY);
    
    // Explicitly list the facilities
    const facilityList = reportFacilities.map(f => `- ${f.name}`).join("\n");
    curY = addTextBlock(facilityList, curY);
    
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 3: REPORTING BOUNDARIES
     * =========================================================
     */
    curY = addSectionHeader(3, "REPORTING BOUNDARIES", null, true);

    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Emission Categories Evaluated", margin, curY);
    curY += 6;
    curY = addTextBlock("In compliance with ISO 14064-1:2018, emissions are categorized as follows:\n- Category 1: Direct GHG emissions and removals\n- Category 2: Indirect GHG emissions from imported energy\n- Categories 3-6: Other indirect GHG emissions", curY);

    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Exclusion Criteria", margin, curY);
    curY += 6;
    curY = addTextBlock(`The criteria for significant emissions and exclusions are defined as:\n${exclusionCriteria}`, curY);
    
    if (exclusionsData.length > 0) {
        curY = checkPageBreak(curY, 50);
    curY += 5;
        doc.setFontSize(14);
        doc.setTextColor(...THEME.accent);
        doc.setFont("helvetica", "bold");
        doc.text("Specific Exclusions", margin, curY);
        curY += 6;
        const exclText = exclusionsData.map(e => `- ${e.source_name}: ${e.justification}`).join("\n");
        curY = addTextBlock(exclText, curY);
    }

    drawFooter();

    /**
     * =========================================================
     * CHAPTER 4: QUANTIFIED GHG INVENTORY
     * =========================================================
     */
    curY = addSectionHeader(4, "QUANTIFIED GHG INVENTORY", null, true);
    
    // Emissions by Category (Table)
    doc.setFontSize(12);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Consolidated Emissions by Category", margin, curY);
    curY += 5;
    
    autoTable(doc, {
        startY: curY,
        head: [["Category (ISO 14064-1:2018)", "Emissions (tCO2e)"]],
        body: [
            ["Category 1: Direct GHG emissions", fullData.scope1Total.toFixed(2)],
            ["Category 2: Indirect emissions from imported energy", fullData.scope2Total.toFixed(2)],
            ["Categories 3-6: Other indirect GHG emissions", fullData.scope3Total.toFixed(2)],
            [{ content: "Total GHG Emissions", styles: { fontStyle: 'bold' } }, { content: fullData.totalEmissions.toFixed(2), styles: { fontStyle: 'bold' } }]
        ],
        ...cleanTableTheme,
        margin: { left: margin, right: margin }
    });
    curY = doc.lastAutoTable.finalY + 10;
    
    // Breakdown of Direct Emissions
    if (curY > pageHeight - 60) {
        doc.addPage();
        drawBackground();
        drawFooter();
        curY = 30;
    }
    
    doc.setFontSize(12);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Breakdown of Direct GHG Emissions (Category 1)", margin, curY);
    curY += 5;
    
    autoTable(doc, {
        startY: curY,
        head: [["Greenhouse Gas", "Emissions (tCO2e)"]],
        body: [
            ["Carbon Dioxide (CO2)", fullData.co2Total.toFixed(2)],
            ["Methane (CH4)", fullData.ch4Total.toFixed(2)],
            ["Nitrous Oxide (N2O)", fullData.n2oTotal.toFixed(2)]
        ],
        ...cleanTableTheme,
        margin: { left: margin, right: margin }
    });
    curY = doc.lastAutoTable.finalY + 10;
    
    // Breakdown by Process Type
    if (curY > pageHeight - 60) {
        doc.addPage();
        drawBackground();
        drawFooter();
        curY = 30;
    }
    doc.setFontSize(12);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Breakdown of Emissions by Process Type", margin, curY);
    curY += 5;
    
    const processBody = Object.entries(fullData.processBreakdown)
        .map(([process, val]) => [process, val.toFixed(2)])
        .sort((a, b) => parseFloat(b[1]) - parseFloat(a[1]));
        
    if (processBody.length > 0) {
        autoTable(doc, {
            startY: curY,
            head: [["Process Type", "Emissions (tCO2e)"]],
            body: processBody,
            ...cleanTableTheme,
            margin: { left: margin, right: margin }
        });
        curY = doc.lastAutoTable.finalY + 10;
    } else {
        curY = addTextBlock("No specific process type data available.", curY);
    }

    // Breakdown by Facility
    if (curY > pageHeight - 60) {
        doc.addPage();
        drawBackground();
        drawFooter();
        curY = 30;
    }
    doc.setFontSize(12);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Emissions Breakdown by Facility", margin, curY);
    curY += 5;
    
    const facilityBody = Object.entries(fullData.facilityBreakdown || {})
        .map(([fac, val]) => [fac, val.toFixed(2)])
        .sort((a, b) => parseFloat(b[1]) - parseFloat(a[1]));
        
    if (facilityBody.length > 0) {
        autoTable(doc, {
            startY: curY,
            head: [["Operational Unit / Facility", "Total Emissions (tCO2e)"]],
            body: facilityBody,
            ...cleanTableTheme,
            margin: { left: margin, right: margin }
        });
        curY = doc.lastAutoTable.finalY + 10;
    } else {
        curY = addTextBlock("No facility breakdown data available.", curY);
    }
    
    // Base Year
    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(12);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Historical Base Year & Targets", margin, curY);
    curY += 6;
    if (baseYearData || specificGoal) {
        let baseYearText = baseYearData 
            ? `The historical base year is ${baseYearData.year}. Base year emissions: ${baseYearData.emissions} tCO2e.` 
            : "No specific base year data is configured.";
        if (baseYearData && baseYearData.reason) {
            baseYearText += `\nReason for base year selection/change: ${baseYearData.reason}`;
        }
        
        let goalText = specificGoal
            ? `Emission Goal: ${specificGoal.title} (Target: ${specificGoal.target_amount} tCO2e by ${specificGoal.target_year})`
            : "No specific emission reduction goals apply for this reporting period.";
            
        curY = addTextBlock(`${baseYearText}\n\n${goalText}`, curY);
    } else {
        curY = addTextBlock("No specific base year data or goals were found for this report.", curY);
    }
    
    // Quantification and Emission Factors
    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(12);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Quantification Approaches & Emission Factors", margin, curY);
    curY += 6;
    
    let usedTier1 = false;
    let usedTier3 = false;
    reportData.forEach(r => {
        const fType = (r.factor_type || "").toLowerCase();
        if (fType.includes("tier 3") || fType.includes("measurement") || fType.includes("engineering")) usedTier3 = true;
        if (fType.includes("tier 1") || fType.includes("default")) usedTier1 = true;
    });
    
    let approachText = "Emissions were quantified using activity data multiplied by appropriate emission factors. Emission factors are primarily sourced from the EPA, API Compendium, and IPCC guidelines.";
    if (usedTier3) {
        approachText += "\n- Tier 3 Approaches (site-specific data or direct measurement) were used for some high-impact or accessible emission sources, providing greater precision.";
    }
    if (usedTier1) {
        approachText += "\n- Tier 1 Approaches (default industry emission factors) were applied where site-specific data was unavailable or for minor emission sources.";
    }
    
    curY = addTextBlock(approachText, curY);

    // Uncertainty Assessment Table
    if (uncertaintyData && uncertaintyData.category_breakdown) {
        if (curY > pageHeight - 80) {
            doc.addPage();
            drawBackground();
            drawFooter();
            curY = 30;
        }
        curY = checkPageBreak(curY, 50);
    curY += 5;
        doc.setFontSize(12);
        doc.setTextColor(...THEME.accent);
        doc.setFont("helvetica", "bold");
        doc.text("Uncertainty Assessment", margin, curY);
        curY += 6;
        curY = addTextBlock(`The overall uncertainty of the inventory has been assessed at ±${uncertaintyData.overall_uncertainty_pct}%. The breakdown by category is detailed below:`, curY);
        
        const uncertBody = uncertaintyData.category_breakdown.map(cat => [
            cat.category || "-",
            cat.total_emissions ? cat.total_emissions.toFixed(2) : "0.00",
            cat.uncertainty_pct || "-"
        ]);
        
        autoTable(doc, {
            startY: curY,
            head: [["Category", "Total Emissions (tCO2e)", "Uncertainty (±%)"]],
            body: uncertBody,
            ...cleanTableTheme,
            margin: { left: margin, right: margin }
        });
        curY = doc.lastAutoTable.finalY + 10;
    }
    
    if (charts.scopeChart || charts.trendChart) {
      if (curY > pageHeight - 80) {
          doc.addPage();
          drawBackground();
          drawFooter();
          curY = 30;
      }
      doc.setFontSize(14);
      doc.setTextColor(...THEME.accent);
      doc.setFont("helvetica", "bold");
      doc.text("Emission Breakdown Charts", margin, curY);
      curY += 10;
      
      const chartW = (pageWidth - margin * 2 - 10) / 2;
      
      // KPIs
      doc.setFontSize(11);
      doc.setTextColor(...THEME.text);
      doc.text("Key Performance Indicators:", margin, curY);
      curY += 6;
      doc.setFontSize(10);
      doc.text(`Total Emissions: ${fullData.totalEmissions.toFixed(2)} tCO2e`, margin, curY);
      doc.text(`Carbon Intensity: ${fullData.intensityMetrics ? fullData.intensityMetrics.avgCo2 : 'N/A'}`, margin + chartW, curY);
      curY += 5;
      doc.text(`Methane Emissions: ${fullData.ch4Total.toFixed(2)} tCH4`, margin, curY);
      doc.text(`Methane Intensity: ${fullData.intensityMetrics ? fullData.intensityMetrics.avgCh4 : 'N/A'}`, margin + chartW, curY);
      curY += 10;
      
      curY = checkPageBreak(curY, 150);

      // Row 1: Scope Split and Source Breakdown (Pies)
      if (charts.scopeChart) doc.addImage(charts.scopeChart, "PNG", margin, curY, chartW, 60);
      if (charts.sourceChart) doc.addImage(charts.sourceChart, "PNG", margin + chartW + 10, curY, chartW, 60);
      curY += 70;
      
      // Row 2: Trend Chart and Comparison Chart
      if (charts.trendChart) doc.addImage(charts.trendChart, "PNG", margin, curY, chartW, 60);
      if (charts.comparisonChart) {
         doc.addImage(charts.comparisonChart, "PNG", margin + chartW + 10, curY, chartW, 60);
      }
      curY += 70;
    }

    drawFooter();

    /**
     * =========================================================
     * CHAPTER 5: GHG REDUCTION INITIATIVES
     * =========================================================
     */
    curY = addSectionHeader(5, "GHG REDUCTION INITIATIVES", null, true);
    
    if (mitigationData.length > 0) {
        curY = addTextBlock(`There are ${mitigationData.length} GHG reduction initiatives documented for this inventory.`, curY);
        curY += 5;
        
        const projBody = mitigationData.map(p => [
            p.title || "-",
            p.status || "-",
            p.estimated_reduction ? p.estimated_reduction.toFixed(2) : "0.00"
        ]);
        
        autoTable(doc, {
            startY: curY,
            head: [["Project Title", "Status", "Estimated Reduction (tCO2e)"]],
            body: projBody,
            ...cleanTableTheme,
            margin: { left: margin, right: margin }
        });
        curY = doc.lastAutoTable.finalY + 10;
    } else {
        curY = addTextBlock("No specific GHG reduction initiatives were recorded for this period.", curY);
    }
    
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 6: QUALITY ASSURANCE & QUALITY CONTROL (QA/QC)
     * =========================================================
     */
    curY = addSectionHeader(6, "QUALITY ASSURANCE & QUALITY CONTROL", null, true);
    
    curY = addTextBlock("To ensure the integrity of this inventory, a comprehensive Quality Assurance (QA) and Quality Control (QC) process is implemented in accordance with ISO 14064-1.", curY);
    
    curY = checkPageBreak(curY, 50);
    curY += 5;
    doc.setFontSize(14);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Verification Checklist", margin, curY);
    curY += 6;
    curY = addTextBlock("The following routine checks are performed as part of the QC procedures:", curY);
    
    const qcBody = [
        ["Data Collection & Input", "Verify sample of input data for transcription errors."],
        ["Methodology Consistency", "Ensure calculation methods remain consistent across time series."],
        ["Trend Analysis", "Identify and examine any unexplained or unusual trends in activity data."],
        ["Uncertainty Control", "Examine unexplained deviations and outlier emission factors."],
        ["Reporting Completeness", "Verify that the final report encompasses all relevant emission sources."]
    ];
    
    autoTable(doc, {
        startY: curY,
        head: [["QC Category", "Verification Action"]],
        body: qcBody,
        ...cleanTableTheme,
        margin: { left: margin, right: margin }
    });
    curY = doc.lastAutoTable.finalY + 10;
    
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 7: REGULATORY FRAMEWORK & REFERENCES
     * =========================================================
     */
    curY = addSectionHeader(7, "REGULATORY FRAMEWORK & REFERENCES", null, true);
    
    curY = addTextBlock("This greenhouse gas inventory was compiled in compliance with both national regulations and international conventions. The primary standards and references utilized include:", curY);
    
    const refBody = [
        ["ISO 14064-1:2018", "Principles and requirements for designing, developing, and reporting GHG inventories."],
        ["API Compendium 2021", "Calculation methodologies and emission factors specific to the oil and gas industry."],
        ["IPCC 2006", "Methodologies for estimating national anthropogenic emissions."],
        ["National Law 05-07", "Algerian law on hydrocarbons (and subsequent amendments)."],
        ["UNFCCC / Paris Agreement", "International framework conventions on climate change."]
    ];
    
    autoTable(doc, {
        startY: curY,
        head: [["Reference / Standard", "Description / Scope"]],
        body: refBody,
        ...cleanTableTheme,
        margin: { left: margin, right: margin }
    });
    curY = doc.lastAutoTable.finalY + 10;
    
    drawFooter();

    /**
     * =========================================================
     * APPENDIX — ALL RECORDS, NO LIMIT
     * =========================================================
     */
    doc.addPage("a4", "l");
    drawBackground();
    doc.setFontSize(18);
    doc.setTextColor(...THEME.accent);
    doc.text("Annex A: Detailed Emissions Data", 20, 20);
    doc.setFontSize(9);
    doc.setTextColor(...THEME.textMuted);
    doc.text(
      `Total records: ${fullData.scope1Rows.length} | Year: ${selectedYear} | All Scopes`,
      20,
      28,
    );

    // Export ALL rows — jsPDF-autotable paginates automatically
    autoTable(doc, {
      startY: 33,
      head: [
        [
          "Date",
          "Facility",
          "Scope",
          "Process / Category",
          "Fuel / Source",
          "Qty",
          "Unit",
          "CO₂ (t)",
          "CH₄ (t)",
          "tCO₂e",
        ],
      ],
      body: fullData.scope1Rows.map((r) => [
        r[1], // date
        r[0] ? String(r[0]).split("_")[0] : "-", // id/equip (trimmed)
        r[12] || "1", // scope
        r[2], // process_type
        r[3], // fuel/source
        Number(r[4] || 0).toLocaleString(undefined, {
          maximumFractionDigits: 2,
        }), // qty
        r[11], // unit
        r[5], // CO2
        r[6], // CH4
        r[7], // tCO2e
      ]),
      ...cleanTableTheme,
      styles: { fontSize: 7, cellPadding: 1.5 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 7.5 },
      // Let autoTable handle page breaks automatically
      didDrawPage: (hookData) => {
        // Re-draw footer on each continuation page
        drawFooter(hookData.pageNumber);
      },
    });

    const filename = `Sonatrach_GHG_Report_${selectedYear}_Full.pdf`;
    const pdfBlob = doc.output("blob");
    const pdfBlobWithMime = new Blob([pdfBlob], { type: "application/pdf" });
    const url = window.URL.createObjectURL(pdfBlobWithMime);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();

    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    }, 1000);
  } catch (err) {
    console.error("PDF Generation Error", err);
    throw err;
  }
}

// --- DATA FETCHING (Unchanged logic, just ensure robustness) ---
async function fetchAllReportData(
  api,
  year,
  rawReportData,
  params,
  productionData = [],
) {
  // ... (Keep existing data processing logic from previous step, it was solid)
  let co2Total = 0,
    ch4Total = 0,
    n2oTotal = 0;
  let scope1Total = 0,
    scope2Total = 0,
    scope3Total = 0;
  let processBreakdown = {
    Combustion: 0,
    Flaring: 0,
    Venting: 0,
    Fugitive: 0,
    Other: 0,
  };
  let facilityBreakdown = {};
  let monthlyData = {};

  const scope1Rows = rawReportData.map((r) => {
    const tVal = r.co2e_total || 0;
    let scope = String(r.scope || "");
    if (!scope || scope === "null" || scope === "undefined") {
      const pType = (r.process_type || "").toLowerCase();
      if (pType.includes("electricity") || pType.includes("purchased"))
        scope = "2";
      else if (
        pType.includes("transport") ||
        pType.includes("sold") ||
        pType.includes("travel")
      )
        scope = "3";
      else scope = "1";
    }

    if (
      (r.co2_emissions || 0) === 0 &&
      (r.ch4_emissions || 0) === 0 &&
      (r.n2o_emissions || 0) === 0 &&
      tVal > 0
    ) {
      co2Total += tVal;
    } else {
      co2Total += r.co2_emissions || 0;
      ch4Total += r.ch4_emissions || 0;
      n2oTotal += r.n2o_emissions || 0;
    }

    const fName = r.facility_name || "Unknown Facility";
    if (!facilityBreakdown[fName]) facilityBreakdown[fName] = 0;
    facilityBreakdown[fName] += tVal;

    let recMonth = r.month;
    if (!recMonth && r.date) {
      const d = new Date(r.date);
      if (!isNaN(d)) recMonth = d.getMonth() + 1;
    }
    if (recMonth) {
      if (!monthlyData[recMonth]) monthlyData[recMonth] = 0;
      monthlyData[recMonth] += tVal;
    }

    if (scope === "2") scope2Total += tVal;
    else if (scope === "3") scope3Total += tVal;
    else scope1Total += tVal;

    const pType = (r.process_type || "").toLowerCase();
    let procCat = "Other";
    if (scope === "1") {
      if (pType.includes("combustion") || pType.includes("fuel"))
        procCat = "Combustion";
      else if (pType.includes("flare") || pType.includes("flaring"))
        procCat = "Flaring";
      else if (pType.includes("vent") || pType.includes("venting"))
        procCat = "Venting";
      else if (pType.includes("fugitive") || pType.includes("leak"))
        procCat = "Fugitive";
    }

    if (!processBreakdown[procCat]) processBreakdown[procCat] = 0;
    processBreakdown[procCat] += tVal;

    let efCo2 = r.ef_used_co2 || 0;
    let efCh4 = r.ef_used_ch4 || 0;
    let efN2o = r.ef_used_n2o || 0;

    if (efCo2 === 0 && r.quantity > 0 && r.co2_emissions > 0)
      efCo2 = r.co2_emissions / r.quantity;
    if (efCh4 === 0 && r.quantity > 0 && r.ch4_emissions > 0)
      efCh4 = r.ch4_emissions / r.quantity;
    if (efN2o === 0 && r.quantity > 0 && r.n2o_emissions > 0)
      efN2o = r.n2o_emissions / r.quantity;

    const dateStr = r.date || r.timestamp;
    const dateObj = dateStr ? new Date(dateStr) : null;
    const dateDisplay =
      dateObj && !isNaN(dateObj)
        ? dateObj.toLocaleDateString()
        : `${r.year || "?"}/${r.month || "?"}`;

    // Determine scope label per record for Annex table column (index 12)
    // Use the already-computed per-record `scope` variable (not the filter param)
    const scopeLabel = scope; // `scope` here is the per-record string: '1', '2', or '3'

    return [
      r.equipment_id || r.id, // [0] id
      dateDisplay, // [1] date
      r.process_type || "-", // [2] process
      r.fuel_type || r.fuel || "-", // [3] fuel
      r.quantity || r.amount || 0, // [4] qty
      Number(r.co2_emissions || 0).toFixed(2), // [5] co2
      Number(r.ch4_emissions || 0).toFixed(2), // [6] ch4
      Number(tVal).toFixed(2), // [7] tco2e
      efCo2,
      efCh4,
      efN2o, // [8][9][10] EFs
      r.unit || "-", // [11] unit
      scopeLabel, // [12] scope (NEW)
      r.facility_name || "-", // [13] facility (NEW)
    ];
  });

  let intensityMetrics = { avgCo2: "N/A", avgCh4: "N/A", totalProd: "0" };
  if (productionData.length > 0) {
    let weightedCo2Sum = 0,
      weightedCh4Sum = 0,
      totalBoeSum = 0;
    productionData.forEach((d) => {
      const boe = d.total_boe || 0;
      if (boe > 0) {
        weightedCo2Sum += d.co2_intensity * boe; // co2_intensity already in kg/BOE
        weightedCh4Sum += d.ch4_intensity * boe; // ch4_intensity already in kg/BOE (was erroneously * 1000)
        totalBoeSum += boe;
      }
    });
    intensityMetrics = {
      avgCo2: totalBoeSum > 0 ? (weightedCo2Sum / totalBoeSum).toFixed(4) : "0",
      avgCh4: totalBoeSum > 0 ? (weightedCh4Sum / totalBoeSum).toFixed(4) : "0",
      totalProd: totalBoeSum.toLocaleString(undefined, {
        maximumFractionDigits: 0,
      }),
    };
  }

  let primaryDriver = "Combustion";
  if (Object.keys(processBreakdown).length > 0) {
    const maxVal = Math.max(...Object.values(processBreakdown));
    const maxKey = Object.keys(processBreakdown).find(
      (k) => processBreakdown[k] === maxVal,
    );
    if (maxKey) primaryDriver = maxKey;
  }

  const totalEmissions = scope1Total + scope2Total + scope3Total;

  return {
    scope1Rows,
    co2Total,
    ch4Total,
    n2oTotal,
    scope1Total,
    scope2Total,
    scope3Total,
    processBreakdown,
    facilityBreakdown,
    intensityMetrics,
    monthlyData,
    totalScale: totalEmissions.toLocaleString(undefined, {
      maximumFractionDigits: 2,
    }),
    totalEmissions,
    primaryDriver,
    year,
  };
}

async function generateReportCharts(
  data,
  compData = null,
  isComparison = false,
) {
  // Reduced resolution to prevent massive PDF sizes
  let comparisonChart = null;
  if (isComparison && compData) {
    comparisonChart = await createChartImage(
      "bar",
      {
        labels: ["Scope 1", "Scope 2", "Scope 3"],
        datasets: [
          {
            label: `${data.year} (Current)`,
            data: [data.scope1Total, data.scope2Total, data.scope3Total],
            backgroundColor: toRgba(THEME.chart.blue),
            borderRadius: 4,
          },
          {
            label: `${compData.year} (Previous)`,
            data: [
              compData.scope1Total,
              compData.scope2Total,
              compData.scope3Total,
            ],
            backgroundColor: toRgba(THEME.chart.slate, 0.5),
            borderRadius: 4,
          },
        ],
      },
      600,
      400,
    );
  }

  const scopeSplit = await createChartImage(
    "doughnut",
    {
      labels: ["Scope 1", "Scope 2", "Scope 3"],
      datasets: [
        {
          data: [data.scope1Total, data.scope2Total, data.scope3Total],
          backgroundColor: [
            toRgba(THEME.chart.orange),
            toRgba(THEME.chart.indigo),
            toRgba(THEME.chart.teal),
          ],
          borderWidth: 0,
        },
      ],
    },
    600,
    400,
  );

  const sourceBreakdown = await createChartImage(
    "bar",
    {
      labels: Object.keys(data.processBreakdown),
      datasets: [
        {
          label: "tCO2e",
          data: Object.values(data.processBreakdown),
          backgroundColor: [
            toRgba(THEME.chart.indigo),
            toRgba(THEME.chart.orange),
            toRgba(THEME.chart.teal),
            toRgba(THEME.chart.amber),
            toRgba(THEME.chart.slate),
          ],
          borderRadius: 8, // Nicer rounded bars
        },
      ],
    },
    600,
    400,
  );

  // NEW: Trend Chart
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const trendData = months.map((_, i) => data.monthlyData[i + 1] || 0);

  const trendChart = await createChartImage(
    "line",
    {
      labels: months,
      datasets: [
        {
          label: "Monthly Emissions (tCO2e)",
          data: trendData,
          borderColor: toRgba(THEME.chart.orange),
          backgroundColor: "rgba(255, 107, 0, 0.1)",
          fill: true,
          tension: 0.4,
        },
      ],
    },
    600,
    300,
  );

  return { scopeSplit, sourceBreakdown, comparisonChart, trendChart };
}

function createChartImage(type, data, width = 600, height = 400) {
  return new Promise((resolve) => {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.style.display = "none";
    document.body.appendChild(canvas);

    // WHITE BACKGROUND PLUGIN — JPEG doesn't support transparency;
    // without this, transparent areas render as black in the exported PDF.
    const whiteBgPlugin = {
      id: "whiteBg",
      beforeDraw(chart) {
        const c = chart.canvas.getContext("2d");
        c.save();
        c.globalCompositeOperation = "destination-over";
        c.fillStyle = "#ffffff";
        c.fillRect(0, 0, chart.canvas.width, chart.canvas.height);
        c.restore();
      },
    };

    const ctx = canvas.getContext("2d");
    const chart = new Chart(ctx, {
      type: type,
      data: data,
      plugins: [whiteBgPlugin],
      options: {
        animation: false,
        responsive: false,
        devicePixelRatio: 1.5,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              font: { size: 14 },
              color: "#1e293b", // dark text on white bg
            },
          },
          tooltip: { enabled: false },
        },
        scales:
          type !== "doughnut" && type !== "pie"
            ? {
                y: {
                  ticks: { font: { size: 12 }, color: "#475569" },
                  grid: { color: "#e2e8f0" },
                },
                x: {
                  ticks: { font: { size: 12 }, color: "#475569" },
                  grid: { color: "#e2e8f0" },
                },
              }
            : {},
      },
    });

    setTimeout(() => {
      const imgData = canvas.toDataURL("image/jpeg", 0.9);
      chart.destroy();
      document.body.removeChild(canvas);
      resolve(imgData);
    }, 400);
  });
}
