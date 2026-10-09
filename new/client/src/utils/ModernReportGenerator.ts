import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { DEFAULT_GWP, getActiveGwpFactors, GWP_STANDARDS } from "../constants";


export function resolveGwpFactors(gwpChoice?: string) {
  const str = String(gwpChoice || "AR5").toUpperCase().trim();
  let standard = "AR5";
  let horizon = "100";
  if (str.includes("AR4")) standard = "AR4";
  else if (str.includes("AR6")) standard = "AR6";
  else standard = "AR5";

  if (str.includes("20")) horizon = "20";
  const factors = getActiveGwpFactors(standard, horizon);
  return {
    standard,
    horizon,
    factors,
    label: `IPCC ${standard} (${horizon}-yr: CH4=${factors.CH4}, N2O=${factors.N2O})`
  };
}

// Sonatrach Brand Colors (White Theme)
type RGB = [number, number, number];

interface ThemeDef {
  primary: RGB;
  secondary: RGB;
  accent: RGB;
  dark: RGB;
  text: RGB;
  textMuted: RGB;
  gold: RGB;
  chart: Record<string, RGB>;
}

const THEME: ThemeDef = {
  primary: [255, 255, 255],
  secondary: [248, 250, 252],
  accent: [255, 107, 0],
  dark: [15, 23, 42],
  text: [30, 41, 59],
  textMuted: [100, 116, 139],
  gold: [218, 165, 32],
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

// --- HELPER: Load Image with Timeout ---
function loadImage(url: string): Promise<string | null> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), 3000);
    const img = new Image();
    img.crossOrigin = "Anonymous";
    img.onload = () => {
      clearTimeout(timer);
      try {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        if (ctx) ctx.drawImage(img, 0, 0);
        resolve(canvas.toDataURL("image/jpeg"));
      } catch {
        resolve(null);
      }
    };
    img.onerror = () => {
      clearTimeout(timer);
      resolve(null);
    };
    img.src = url;
  });
}

