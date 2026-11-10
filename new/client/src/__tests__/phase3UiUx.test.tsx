import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { LANGUAGES, setLanguage, currentLanguage } from "../i18n";
import { TableSkeleton, ChartSkeleton } from "../ui/Skeleton";
import Scope2FormNewElectricityEntry from "../components/scope2-form/Scope2FormNewElectricityEntry";

describe("Phase 3 UI/UX Verifications", () => {
  describe("3.8 Arabic Language & RTL Direction", () => {
    it("includes Arabic ('ar') in the supported LANGUAGES list with dir='rtl'", () => {
      const arLang = LANGUAGES.find((l) => l.value === "ar");
      expect(arLang).toBeDefined();
      expect(arLang?.label).toBe("العربية");
      expect(arLang?.dir).toBe("rtl");
    });

    it("sets document dir to 'rtl' when language is switched to Arabic", () => {
      setLanguage("ar", { reload: false });
      expect(document.documentElement.dir).toBe("rtl");
      expect(document.documentElement.lang).toBe("ar");

      // Reset back to English
      setLanguage("en", { reload: false });
      expect(document.documentElement.dir).toBe("ltr");
      expect(document.documentElement.lang).toBe("en");
    });
  });

  describe("3.3 Scope 2 Disabled & Dependent Fields", () => {
    const dummyProps = {
      activity: "",
      allocationMethod: "wri_efficiency",
      amount: "",
      boilerEff: 0.8,
      division: "",
      facilityId: "",
      field: "",
      getFacilityOptions: () => [
        { value: "1", label: "Hassi Messaoud North" },
        { value: "2", label: "Hassi R'Mel" },
      ],
      getGridOptions: () => [],
      gridRegion: "",
      handleAddEntry: () => {},
      handleSourceTypeChange: () => {},
      heatEff: "",
      heatOutput: "",
      marketFactor: "",
      marketInstrument: "",
      month: 1,
      powerEff: "",
      powerOutput: "",
      setAllocationMethod: () => {},
      setAmount: () => {},
      setBoilerEff: () => {},
      setFacilityId: () => {},
      setGridRegion: () => {},
      setHeatEff: () => {},
      setHeatOutput: () => {},
      setMarketFactor: () => {},
      setMarketInstrument: () => {},
      setMonth: () => {},
      setPowerEff: () => {},
      setPowerOutput: () => {},
      setTransLoss: () => {},
      setUnit: () => {},
      setYear: () => {},
      sourceType: "electricity",
      submitting: false,
      transLoss: 0,
      unit: "kWh",
      unitOptions: [],
      year: 2026,
    };

    it("displays 'Select a region first' on dependent fields when no region is selected", () => {
      render(<Scope2FormNewElectricityEntry {...dummyProps} facilityId="" activity="" division="" field="" />);
      const selectFirstPrompts = screen.getAllByText("Select a region first");
      expect(selectFirstPrompts.length).toBeGreaterThanOrEqual(3);

      const inputs = screen.getAllByPlaceholderText("Select a region first");
      expect(inputs.length).toBe(3);
      inputs.forEach((input) => expect(input).toBeDisabled());
    });

    it("displays 'Auto-filled from Region' when a region is selected", () => {
      render(
        <Scope2FormNewElectricityEntry
          {...dummyProps}
          facilityId="1"
          activity="Upstream"
          division="Production"
          field="Hassi Messaoud"
        />
      );
      const autoFilledBadges = screen.getAllByText("Auto-filled from Region");
      expect(autoFilledBadges.length).toBe(3);
    });

    it("displays Location-based method for standard grid electricity and Market-based when contractual instrument selected", () => {
      const { rerender } = render(
        <Scope2FormNewElectricityEntry
          {...dummyProps}
          sourceType="electricity"
          marketInstrument=""
        />
      );
      expect(screen.getByText("Location-based (Grid)")).toBeInTheDocument();

      rerender(
        <Scope2FormNewElectricityEntry
          {...dummyProps}
          sourceType="electricity"
          marketInstrument="REC"
        />
      );
      expect(screen.getByText("Market-based (Contractual)")).toBeInTheDocument();
    });
  });

  describe("3.6 Skeleton Loaders", () => {
    it("renders TableSkeleton with accessible role='status'", () => {
      render(<TableSkeleton rows={4} cols={3} />);
      const tableStatus = screen.getByRole("status", { name: /loading table data/i });
      expect(tableStatus).toBeInTheDocument();
    });

    it("renders ChartSkeleton with accessible role='status'", () => {
      render(<ChartSkeleton height={250} />);
      const chartStatus = screen.getByRole("status", { name: /loading chart/i });
      expect(chartStatus).toBeInTheDocument();
    });
  });
});
