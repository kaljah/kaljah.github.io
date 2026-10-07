import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PieChart, LineChart, BarChart } from "../components/charts";

describe("Modernized Chart Suite", () => {
  describe("PieChart", () => {
    it("renders empty state when data is missing or empty", () => {
      render(<PieChart data={[]} />);
      expect(screen.getByText("No distribution data available")).toBeInTheDocument();
    });

    it("renders empty state when total value is 0", () => {
      render(
        <PieChart
          data={[
            { name: "Scope 1", value: 0 },
            { name: "Scope 2", value: 0 },
          ]}
        />,
      );
      expect(screen.getByText("No distribution data available")).toBeInTheDocument();
    });

    it("renders donut chart with center KPI overlay and legend pills", () => {
      const data = [
        { name: "Combustion", value: 1200 },
        { name: "Flaring", value: 800 },
      ];
      render(
        <PieChart
          data={data}
          title="Emissions Distribution"
          centerLabel="TOTAL"
          centerSub="tCO₂e"
        />,
      );

      expect(screen.getByText("Emissions Distribution")).toBeInTheDocument();
      expect(screen.getByText("TOTAL")).toBeInTheDocument();
      expect(screen.getByText("2.0k")).toBeInTheDocument();
      expect(screen.getByText("tCO₂e")).toBeInTheDocument();
      expect(screen.getByText("Combustion")).toBeInTheDocument();
      expect(screen.getByText("Flaring")).toBeInTheDocument();
    });
  });

  describe("LineChart", () => {
    it("renders empty state when data is empty", () => {
      render(<LineChart data={[]} />);
      expect(screen.getByText("No trend data available")).toBeInTheDocument();
    });

    it("renders line chart with title and custom data", () => {
      const data = [
        { year: 2021, emissions: 100 },
        { year: 2022, emissions: 90 },
      ];
      const { container } = render(
        <LineChart
          data={data}
          xKey="year"
          lines={[{ dataKey: "emissions", name: "Emissions", color: "#ff6600" }]}
          title="Yearly Trend"
        />,
      );

      expect(screen.getByText("Yearly Trend")).toBeInTheDocument();
      expect(container.querySelector(".chart-wrapper")).toBeInTheDocument();
    });

    it("supports series alias for lines", () => {
      const data = [{ year: 2021, val: 50 }];
      const { container } = render(
        <LineChart
          data={data}
          xKey="year"
          series={[{ dataKey: "val", name: "Value", color: "#2563eb" }]}
        />,
      );
      expect(container.querySelector(".chart-wrapper")).toBeInTheDocument();
    });
  });

  describe("BarChart", () => {
    it("renders empty state when data is empty", () => {
      render(<BarChart data={[]} />);
      expect(screen.getByText("No benchmark data available")).toBeInTheDocument();
    });

    it("renders bar chart with title and data", () => {
      const data = [
        { name: "Facility A", value: 15.5 },
        { name: "Facility B", value: 22.1 },
      ];
      const { container } = render(
        <BarChart
          data={data}
          dataKey="value"
          xKey="name"
          title="Facility Comparison"
        />,
      );

      expect(screen.getByText("Facility Comparison")).toBeInTheDocument();
      expect(container.querySelector(".chart-wrapper")).toBeInTheDocument();
    });

    it("renders multiple bars with bars prop", () => {
      const data = [
        { name: "Facility A", scope1: 10, scope2: 5 },
      ];
      const { container } = render(
        <BarChart
          data={data}
          bars={[
            { dataKey: "scope1", name: "Scope 1", color: "#ff6600" },
            { dataKey: "scope2", name: "Scope 2", color: "#2563eb" },
          ]}
        />,
      );
      expect(container.querySelector(".chart-wrapper")).toBeInTheDocument();
    });
  });
});
