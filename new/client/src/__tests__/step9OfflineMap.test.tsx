import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn(),
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, fullName: "Demo Admin", role: "admin", location: "Global" },
    loading: false,
  }),
}));

vi.mock("../components/Toast", () => ({
  useToast: () => toastMock,
}));

const apiGetMock = vi.fn();
vi.mock("../api", () => ({
  default: {
    get: (...args: any[]) => apiGetMock(...args),
  },
}));

const mountedTileLayers: Array<{ url: string; eventHandlers?: Record<string, () => void> }> = [];

vi.mock("react-leaflet", () => {
  const MapContainer = ({ children }: any) => (
    <div data-testid="leaflet-map-container">{children}</div>
  );
  const TileLayer = (props: any) => {
    mountedTileLayers.push({ url: props.url, eventHandlers: props.eventHandlers });
    return <div data-testid="leaflet-tile-layer" data-url={props.url} />;
  };
  const GeoJSON = ({ data }: any) => (
    <div data-testid={`leaflet-geojson-${data?.properties?.name || "layer"}`} />
  );
  const Marker = ({ children }: any) => <div data-testid="leaflet-marker">{children}</div>;
  const Circle = () => <div data-testid="leaflet-circle" />;
  const Tooltip = ({ children }: any) => <div>{children}</div>;
  const ZoomControl = () => <div data-testid="leaflet-zoom" />;
  const useMap = () => ({ flyTo: vi.fn(), invalidateSize: vi.fn() });
  return { MapContainer, TileLayer, GeoJSON, Marker, Circle, Tooltip, ZoomControl, useMap };
});

import EmissionsMap from "../pages/MethaneExplorer";

const SAMPLE_FACILITIES = [
  {
    id: 1,
    name: "Facility A-1",
    code: "FA-1",
    region: "Basin Alpha",
    region_identifier: "Basin Alpha",
    activity: "EP",
    division: "Production",
    latitude: 31.65,
    longitude: 6.08,
  },
  {
    id: 2,
    name: "Facility B-2",
    code: "FB-2",
    region: "Basin Beta",
    region_identifier: "Basin Beta",
    activity: "GP",
    division: "Processing",
    latitude: 28.42,
    longitude: 4.15,
  },
];

const SAMPLE_STATS = [
  { facility_id: 1, total_ch4: 3200, total_co2e: 89600, total_boe: 1200000, ch4_intensity: 0.25 },
  { facility_id: 2, total_ch4: 800, total_co2e: 22400, total_boe: 650000, ch4_intensity: 0.11 },
];

