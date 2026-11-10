import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SettingsFacilityLevelOGMPOverrides from "../pages/settings/SettingsFacilityLevelOGMPOverrides";

describe("SettingsFacilityLevelOGMPOverrides", () => {
  const mockFacilities = [
    {
      id: 1,
      name: "RNS Facility",
      code: "FAC-1",
      segment: "Upstream",
    },
    {
      id: 7,
      name: "Basin Gamma Sour Gas Plant",
      code: "FAC-7",
      segment: "Upstream",
    },
  ];

  it("computes target year correctly: base year + 5 for non_operated and + 3 for operated", () => {
    const facilityEdits = {
      1: {
        operator_status: "non_operated",
        country: "Algeria",
        ogmp_membership_year: 2023,
        reconciliation_threshold: 50.0,
      },
      7: {
        operator_status: "operated",
        country: "Algeria",
        ogmp_membership_year: 2023,
        reconciliation_threshold: 15.0,
      },
    };

    render(
      <SettingsFacilityLevelOGMPOverrides
        facilities={mockFacilities}
        facilityEdits={facilityEdits}
        handleFacilityChange={vi.fn()}
        handleSaveFacility={vi.fn()}
        isAdmin={true}
        user={{ role: "admin" }}
      />
    );

    // RNS is non-operated, base year 2023 -> target year must be 2028 (2023 + 5), NOT 2026!
    expect(screen.getByText("2028")).toBeInTheDocument();
    // Basin Gamma is operated, base year 2023 -> target year must be 2026 (2023 + 3)
    const year2026Elements = screen.getAllByText("2026");
    expect(year2026Elements.length).toBeGreaterThan(0);
    // Specifically ensure one of the 2026 elements is the Target Year badge (not just the dropdown option)
    expect(year2026Elements.some((el) => el.tagName === "SPAN")).toBe(true);
  });

  it("displays Unsaved badge and batch save button when dirtyFacilityIds has entries", () => {
    const facilityEdits = {
      1: {
        operator_status: "non_operated",
        country: "Algeria",
        ogmp_membership_year: 2023,
        reconciliation_threshold: 50.0,
      },
    };

    render(
      <SettingsFacilityLevelOGMPOverrides
        facilities={[mockFacilities[0]]}
        facilityEdits={facilityEdits}
        handleFacilityChange={vi.fn()}
        handleSaveFacility={vi.fn()}
        dirtyFacilityIds={new Set([1])}
        handleSaveAllDirtyFacilities={vi.fn()}
        isAdmin={true}
        user={{ role: "admin" }}
      />
    );

    expect(screen.getByText("Unsaved")).toBeInTheDocument();
    expect(screen.getByText(/Save All Modified Facilities/)).toBeInTheDocument();
  });
});