export async function generateModernPDF(api: any, filters: any): Promise<void> {
  const { year, scope, regionId, processType, comparisonYear, exclusionCriteria = 'None provided', verificationStatus = 'Not externally verified', personResponsible = 'Logged In User', gwpStandard: requestedGwp } = filters;
  // BUG-077: a missing year means ALL years; never relabel it as the current fiscal year
  const isAllYears = !year || year === "all";
  const selectedYear = isAllYears ? "All years" : year;
  const isComparison = comparisonYear && comparisonYear !== "none";

  // 1. Comprehensive Data Fetching
  // NOTE: When regionId is an array (multi-select), do NOT send facility_id param —
  // fetch all data then filter client-side (the API only accepts a single facility_id).
  const params = {
    limit: 5000, // Hard cap client-side; use /api/reports/export for full dataset
    status: "Verified", // BUG-077: the inventory counts approved records only
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

  const targetFacilityId =
    regionId && regionId !== "all" && !Array.isArray(regionId)
      ? regionId
      : Array.isArray(regionId) && regionId.length === 1
        ? regionId[0]
        : undefined;

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
      exclusionsRes,
      settingsRes,
      profileImg,
      flaringRes,
      granularIntensitiesRes,
      capComplianceRes,
      capEmissionsRes,
      equityAllocRes,
      allProdRes,
    ] = await Promise.all([
      api.get("/emissions", { params }),
      api.get("/facilities").catch(() => ({ data: [] })),
      api
        .get("/dashboard/mitigation", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facilityId: targetFacilityId }),
          },
        })
        .catch(() => ({ data: [] })),
      api
        .get("/dashboard/intensity-stats", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facilityId: targetFacilityId }),
          },
        })
        .catch(() => ({ data: [] })),
      api
        .get(`/dashboard/goals/${subFetchYear || new Date().getFullYear()}`)
        .catch(() => ({ data: null })),
      api
        .get("/dashboard/exclusions", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facilityId: targetFacilityId }),
          },
        })
        .catch(() => ({ data: [] })),
      api.get("/auth/settings").catch(() => ({ data: { gwp_standard: 'IPCC AR5' } })),
      loadImage("/company_profile.jpg").catch(() => null),
      api
        .get("/dashboard/flaring-summary", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facilityId: targetFacilityId }),
          },
        })
        .catch(() => ({ data: null })),
      api
        .get("/dashboard/granular-intensities", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facilityId: targetFacilityId }),
          },
        })
        .catch(() => ({ data: null })),
      api
        .get("/cap/compliance", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facility_id: targetFacilityId }),
          },
        })
        .catch(() => ({ data: [] })),
      api
        .get("/cap/emissions", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facility_id: targetFacilityId }),
          },
        })
        .catch(() => ({ data: [] })),
      api
        .get("/equity/allocation", {
          params: {
            year: subFetchYear,
            ...(targetFacilityId && { facility_id: targetFacilityId }),
          },
        })
        .catch(() => ({ data: [] })),
      api.get("/data/production").catch(() => ({ data: [] })),
    ]);

    const flaringSummary = flaringRes?.data || null;
    const granularIntensities = granularIntensitiesRes?.data || null;
    const capCompliance = Array.isArray(capComplianceRes?.data) ? capComplianceRes.data : [];
    const capEmissions = Array.isArray(capEmissionsRes?.data) ? capEmissionsRes.data : [];
    const equityAllocations = Array.isArray(equityAllocRes?.data) ? equityAllocRes.data : [];
    // the production tables cover the facilities the report covers (they printed company-wide
    // production beside one facility's emissions)
    const reportFacilityIds = Array.isArray(regionId)
      ? (regionId.length ? regionId.map(String) : null)
      : regionId && regionId !== "all" ? [String(regionId)] : null;
    const allHistoricalProduction = (Array.isArray(allProdRes?.data?.data || allProdRes?.data)
      ? (allProdRes?.data?.data || allProdRes?.data)
      : []
    ).filter((p: any) => !reportFacilityIds || reportFacilityIds.includes(String(p.facilityId ?? p.facility_id)));

    let reportData: any[] =
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

    const allFacilities: any[] = facilitiesRes.data || [];
    const mitigationData: any[] = mitigationRes.data || [];
    const productionData: any[] = prodRes.data || [];
    const specificGoal: any = goalRes.data;
    const exclusionsData: any[] = exclusionsRes.data || [];
    const settingsData = settingsRes.data || { gwp_standard: 'IPCC AR5' };
    const activeGwpChoice = requestedGwp || settingsData.gwp_standard || 'AR5';
    const resolvedGwp = resolveGwpFactors(activeGwpChoice);
    // stored totals are on the system GWP set (recalculated when it changes), not the requested one
    const storedGwp = resolveGwpFactors(settingsData.gwp_standard || 'AR5');

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

    let reportFacilities: any[] = [];
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
      resolvedGwp.factors,
      storedGwp.factors,
    );

    // Comparison Data
    let compData = null;
    if (isComparison) {
      const compParams = { ...params, year: comparisonYear };
      try {
        const cRes = await api.get("/emissions", { params: compParams });
        let cReportData = cRes.data.emissions || cRes.data || [];
        if (Array.isArray(regionId)) {
          cReportData = cReportData.filter((r: any) =>
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
          resolvedGwp.factors,
          storedGwp.factors,
        );
      } catch (e) {
        console.warn("Comparison Fetch Failed", e);
      }
    }

    // Initialize PDF
    const doc: any = new jsPDF("p", "mm", "a4");
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;

    // --- HELPERS ---
    function drawBackground() {
      doc.setFillColor(255, 255, 255);
      doc.rect(0, 0, pageWidth, pageHeight, "F");
    }

    function drawFooter(pageNumberOverride: number | null = null) {
      const pageNumber = pageNumberOverride || doc.internal.getNumberOfPages();
      doc.setFillColor(250, 250, 250);
      doc.rect(0, pageHeight - 15, pageWidth, 15, "F"); // Light footer bg
      doc.setFontSize(8);
      doc.setTextColor(...THEME.textMuted);
      doc.text(
        `Sonatrach GHG Inventory ${isAllYears ? "Historical" : selectedYear} | ISO 14064-1 Compliant`,
        margin,
        pageHeight - 6,
      );
      doc.text(`Page ${pageNumber}`, pageWidth - margin - 10, pageHeight - 6, {
        align: "right",
      });
    }

    function addSectionHeader(
      number: number | string,
      title: string,
      yOverride: number | null = null,
      newPage: boolean = false,
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

    function checkPageBreak(currentY: number, requiredSpace: number = 30): number {
      if (currentY + requiredSpace > pageHeight - margin) {
        doc.addPage();
        drawBackground();
        drawFooter();
        return 30; // New curY
      }
      return currentY;
    }

    function addTextBlock(text: string, y: number, fontSize: number = 10, color: RGB = THEME.text): number {
      doc.setFontSize(fontSize);
      doc.setTextColor(...color);
      doc.setFont("helvetica", "normal");
      const splitText = doc.splitTextToSize(text, pageWidth - margin * 2);
      y = checkPageBreak(y, splitText.length * 5 + 10);
      doc.text(splitText, margin, y);
      return y + splitText.length * 5 + 5;
    }

    // --- HELPER: Modern Table Styles ---
    const cleanTableTheme: any = {
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
      `${isAllYears ? "DATA" : selectedYear}`,
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
      `${isAllYears ? "All Historical Records" : "FISCAL YEAR " + selectedYear}`,
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
    doc.text("INTENSITY (kg CO2e/BOE)", 100, overlayY);
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

    addTextBlock(cautionText, cautionY, 11, THEME.text);

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

    let narrative = `The ${isAllYears ? "comprehensive" : selectedYear} GHG Inventory consolidates emissions from ${reportFacilities.length} facilities. Represents a precise accounting of direct and indirect greenhouse gas emissions in adherence to international standards. Total emissions are calculated in metric tonnes of CO2 equivalent (tCO2e) under ${resolvedGwp.label}. ${fullData.primaryDriver} has been identified as the significant emission source over the reporting period.`;
    if (isComparison && compData) {
      const diff = fullData.totalEmissions - compData.totalEmissions;
      const pct =
        compData.totalEmissions > 0
          ? Number(((diff / compData.totalEmissions) * 100).toFixed(1))
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

    curY += 38;
    doc.setFontSize(11);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("2030 Decarbonization Roadmap & Operational Milestones", margin, curY);
    curY += 5;

    // BUG-078: every statement is computed from the fetched data; nothing is a fixed claim
    const na = "n/a";
    const flareIntensityHl = flaringSummary?.flaring_intensity_pct;
    const execHighlights = [
      ["Scope 1 & 2 Emissions", `${(fullData.totalEmissions).toLocaleString(undefined, { maximumFractionDigits: 0 })} tCO2e`,
        `Verified Scope 1 + 2 for ${isAllYears ? "all years" : selectedYear}.`],
      ["Methane Emissions", `${fullData.ch4Total.toLocaleString(undefined, { maximumFractionDigits: 0 })} tCH4`,
        "Verified bottom-up methane for the period."],
      ["Operational Flaring Volume", flaringSummary?.total_flaring ? `${flaringSummary.total_flaring.volume_knm3.toLocaleString()} kNm3` : na,
        flareIntensityHl != null ? `Flaring intensity ${flareIntensityHl}% of gross gas vs the 1.00% limit (${flaringSummary.compliance_status}).` : (flaringSummary?.compliance_status || "Flaring intensity not assessable for this period.")],
      ["Flare Destruction Efficiency (DRE)", flaringSummary?.measured_dre_pct != null ? `${flaringSummary.measured_dre_pct}% measured` : na,
        flaringSummary?.dre_method || "No measured DRE recorded; calculations use the 98% default."],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["Performance Milestone", "Observed Metric", "Strategic Decarbonization Significance"]],
      body: execHighlights,
      ...cleanTableTheme,
      margin: { left: margin, right: margin }
    });
    curY = doc.lastAutoTable.finalY + 10;

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
    curY = addTextBlock(isAllYears ? "The reporting period covers all years with verified data." : `The reporting period is the year ${selectedYear}.`, curY);

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
    
    const uniqueBoundaries = [...new Set(reportFacilities.map(f => {
      if (f.boundary_type && f.boundary_detail) {
        return `${f.boundary_type} (${f.boundary_detail})`;
      }
      return f.boundary_type || "Operational Control";
    }))].join(" and ");
    
    curY = addTextBlock(`The consolidation approach used for organizational boundaries is: ${uniqueBoundaries}.`, curY);
    curY += 4;
    curY = addTextBlock(`This inventory consolidates ${reportFacilities.length} facilities within the specified operational and equity boundaries:`, curY);
    curY += 4;

    const facRows = reportFacilities.map((f) => [
      f.name || "Unknown",
      f.code || "-",
      f.segment || "Upstream",
      f.boundary_type || "Operational Control",
      f.boundary_type === "Equity Share" ? `${f.equity_share_pct || 100}%` : "100%",
      f.operator_status || "operated",
      f.country || "Algeria",
    ]);

    autoTable(doc, {
      startY: curY,
      head: [["Facility / Asset", "Code", "Segment", "Boundary Type", "Equity %", "Status", "Country"]],
      body: facRows,
      ...cleanTableTheme,
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;

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
     * CHAPTER 4: HYDROCARBON PRODUCTION PROFILE
     * =========================================================
     */
    curY = addSectionHeader(4, "HYDROCARBON PRODUCTION PROFILE", null, true);

    curY = addTextBlock(
      "Hydrocarbon production data reflects operational throughput across active extraction, processing, and reinjection assets. Gaseous production comprises gross gas extraction, gas utilized for reservoir reinjection, and associated gas. Liquid production includes stabilized crude oil, lease condensates, and liquefied petroleum gas (LPG). Standard reporting incorporates both physical volumes and energy-equivalent barrels of oil equivalent (BOE).",
      curY
    );
    curY += 4;

    const currYearProds: any[] = (allHistoricalProduction as any[]).filter(
      (p: any) => isAllYears || String(p.year) === String(selectedYear)
    );
    const grossGasMmsm3 = currYearProds.reduce(
      (sum: number, p: any) => sum + (Number(p.gross_gas_mmsm3) || 0),
      0
    );
    const gasWoInjMmsm3 = currYearProds.reduce(
      (sum: number, p: any) => sum + (Number(p.gas_without_injected_mmsm3) || 0),
      0
    );
    const injGasMmsm3 = currYearProds.reduce(
      (sum: number, p: any) => sum + (Number(p.injected_gas_mmsm3) || 0),
      0
    );
    const crudeMmboe = currYearProds.reduce(
      (sum: number, p: any) => sum + (Number(p.crude_oil_mmboe) || 0),
      0
    );
    const totalMmboe = currYearProds.reduce(
      (sum: number, p: any) => sum + (Number(p.total_production_mmboe) || 0),
      0
    );
    const totalWoInjMmboe = currYearProds.reduce(
      (sum: number, p: any) => sum + (Number(p.total_production_no_injected_mmboe) || 0),
      0
    );
    const saleableMmboe = currYearProds.reduce(
      (sum: number, p: any) => sum + (Number(p.saleable_production_mmboe) || 0),
      0
    );

    // 1 MMSm3 = 35,314.67 Mcf x 0.178 BOE/Mcf (platform BOE definition, services/dashboard_filters.py)
    const MMBOE_PER_MMSM3 = 35.314666721 * 0.178 / 1000;
    const NA = "—";
    const prodRows = [
      [
        "Gross Gas Production",
        "MMSm3",
        grossGasMmsm3 > 0
          ? grossGasMmsm3.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : NA,
        grossGasMmsm3 > 0 ? (grossGasMmsm3 * MMBOE_PER_MMSM3).toFixed(2) + " MMBOE" : NA,
      ],
      [
        "Injected Gas Volume",
        "MMSm3",
        injGasMmsm3 > 0
          ? injGasMmsm3.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : NA,
        injGasMmsm3 > 0 ? (injGasMmsm3 * MMBOE_PER_MMSM3).toFixed(2) + " MMBOE" : NA,
      ],
      [
        "Gas Production w/o Injected Gas",
        "MMSm3",
        gasWoInjMmsm3 > 0
          ? gasWoInjMmsm3.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : NA,
        gasWoInjMmsm3 > 0 ? (gasWoInjMmsm3 * MMBOE_PER_MMSM3).toFixed(2) + " MMBOE" : NA,
      ],
      [
        "Liquid Production (Crude Oil, Condensates, LPG)",
        "MMBOE",
        crudeMmboe > 0 ? crudeMmboe.toFixed(2) : NA,
        crudeMmboe > 0 ? crudeMmboe.toFixed(2) + " MMBOE" : NA,
      ],
      [
        { content: "Total Production (Gross Extraction)", styles: { fontStyle: "bold" } },
        { content: "MMBOE", styles: { fontStyle: "bold" } },
        { content: totalMmboe > 0 ? totalMmboe.toFixed(2) : NA, styles: { fontStyle: "bold" } },
        { content: "100.0% Baseline Denominator", styles: { fontStyle: "bold" } },
      ],
      [
        "Total Production without Injected Gas",
        "MMBOE",
        totalWoInjMmboe > 0 ? totalWoInjMmboe.toFixed(2) : NA,
        "Net Operational Throughput",
      ],
      [
        { content: "Total Saleable Production", styles: { fontStyle: "bold", textColor: THEME.accent } },
        { content: "MMBOE", styles: { fontStyle: "bold", textColor: THEME.accent } },
        { content: saleableMmboe > 0 ? saleableMmboe.toFixed(2) : NA, styles: { fontStyle: "bold", textColor: THEME.accent } },
        { content: "Commercial Sales Denominator", styles: { fontStyle: "bold", textColor: THEME.accent } },
      ],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["Hydrocarbon Stream / Product", "Unit", "Reported Volume", "Equivalent MMBOE / Share"]],
      body: prodRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 5: QUANTIFIED GHG INVENTORY & MODULAR BREAKDOWN
     * =========================================================
     */
    curY = addSectionHeader(5, "QUANTIFIED GHG INVENTORY & MODULAR BREAKDOWN", null, true);

    doc.setFontSize(11);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Table 5.1: Consolidated Emissions by ISO 14064-1 Category", margin, curY);
    curY += 5;

    autoTable(doc, {
      startY: curY,
      head: [["Category (ISO 14064-1:2018)", "Emissions (tCO2e)", "Relative Share (%)"]],
      body: [
        [
          "Category 1: Direct GHG emissions (Scope 1)",
          fullData.scope1Total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
          fullData.totalEmissions > 0 ? ((fullData.scope1Total / fullData.totalEmissions) * 100).toFixed(1) + "%" : "0.0%",
        ],
        [
          "Category 2: Indirect emissions from imported energy (Scope 2)",
          fullData.scope2Total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
          fullData.totalEmissions > 0 ? ((fullData.scope2Total / fullData.totalEmissions) * 100).toFixed(1) + "%" : "0.0%",
        ],
        [
          "Categories 3-6: Value chain indirect GHG emissions (Scope 3)",
          fullData.scope3Total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
          "—",
        ],
        [
          { content: "Total Consolidated Footprint (Scopes 1+2)", styles: { fontStyle: "bold" } },
          { content: fullData.totalEmissions.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), styles: { fontStyle: "bold" } },
          { content: "100.0%", styles: { fontStyle: "bold" } },
        ],
      ],
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 8;

    curY = checkPageBreak(curY, 65);
    doc.setFontSize(11);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Table 5.2: SANGEA Modular Inventory Breakdown", margin, curY);
    curY += 5;

    const sangeaCombustion = fullData.processBreakdown?.["Combustion"] ?? 0;
    const sangeaFlaring = fullData.processBreakdown?.["Flaring"] ?? (flaringSummary?.total_flaring?.tco2e ?? 0);
    const sangeaLeaks = fullData.processBreakdown?.["Fugitive"] ?? 0.0;
    const sangeaVenting = fullData.processBreakdown?.["Venting"] ?? 0.0;

    const sangeaRows = [
      ["Stationary Combustion", Number(sangeaCombustion).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Gas turbines, compressor drivers, heaters, thermal oxidizers"],
      ["Flaring (Routine, Non-Routine, Safety)", Number(sangeaFlaring).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Central processing facility (CPF) flares, low-pressure flares, pilots"],
      ["Equipment Leaks & Fugitives", Number(sangeaLeaks).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Valves, pump seals, compressor rod packing, flanges"],
      ["Tank & Process Venting", Number(sangeaVenting).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Atmospheric storage tanks, glycol dehydrators, pig launching/receiving"],
      ["Scope 2 (Purchased Electricity)", Number(fullData.scope2Total).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Purchased power imported from national electricity grid"],
      [
        { content: "Total Operational Footprint", styles: { fontStyle: "bold" } },
        { content: Number(fullData.totalEmissions).toLocaleString(undefined, { maximumFractionDigits: 1 }), styles: { fontStyle: "bold" } },
        { content: "Comprehensive Operational Inventory (API Compendium 2021)", styles: { fontStyle: "bold" } },
      ],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["SANGEA Accounting Module", "Emissions (tCO2e)", "Covered Equipment & Operational Scope"]],
      body: sangeaRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 6: OPERATIONAL FLARING & EXECUTIVE DECREE 21-330
     * =========================================================
     */
    curY = addSectionHeader(6, "OPERATIONAL FLARING & EXECUTIVE DECREE 21-330", null, true);

    curY = addTextBlock(
      "Flaring operations are classified into Routine, Non-Routine, and Safety flaring pursuant to the World Bank Zero Routine Flaring (ZRF) initiative and Algerian Executive Decree No. 21-330. Executive Decree 21-330 Article 9 imposes a binding national limit: total volume of gas flared from hydrocarbon production and processing installations must remain below 1.00% of gross gas production.",
      curY
    );
    curY += 4;

    // BUG-078: no sample figures or invented 56/40/4 split when data is missing
    const r_knm3 = flaringSummary?.routine_flaring?.volume_knm3 ?? 0;
    const nr_knm3 = flaringSummary?.non_routine_flaring?.volume_knm3 ?? 0;
    const s_knm3 = flaringSummary?.safety_flaring?.volume_knm3 ?? 0;
    const tot_knm3 = flaringSummary?.total_flaring?.volume_knm3 ?? 0;

    const r_tco2e = flaringSummary?.routine_flaring?.tco2e ?? 0;
    const nr_tco2e = flaringSummary?.non_routine_flaring?.tco2e ?? 0;
    const s_tco2e = flaringSummary?.safety_flaring?.tco2e ?? 0;
    const tot_tco2e = flaringSummary?.total_flaring?.tco2e ?? sangeaFlaring;

    const flareStreamRows = [
      ["Routine Flaring", r_knm3.toLocaleString(), (r_knm3 / 1000).toFixed(3), (flaringSummary?.routine_flaring?.percentage ?? 0) + "%", Number(r_tco2e).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Continuous flaring of associated gas during normal operations"],
      ["Non-Routine Flaring", nr_knm3.toLocaleString(), (nr_knm3 / 1000).toFixed(3), (flaringSummary?.non_routine_flaring?.percentage ?? 0) + "%", Number(nr_tco2e).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Process upsets, plant turnarounds, depressurizations, unit trips"],
      ["Safety & Purge Flaring", s_knm3.toLocaleString(), (s_knm3 / 1000).toFixed(3), (flaringSummary?.safety_flaring?.percentage ?? 0) + "%", Number(s_tco2e).toLocaleString(undefined, { maximumFractionDigits: 1 }), "Continuous flare header sweep, pilot gas, and positive pressure seal"],
      [
        { content: "Total CPF & Field Flaring", styles: { fontStyle: "bold" } },
        { content: tot_knm3.toLocaleString(), styles: { fontStyle: "bold" } },
        { content: (tot_knm3 / 1000).toFixed(3), styles: { fontStyle: "bold" } },
        { content: "100.0%", styles: { fontStyle: "bold" } },
        { content: Number(tot_tco2e).toLocaleString(undefined, { maximumFractionDigits: 1 }), styles: { fontStyle: "bold" } },
        { content: "Consolidated Annual Flare Stream", styles: { fontStyle: "bold" } },
      ],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["Flaring Category", "kNm3", "MMSm3", "Share (%)", "tCO2e", "Operational Scope"]],
      body: flareStreamRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 8;

    curY = checkPageBreak(curY, 60);
    doc.setFontSize(11);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Executive Decree 21-330 Article 9 Compliance Verdict", margin, curY);
    curY += 5;

    const flareIntensityVal = flaringSummary?.flaring_intensity_pct ?? null;
    const isCompliantFlare = flareIntensityVal != null ? flareIntensityVal <= 1.00 : null;
    const yoy = flaringSummary?.yoy_change_pct;
    const measuredDre = flaringSummary?.measured_dre_pct;

    const complianceRows = [
      ["Flaring Intensity (% Gross Gas)", flareIntensityVal != null ? `${flareIntensityVal.toFixed(3)}%` : "n/a", "<= 1.00%", "Executive Decree 21-330 Art. 9",
        isCompliantFlare == null ? "NOT ASSESSABLE" : isCompliantFlare ? "COMPLIANT (PASS)" : "EXCEEDED"],
      ["Flare Destruction Efficiency (DRE)", measuredDre != null ? `${measuredDre}%` : "n/a", "98.0% Standard Default",
        flaringSummary?.dre_method || "Not measured", measuredDre == null ? "DEFAULT APPLIED" : measuredDre >= 98 ? "AT OR ABOVE DEFAULT" : "BELOW DEFAULT"],
      ["Year-over-Year Flaring Trajectory", yoy != null ? `${yoy > 0 ? "+" : ""}${yoy}%` : "n/a", "Negative Trend (<0%)", "Corporate Decarbonization Roadmap",
        yoy == null ? "NOT ASSESSABLE" : yoy < 0 ? "DECREASING" : "INCREASING"],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["Compliance Metric", "Observed Value", "Statutory Limit", "Governing Standard", "Compliance Verdict"]],
      body: complianceRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 7: CRITERIA AIR POLLUTANTS & DECREE 06-138
     * =========================================================
     */
    curY = addSectionHeader(7, "CRITERIA AIR POLLUTANTS & DECREE 06-138", null, true);

    curY = addTextBlock(
      "Criteria Air Pollutants (CAP) are estimated under a dual methodology combining API Compendium 2021 Section 4/5 stoichiometric emission factors for mass emissions with isokinetic stack sampling in accordance with Algerian Executive Decree No. 06-138. Decree 06-138 establishes atmospheric emission limit values (ELVs) in mg/Nm3 for classified industrial facilities.",
      curY
    );
    curY += 4;

    // Chapter 7 is built from the site CAP records (verified only), never from sample numbers
    const CAP_LABELS: Record<string, string> = {
      NO2: "Nitrogen Oxides (NO2)", CO: "Carbon Monoxide (CO)", SO2: "Sulfur Dioxide (SO2)",
      PM: "Particulate Matter (PM)", VOC: "Volatile Organic Compounds (VOC)",
    };
    const CAP_MODULES = [["Stationary Combustion", "combustion"], ["Flare", "flaring"], ["Equipment Leaks", "leaks"], ["O&G Venting", "venting"]];
    const tfmt = (v: any) => (v ? Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—");
    const verifiedCap: any[] = (capEmissions as any[]).filter((r: any) => r.status === "Verified");
    const capMassRows = Object.keys(CAP_LABELS).map((pol) => {
      const recs = verifiedCap.filter((r: any) => r.pollutant === pol);
      const byMod = CAP_MODULES.map(([mod]) => recs.filter((r: any) => r.source_module === mod).reduce((t: number, r: any) => t + (Number(r.mass_tonnes) || 0), 0));
      const moduleSum = byMod.reduce((t: number, v: number) => t + v, 0);
      // a record kept only as a "Total" counts in the total, never on top of module records
      const totalOnly = recs.filter((r: any) => r.source_module === "Total").reduce((t: number, r: any) => t + (Number(r.mass_tonnes) || 0), 0);
      return [CAP_LABELS[pol], ...byMod.map(tfmt), tfmt(moduleSum || totalOnly)];
    });
    const hasCapMass = verifiedCap.length > 0;
    if (!hasCapMass) {
      curY = addTextBlock("No verified criteria air pollutant records exist for this reporting year.", curY);
      curY += 4;
    }

    autoTable(doc, {
      startY: curY,
      head: [["Pollutant", "Combustion (t)", "Flaring (t)", "Leaks (t)", "Venting (t)", "Total Mass (t)"]],
      body: capMassRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 8;

    curY = checkPageBreak(curY, 60);
    doc.setFontSize(11);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("Executive Decree 06-138 Compliance Scorecard", margin, curY);
    curY += 5;

    const capCompRows: any[] = [];
    (capCompliance as any[]).forEach((fac: any) => {
      (fac.pollutants || []).forEach((p: any) => {
        capCompRows.push([
          `${fac.facility_name} · ${CAP_LABELS[p.pollutant] || p.pollutant}`,
          tfmt(p.total_tonnes),
          p.measured_concentration_mg_nm3 ? Number(p.measured_concentration_mg_nm3).toFixed(2) : "not measured",
          Number(p.statutory_limit_mg_nm3).toFixed(1),
          p.status,
        ]);
      });
    });
    if (capCompRows.length === 0) {
      capCompRows.push(["No facility in scope", "—", "—", "—", "NOT ASSESSED"]);
    }

    autoTable(doc, {
      startY: curY,
      head: [["Pollutant", "Annual Mass (t)", "Measured Conc. (mg/Nm3)", "Decree 06-138 Limit", "Compliance Verdict"]],
      body: capCompRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 8: MULTI-METRIC INTENSITIES MATRIX
     * =========================================================
     */
    curY = addSectionHeader(8, "MULTI-METRIC INTENSITIES MATRIX", null, true);

    curY = addTextBlock(
      "Greenhouse gas and methane intensities provide normalized operational benchmarks. Carbon intensity is quantified across both Total Production (including reinjected gas) and Saleable Commercial Products. Methane intensity is evaluated per the Natural Gas Sustainability Initiative (NGSI) mass-balance protocol.",
      curY
    );
    curY += 4;

    // BUG-044 / BUG-078: values and verdicts computed from the data; "n/a" when not recorded
    const ciTot = granularIntensities?.ci_by_total_production_kg_boe ?? null;
    const ciSal = granularIntensities?.ci_by_saleable_production_kg_boe ?? null;
    const ngsiCh4 = granularIntensities?.methane_intensity_ngsi_wt_pct ?? null;
    const boeTot = granularIntensities?.total_production_boe || 0;
    const flaredSm3PerBoe = boeTot > 0 && flaringSummary?.total_flaring ? (flaringSummary.total_flaring.volume_m3 / boeTot) : null;
    const fmt = (v: any, d: number = 2) => (v == null ? "n/a" : Number(v).toFixed(d));

    const intensityRows = [
      ["Carbon Intensity (Total Production)", `${fmt(ciTot)} kg CO2e / BOE`, "SANGEA / Ipieca Guidelines",
        ciTot == null ? "No production recorded" : ciTot < 15 ? "Below 15.0 kg/BOE" : "At or above 15.0 kg/BOE"],
      ["Carbon Intensity (Saleable Product)", `${fmt(ciSal)} kg CO2e / BOE`, "Company Protocol",
        ciSal == null ? "Saleable production not recorded" : "Normalized to commercial export sales"],
      ["Methane Intensity (NGSI Protocol)", `${fmt(ngsiCh4, 3)} wt.%`, "NGSI Methane Protocol",
        ngsiCh4 == null ? "Gas throughput not recorded" : ngsiCh4 <= 0.20 ? "Below the 0.20% methane intensity ceiling" : "Above the 0.20% methane intensity ceiling"],
      ["Flaring Intensity (Volume)", `${fmt(flaredSm3PerBoe)} Sm3 / BOE`, "World Bank GGFR Framework", flaredSm3PerBoe == null ? "Not assessable" : "Computed from recorded flaring and production"],
      ["Flaring Intensity (Gas Ratio)", `${fmt(flareIntensityVal, 3)} vol.%`, "Executive Decree 21-330 Art. 9",
        isCompliantFlare == null ? "Not assessable" : isCompliantFlare ? "Within the 1.00% statutory ceiling" : "Exceeds the 1.00% statutory ceiling"],
      ["OGCI 2025 Industry Target", "17.0 kg CO2e / BOE", "Oil and Gas Climate Initiative", "Global upstream decarbonization benchmark"],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["Performance Intensity Indicator", "Reported Metric", "Accounting Protocol", "Benchmark Reference"]],
      body: intensityRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 9: JV PARTNER EQUITY SHARE ALLOCATIONS
     * =========================================================
     */
    curY = addSectionHeader(9, "JV PARTNER EQUITY SHARE ALLOCATIONS", null, true);

    curY = addTextBlock(
      "Under ISO 14064-1 equity share accounting and the Block 404a / Block 208 Association Contracts, operational GHG and methane emissions are allocated proportional to the participating interest of each joint venture partner.",
      curY
    );
    curY += 4;

    // BUG-078: partner shares come from the server's /equity/allocation (effective equity slices,
    // Verified Scope 1 and Scope 2 records), never from hard-coded percentages.
    const partnerAgg: Record<string, { name: string; code: string; co2e: number; ch4: number }> = {};
    let totCo2eAll = 0;
    let totCh4All = 0;
    (equityAllocations as any[]).forEach((fac: any) => {
      totCo2eAll += Number(fac.total_co2e || 0);
      totCh4All += Number(fac.total_ch4 || 0);
      (fac.partners || []).forEach((pa: any) => {
        const k = pa.partner_id ?? pa.partner_name;
        if (!partnerAgg[k]) partnerAgg[k] = { name: pa.partner_name, code: pa.partner_code || "", co2e: 0, ch4: 0 };
        partnerAgg[k].co2e += Number(pa.allocated_co2e || 0);
        partnerAgg[k].ch4 += Number(pa.allocated_ch4 || 0);
      });
    });
    const partnerList = Object.values(partnerAgg).filter((pa: any) => pa.co2e > 0 || pa.ch4 > 0);
    const jvRows = partnerList.length === 0
      ? [[{ content: "No JV equity shares configured for this period (see Equity Share settings).", colSpan: 6 }]]
      : [
        ...partnerList.map((pa) => [
          pa.name,
          pa.code,
          "",
          totCo2eAll > 0 ? `${((pa.co2e / totCo2eAll) * 100).toFixed(2)}%` : "n/a",
          pa.co2e.toLocaleString(undefined, { maximumFractionDigits: 1 }),
          pa.ch4.toFixed(1),
        ]),
        [
          { content: "Total (Verified Scope 1 + 2)", styles: { fontStyle: "bold" } },
          "",
          "",
          "",
          { content: totCo2eAll.toLocaleString(undefined, { maximumFractionDigits: 1 }), styles: { fontStyle: "bold" } },
          { content: totCh4All.toFixed(1), styles: { fontStyle: "bold" } },
        ],
      ];

    autoTable(doc, {
      startY: curY,
      head: [["Joint Venture Partner", "Code", "Country", "Equity %", "Allocated GHG (tCO2e)", "Allocated CH4 (tCH4)"]],
      body: jvRows,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 10: GHG REDUCTION INITIATIVES
     * =========================================================
     */
    curY = addSectionHeader(10, "GHG REDUCTION INITIATIVES", null, true);

    if (mitigationData.length > 0) {
      curY = addTextBlock(
        `There are ${mitigationData.length} GHG reduction initiatives documented for this inventory.`,
        curY
      );
      curY += 5;

      const projBody = mitigationData.map((p) => [
        p.title || "-",
        p.status || "-",
        p.estimated_reduction ? p.estimated_reduction.toFixed(2) : "0.00",
      ]);

      autoTable(doc, {
        startY: curY,
        head: [["Project Title", "Status", "Estimated Reduction (tCO2e)"]],
        body: projBody,
        ...cleanTableTheme,
        styles: { fontSize: 8, cellPadding: 2 },
        headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
        margin: { left: margin, right: margin },
      });
      curY = doc.lastAutoTable.finalY + 10;
    } else {
      curY = addTextBlock(
        "Key operational reduction initiatives include flare minimization sweep gas retrofits, routine flare gas re-routing to low-pressure compression, and optical gas imaging (OGI) leak repairs.",
        curY
      );
    }
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 11: QUALITY ASSURANCE & QUALITY CONTROL (QA/QC)
     * =========================================================
     */
    curY = addSectionHeader(11, "QUALITY ASSURANCE & QUALITY CONTROL", null, true);

    curY = addTextBlock(
      "To ensure the integrity of this inventory, a comprehensive Quality Assurance (QA) and Quality Control (QC) process is implemented in accordance with ISO 14064-1.",
      curY
    );
    curY += 4;

    const qcBody = [
      ["Data Collection & Input", "Verify sample of input activity metering data against DCS logs and custody transfer tickets."],
      ["Methodology Consistency", "Ensure calculation algorithms conform to API Compendium 2021 across entire time series."],
      ["Flaring Metering Audit", "Inspect ultrasonic flare meters and calibrate flow meters per API MPMS Chapter 14."],
      ["LDAR Survey Verification", "Conduct optical gas imaging (OGI) surveys with FLIR GFx320 certified cameras to eliminate leaks."],
      ["Uncertainty Control", "Examine unexplained deviations and apply Tier 3 site-specific factors where accessible."],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["QC Category", "Verification Action"]],
      body: qcBody,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * CHAPTER 12: REGULATORY FRAMEWORK & REFERENCES
     * =========================================================
     */
    curY = addSectionHeader(12, "REGULATORY FRAMEWORK & REFERENCES", null, true);

    curY = addTextBlock(
      "This greenhouse gas inventory was compiled in compliance with Algerian national environmental legislation and international climate reporting standards. Primary statutory references include:",
      curY
    );
    curY += 4;

    const refBody = [
      ["Executive Decree 06-138", "Regulates atmospheric emissions and sets statutory limit values (mg/Nm3) for industrial installations."],
      ["Executive Decree 21-330 Art. 9", "Establishes a mandatory limit on gas flaring not to exceed 1.00% of gross gas production."],
      ["National Hydrocarbon Law 19-13", "Governs hydrocarbon exploration, exploitation, and environmental protection in Algeria."],
      ["ISO 14064-1:2018", "Specification with guidance at the organization level for quantification and reporting of GHG emissions."],
      ["API Compendium 2021", "Standard industry methodologies and emission factors for petroleum and natural gas facilities."],
      ["UNFCCC / Paris Agreement", "National Determined Contributions (NDC) alignment for low-carbon energy transition."],
    ];

    autoTable(doc, {
      startY: curY,
      head: [["Statute / Standard", "Regulatory Mandate & Scope"]],
      body: refBody,
      ...cleanTableTheme,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 8.5 },
      margin: { left: margin, right: margin },
    });
    curY = doc.lastAutoTable.finalY + 10;
    drawFooter();

    /**
     * =========================================================
     * ANNEX A: COMPREHENSIVE 5-YEAR HISTORICAL DATA TABLES (2021–2025)
     * =========================================================
     */
    doc.addPage("a4", "p");
    drawBackground();
    curY = 30;

    doc.setFontSize(16);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    const annexEnd = isAllYears ? new Date().getFullYear() : Number(year);
    const annexYears = [4, 3, 2, 1, 0].map((k) => annexEnd - k);
    doc.text(`ANNEX A: 5-YEAR HISTORICAL DATA TABLES (${annexYears[0]}–${annexEnd})`, margin, curY);
    doc.setDrawColor(200, 200, 200);
    doc.setLineWidth(0.5);
    doc.line(margin, curY + 4, pageWidth - margin, curY + 4);
    curY += 14;

    // Annex A is built from the records of each year; a year without records shows "—"
    const yearParams = (y: any) => ({ year: y, ...(targetFacilityId && { facilityId: targetFacilityId, facility_id: targetFacilityId }) });
    const [annexFlaring, annexIntensity]: [any[], any[]] = await Promise.all([
      Promise.all(annexYears.map((y: any) => api.get("/dashboard/flaring-summary", { params: yearParams(y) }).then((r: any) => r.data).catch(() => null))),
      Promise.all(annexYears.map((y: any) => api.get("/dashboard/granular-intensities", { params: yearParams(y) }).then((r: any) => r.data).catch(() => null))),
    ]);
    const prodSum = (y: any, field: string) => {
      const rows = (allHistoricalProduction as any[]).filter((p: any) => String(p.year) === String(y));
      const v = rows.reduce((t: number, p: any) => t + (Number(p[field]) || 0), 0);
      return rows.length && v > 0 ? v : null;
    };
    const cell = (v: any, d: number = 2, suffix: string = "") => (v == null || !Number.isFinite(Number(v)) ? "—" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) + suffix);
    const annexTable = (title: string, headFirst: string, rows: any[]) => {
      curY = checkPageBreak(curY, 60);
      doc.setFontSize(10);
      doc.setTextColor(...THEME.dark);
      doc.setFont("helvetica", "bold");
      doc.text(title, margin, curY);
      curY += 4;
      autoTable(doc, {
        startY: curY,
        head: [[headFirst, "Unit", ...annexYears.map(String)]],
        body: rows,
        ...cleanTableTheme,
        styles: { fontSize: 7.5, cellPadding: 1.5 },
        headStyles: { ...cleanTableTheme.headStyles, fontSize: 8 },
        margin: { left: margin, right: margin },
      });
      curY = doc.lastAutoTable.finalY + 8;
    };

    annexTable("Table A.1: Hydrocarbon Production Profile", "Product Stream", [
      ["Gross Gas Production", "MMSm3", ...annexYears.map((y) => cell(prodSum(y, "gross_gas_mmsm3")))],
      ["Injected Gas Volume", "MMSm3", ...annexYears.map((y) => cell(prodSum(y, "injected_gas_mmsm3")))],
      ["Gas w/o Injected Gas", "MMSm3", ...annexYears.map((y) => cell(prodSum(y, "gas_without_injected_mmsm3")))],
      ["Liquid Production (Crude/LPG)", "MMBOE", ...annexYears.map((y) => cell(prodSum(y, "crude_oil_mmboe")))],
      ["Total Production (Gross)", "MMBOE", ...annexYears.map((y) => cell(prodSum(y, "total_production_mmboe")))],
      ["Total Production w/o Injected Gas", "MMBOE", ...annexYears.map((y) => cell(prodSum(y, "total_production_no_injected_mmboe")))],
      ["Total Saleable Production", "MMBOE", ...annexYears.map((y) => cell(prodSum(y, "saleable_production_mmboe")))],
    ]);

    const flareVol = (f: any, k: string) => (f && f[k] && f[k].volume_knm3 ? f[k].volume_knm3 : null);
    annexTable("Table A.2: Flaring Breakdown", "Flaring Category", [
      ["Routine Flaring", "kNm3", ...annexFlaring.map((f) => cell(flareVol(f, "routine_flaring"), 0))],
      ["Non-Routine Flaring", "kNm3", ...annexFlaring.map((f) => cell(flareVol(f, "non_routine_flaring"), 0))],
      ["Safety & Purge Flaring", "kNm3", ...annexFlaring.map((f) => cell(flareVol(f, "safety_flaring"), 0))],
      ["Total Flared Volume", "kNm3", ...annexFlaring.map((f) => cell(flareVol(f, "total_flaring"), 0))],
      ["Flaring Intensity (% Gas)", "vol.%", ...annexFlaring.map((f) => cell(f?.flaring_intensity_pct, 2, "%"))],
      ["Decree 21-330 Status", "Limit: <=1.00%", ...annexFlaring.map((f) =>
        f?.flaring_intensity_pct == null ? "—" : Number(f.flaring_intensity_pct) <= 1.0 ? "COMPLIANT" : "Exceeded")],
    ]);

    annexTable("Table A.3: Performance Intensities", "Intensity Metric", [
      ["Carbon Intensity (Total BOE)", "kg CO2e / BOE", ...annexIntensity.map((g) => cell(g?.ci_by_total_production_kg_boe))],
      ["Carbon Intensity (Saleable BOE)", "kg CO2e / BOE", ...annexIntensity.map((g) => cell(g?.ci_by_saleable_production_kg_boe))],
      ["Methane Intensity (NGSI)", "wt.%", ...annexIntensity.map((g) => cell(g?.methane_intensity_ngsi_wt_pct, 3, "%"))],
      ["Flaring Intensity (Volume)", "Sm3 / BOE", ...annexYears.map((y, i) => {
        const f = annexFlaring[i];
        const boe = annexIntensity[i]?.total_production_boe;
        return cell(boe > 0 && f?.total_flaring?.volume_m3 ? f.total_flaring.volume_m3 / boe : null);
      })],
    ]);
    curY += 2;
    drawFooter();

    /**
     * =========================================================
     * ANNEX B: DETAILED VERIFIED EMISSIONS RECORD LEDGER
     * =========================================================
     */
    doc.addPage("a4", "p");
    drawBackground();
    curY = 30;

    doc.setFontSize(16);
    doc.setTextColor(...THEME.accent);
    doc.setFont("helvetica", "bold");
    doc.text("ANNEX B: DETAILED VERIFIED EMISSIONS LEDGER", margin, curY);
    doc.setFontSize(9);
    doc.setTextColor(...THEME.textMuted);
    doc.text(
      `Total verified records: ${fullData.scope1Rows.length} | Fiscal Year: ${selectedYear} | GWP Standard: ${resolvedGwp.label}`,
      margin,
      curY + 7
    );
    curY += 14;

    autoTable(doc, {
      startY: curY,
      head: [
        [
          "Date",
          "Facility",
          "Scope",
          "Process / Source",
          "Fuel",
          "Qty",
          "Unit",
          "CO2 (t)",
          "CH4 (t)",
          "tCO2e",
        ],
      ],
      body: fullData.scope1Rows.map((r) => [
        r[1],
        r[13] || "-",
        r[12] || "1",
        r[2],
        r[3],
        Number(r[4] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 }),
        r[11],
        Number(r[5] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 }),
        Number(r[6] || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }),
        Number(r[7] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 }),
      ]),
      ...cleanTableTheme,
      styles: { fontSize: 6.5, cellPadding: 1.2 },
      headStyles: { ...cleanTableTheme.headStyles, fontSize: 7 },
      didDrawPage: (hookData) => {
        drawFooter(hookData.pageNumber);
      },
    });

    // named after what the report covers (every report was saved as the Berkine master report)
    const scopeName = reportFacilities.length === 1
      ? String(reportFacilities[0].name || "Facility").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "")
      : "All_Facilities";
    const filename = `GHG_Inventory_Report_${scopeName}_${isAllYears ? "All_Years" : selectedYear}.pdf`;
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

// --- DATA FETCHING (Dynamic GWP Recalculation) ---
async function fetchAllReportData(
  api: any,
  year: any,
  rawReportData: any[],
  params: any,
  productionData: any[] = [],
  gwpFactors: any = DEFAULT_GWP,
  storedGwpFactors: any = gwpFactors,
) {
  let co2Total = 0,
    ch4Total = 0,
    n2oTotal = 0;
  let scope1Total = 0,
    scope2Total = 0,
    scope3Total = 0,
    storedScope12 = 0;
  let processBreakdown: Record<string, number> = {
    Combustion: 0,
    Flaring: 0,
    Venting: 0,
    Fugitive: 0,
    Other: 0,
  };
  let facilityBreakdown: Record<string, number> = {};
  let monthlyData: Record<number | string, number> = {};

  const co2_factor = (gwpFactors && gwpFactors.CO2 !== undefined) ? Number(gwpFactors.CO2) : 1;
  const ch4_factor = (gwpFactors && gwpFactors.CH4 !== undefined) ? Number(gwpFactors.CH4) : 28;
  const n2o_factor = (gwpFactors && gwpFactors.N2O !== undefined) ? Number(gwpFactors.N2O) : 265;

  const scope1Rows = rawReportData.map((r) => {
    const co2Val = Number(r.co2_emissions || 0);
    const ch4Val = Number(r.ch4_emissions || 0);
    const n2oVal = Number(r.n2o_emissions || 0);

    // BUG-077: use the stored, server-calculated co2e_total (same basis as the dashboard);
    // re-deriving it client-side made the PDF disagree with the dashboard
    // re-based on the requested GWP set by its CH4 / N2O difference (the PDF printed the AR5 totals under an AR4 label)
    let tVal = Number(r.co2e_total || 0);
    if (!tVal && (co2Val > 0 || ch4Val > 0 || n2oVal > 0)) {
      tVal = (co2Val * co2_factor) + (ch4Val * ch4_factor) + (n2oVal * n2o_factor);
    } else if (tVal) {
      tVal += ch4Val * (ch4_factor - Number(storedGwpFactors?.CH4 ?? ch4_factor))
        + n2oVal * (n2o_factor - Number(storedGwpFactors?.N2O ?? n2o_factor));
    }

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

    if (co2Val === 0 && ch4Val === 0 && n2oVal === 0 && tVal > 0) {
      co2Total += tVal;
    } else {
      co2Total += co2Val;
      ch4Total += ch4Val;
      n2oTotal += n2oVal;
    }

    const fName = r.facility_name || "Unknown Facility";
    if (!facilityBreakdown[fName]) facilityBreakdown[fName] = 0;
    facilityBreakdown[fName] += tVal;

    let recMonth = r.month;
    if (!recMonth && r.date) {
      const d = new Date(r.date);
      if (!isNaN(d.getTime())) recMonth = d.getMonth() + 1;
    }
    if (recMonth) {
      if (!monthlyData[recMonth]) monthlyData[recMonth] = 0;
      monthlyData[recMonth] += tVal;
    }

    if (scope === "2") scope2Total += tVal;
    else if (scope === "3") scope3Total += tVal;
    else scope1Total += tVal;
    if (scope !== "3") storedScope12 += Number(r.co2e_total || 0) || tVal;

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

    // Scope 1 sources only: Scope 2 / 3 rows landed in "Other", which then read as the primary driver
    if (scope === "1") processBreakdown[procCat] = (processBreakdown[procCat] || 0) + tVal;

    let efCo2 = r.ef_used_co2 || 0;
    let efCh4 = r.ef_used_ch4 || 0;
    let efN2o = r.ef_used_n2o || 0;

    if (efCo2 === 0 && r.quantity > 0 && r.co2_emissions > 0)
      efCo2 = r.co2_emissions / r.quantity;
    if (efCh4 === 0 && r.quantity > 0 && r.ch4_emissions > 0)
      efCh4 = r.ch4_emissions / r.quantity;
    if (efN2o === 0 && r.quantity > 0 && r.n2o_emissions > 0)
      efN2o = r.n2o_emissions / r.quantity;

    // the activity period, not the entry date (every row showed the day it was typed in)
    const dateStr = r.date || r.timestamp;
    const dateObj = dateStr ? new Date(dateStr) : null;
    const dateDisplay = r.year && r.month
      ? `${r.year}-${String(r.month).padStart(2, "0")}`
      : dateObj && !isNaN(dateObj.getTime())
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

  let totalProductionBoe = 0;
  let intensityMetrics = { avgCo2: "N/A", avgCh4: "N/A", totalProd: "0" };
  if (productionData.length > 0) {
    let weightedCo2Sum = 0,
      weightedCh4Sum = 0,
      totalBoeSum = 0;
    productionData.forEach((d: any) => {
      const boe = d.total_boe || 0;
      if (boe > 0) {
        weightedCo2Sum += d.co2_intensity * boe; // co2_intensity already in kg/BOE
        weightedCh4Sum += d.ch4_intensity * boe; // ch4_intensity already in kg/BOE (was erroneously * 1000)
        totalBoeSum += boe;
      }
    });
    totalProductionBoe = totalBoeSum;
    // the server intensity is on the stored (system GWP-100) totals: re-base it on the requested GWP set
    const gwpRatio = storedScope12 > 0 ? (scope1Total + scope2Total) / storedScope12 : 1;
    intensityMetrics = {
      avgCo2: totalBoeSum > 0 ? ((weightedCo2Sum / totalBoeSum) * gwpRatio).toFixed(4) : "0",
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

  // the operational footprint every "Scope 1 & 2" / "Scopes 1+2" line prints; Scope 3 is reported beside it
  const totalEmissions = scope1Total + scope2Total;

  return {
    scope1Rows,
    co2Total,
    ch4Total,
    n2oTotal,
    scope1Total,
    scope2Total,
    scope3Total,
    totalProductionBoe,
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