describe("Step 9: Offline Map Vector Fallback", () => {
  let onlineSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mountedTileLayers.length = 0;
    onlineSpy = vi.spyOn(window.navigator, "onLine", "get").mockReturnValue(true);

    apiGetMock.mockImplementation((url: string) => {
      if (url === "/facilities") return Promise.resolve({ data: SAMPLE_FACILITIES });
      if (url.startsWith("/dashboard/intensity-stats")) return Promise.resolve({ data: SAMPLE_STATS });
      if (url === "/dashboard/years") return Promise.resolve({ data: [2024, 2025] });
      if (url === "/data/ogmp-surveys") return Promise.resolve({ data: [] });
      if (url === "/map-config") {
        return Promise.resolve({ data: { tile_url: null, attribution: null, subdomains: null } });
      }
      return Promise.resolve({ data: {} });
    });
  });

  afterEach(() => {
    onlineSpy.mockRestore();
  });

  it("shows bundled Algeria vector outline, facility markers, and short note when /api/map-config returns tile_url=null (never calls external OSM)", async () => {
    render(
      <MemoryRouter>
        <EmissionsMap />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("offline-vector-map")).toBeInTheDocument();
      expect(screen.getByText(/Basemap tiles offline/i)).toBeInTheDocument();
    });

    // Must never mount an external openstreetmap.fr tile layer when unconfigured/offline
    expect(mountedTileLayers).toHaveLength(0);
    expect(screen.getByTestId("algeria-vector-outline")).toHaveAttribute("d");
    expect(screen.getByTestId("vector-marker-1")).toHaveAccessibleName(/Facility A-1/i);
    expect(screen.getByTestId("vector-marker-2")).toHaveAccessibleName(/Facility B-2/i);
  });

  it("switches to the bundled Algeria vector fallback when tiles fail to load (tileerror)", async () => {
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/facilities") return Promise.resolve({ data: SAMPLE_FACILITIES });
      if (url.startsWith("/dashboard/intensity-stats")) return Promise.resolve({ data: SAMPLE_STATS });
      if (url === "/dashboard/years") return Promise.resolve({ data: [2024, 2025] });
      if (url === "/data/ogmp-surveys") return Promise.resolve({ data: [] });
      if (url === "/map-config") {
        return Promise.resolve({
          data: {
            tile_url: "https://tiles.example.test/{z}/{x}/{y}.png",
            attribution: "Test Tiles",
            subdomains: "abc",
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter>
        <EmissionsMap />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("leaflet-tile-layer")).toHaveAttribute(
        "data-url",
        "https://tiles.example.test/{z}/{x}/{y}.png",
      );
    });

    act(() => {
      mountedTileLayers[0]?.eventHandlers?.tileerror?.();
    });

    await waitFor(() => {
      expect(screen.getByTestId("offline-vector-map")).toBeInTheDocument();
    });
    expect(screen.getByTestId("algeria-vector-outline")).toHaveAttribute("d");
    expect(screen.getByText(/Basemap tiles offline/i)).toBeInTheDocument();
  });

  it("uses offline vector fallback immediately when network is disabled and opens dossier on marker click", async () => {
    onlineSpy.mockReturnValue(false);
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/facilities") return Promise.resolve({ data: SAMPLE_FACILITIES });
      if (url.startsWith("/dashboard/intensity-stats")) return Promise.resolve({ data: SAMPLE_STATS });
      if (url === "/dashboard/years") return Promise.resolve({ data: [2024, 2025] });
      if (url === "/data/ogmp-surveys") return Promise.resolve({ data: [] });
      if (url === "/map-config") {
        return Promise.resolve({
          data: {
            tile_url: "https://tiles.example.test/{z}/{x}/{y}.png",
            attribution: "Test Tiles",
            subdomains: "abc",
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter>
        <EmissionsMap />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("offline-vector-map")).toBeInTheDocument();
      expect(screen.getByTestId("vector-marker-1")).toBeInTheDocument();
    });
    expect(mountedTileLayers).toHaveLength(0);

    const markerBtn = screen.getByTestId("vector-marker-1");
    fireEvent.click(markerBtn);

    await waitFor(() => {
      expect(screen.getByRole("region", { name: /Facility Reconnaissance Dossier/i })).toBeInTheDocument();
    });
    expect(screen.getAllByText("Facility A-1").length).toBeGreaterThanOrEqual(1);
  });

  it("switches to the vector fallback if browser fires offline event after initial online render", async () => {
    apiGetMock.mockImplementation((url: string) => {
      if (url === "/facilities") return Promise.resolve({ data: SAMPLE_FACILITIES });
      if (url.startsWith("/dashboard/intensity-stats")) return Promise.resolve({ data: SAMPLE_STATS });
      if (url === "/dashboard/years") return Promise.resolve({ data: [2024, 2025] });
      if (url === "/data/ogmp-surveys") return Promise.resolve({ data: [] });
      if (url === "/map-config") {
        return Promise.resolve({
          data: {
            tile_url: "https://tiles.example.test/{z}/{x}/{y}.png",
            attribution: "Test Tiles",
            subdomains: "abc",
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter>
        <EmissionsMap />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("leaflet-tile-layer")).toBeInTheDocument();
    });

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("offline-vector-map")).toBeInTheDocument();
      expect(screen.getByText(/Basemap tiles offline/i)).toBeInTheDocument();
    });
    expect(screen.getByTestId("algeria-vector-outline")).toHaveAttribute("d");
    expect(screen.getByTestId("vector-marker-1")).toHaveAccessibleName(/Facility A-1/i);
  });
});
