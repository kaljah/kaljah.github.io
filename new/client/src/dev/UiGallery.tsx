import React, { useState } from "react";
import { Inbox, Plus } from "lucide-react";
import {
  Badge,
  Banner,
  Button,
  Card,
  CardHeader,
  ConfirmDialog,
  DataTable,
  Dialog,
  EmptyState,
  Field,
  FilterBar,
  HelpTip,
  GlossaryHelpTip,
  IconButton,
  Input,
  Menu,
  MenuContent,
  MenuItem,
  MenuTrigger,
  NumberInput,
  Page,
  PageHeader,
  PageSkeleton,
  RadioCardGroup,
  SegmentedControl,
  Select,
  Sheet,
  Skeleton,
  StatCard,
  StatusBadge,
  FlagChip,
  DataHealthBadge,
  OgmpL5Badge,
  TargetTrackingBadge,
  StatusPill,
  Stepper,
  Switch,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
  Tooltip,
  TooltipProvider,
} from "../ui";
import { AdvancedSection } from "../components/AdvancedSection";
import { BarChart, WaterfallChart } from "../components/charts";

// Development-only catalogue of design tokens and components (route /__ui).
const SWATCHES: [string, string][] = [
  ["brand-500", "var(--color-brand-500)"],
  ["brand-600", "var(--color-brand-600)"],
  ["brand-700 (primary)", "var(--color-brand-700)"],
  ["brand-teal (secondary)", "var(--color-brand-teal)"],
  ["scope-1 (deep orange)", "var(--color-scope-1)"],
  ["scope-2 (blue)", "var(--color-scope-2)"],
  ["scope-3 (violet)", "var(--color-scope-3)"],
  ["ink-900 (text)", "var(--color-ink-900)"],
  ["ink-600", "var(--color-ink-600)"],
  ["ink-500 (placeholder)", "var(--color-ink-500)"],
  ["ink-200 (border)", "var(--color-ink-200)"],
  ["green-600 (unc-low)", "var(--color-green-600)"],
  ["green-700 (text)", "var(--color-green-700)"],
  ["amber-500 (unc-med)", "var(--color-amber-500)"],
  ["amber-700 (text)", "var(--color-amber-700)"],
  ["red-600 (unc-high)", "var(--color-red-600)"],
  ["red-700 (text)", "var(--color-red-700)"],
];

const lin = (c: number): number => {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
};

const lum = (hex: string): number => {
  const [r, g, b] = [1, 3, 5].map((i) => lin(parseInt(hex.slice(i, i + 2), 16)));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

const contrast = (a: string, b: string): string => {
  const [x, y] = [lum(a), lum(b)];
  return ((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)).toFixed(2);
};

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, children }) => (
  <Card className="flex flex-col gap-4">
    <CardHeader title={title} className="mb-0" />
    {children}
  </Card>
);

interface ExampleRow {
  name: string;
  co2e: number;
  status: string;
}

const rows: ExampleRow[] = [
  { name: "Stationary combustion", co2e: 1234.567, status: "Verified" },
  { name: "Flaring", co2e: 88.1, status: "Pending" },
  { name: "Venting", co2e: 660943.175, status: "Draft" },
];

const columns: any[] = [
  { accessorKey: "name", header: "Source" },
  { accessorKey: "co2e", header: "CO2e", meta: { numeric: true, unit: "t" }, cell: (c: any) => c.getValue().toLocaleString() },
  { accessorKey: "status", header: "Status", cell: (c: any) => <StatusPill status={c.getValue()} /> },
];

const UiGallery: React.FC = () => {
  const [gwp, setGwp] = useState<string>("100");
  const [std, setStd] = useState<string>("ar5");
  const [on, setOn] = useState<boolean>(true);
  const [dialog, setDialog] = useState<boolean>(false);
  const [sheet, setSheet] = useState<boolean>(false);
  const [drawerDemoOpen, setDrawerDemoOpen] = useState<boolean>(false);
  const [confirm, setConfirm] = useState<boolean>(false);
  const [sel, setSel] = useState<string>("a");

  return (
    <TooltipProvider>
      <Page>
        <PageHeader
          eyebrow="Development"
          title="UI gallery"
          description="Design tokens and shared components. Only available in development builds."
          actions={<Button>Primary action</Button>}
        />

        <Section title="Colors and contrast on white">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
            {SWATCHES.map(([name, hex]) => (
              <div key={name} className="overflow-hidden rounded-md border border-border">
                {/* eslint-disable-next-line no-restricted-syntax -- swatch shows the literal color */}
                <div style={{ background: hex }} className="h-12" />
                <div className="p-2 text-xs">
                  <p className="font-semibold text-text">{name}</p>
                  <p className="text-text-secondary">
                    {hex} &middot; {contrast(hex, "var(--color-white)")}:1
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Type scale">
          <p className="text-3xl text-text">text-3xl Emissions overview</p>
          <p className="text-2xl text-text">text-2xl Emissions overview</p>
          <p className="text-xl text-text">text-xl Emissions overview</p>
          <p className="text-lg text-text">text-lg Emissions overview</p>
          <p className="text-md text-text">text-md Emissions overview</p>
          <p className="text-base text-text">text-base Emissions overview</p>
          <p className="text-sm text-text">text-sm Emissions overview</p>
          <p className="text-xs text-text">text-xs Emissions overview</p>
        </Section>

        <Section title="Buttons">
          <div className="flex flex-wrap items-center gap-2">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
            <Button variant="link">Link</Button>
            <Button loading>Loading</Button>
            <Button disabled>Disabled</Button>
            <Button size="sm">Small</Button>
            <Button size="lg">Large</Button>
            <IconButton label="Example icon button">
              <Inbox className="size-5" aria-hidden="true" />
            </IconButton>
          </div>
        </Section>

        <Section title="Badges, statuses, banners">
          <div className="flex flex-wrap gap-2 items-center">
            <Badge>Neutral</Badge>
            <Badge tone="brand">Brand</Badge>
            <Badge tone="success">Success</Badge>
            <Badge tone="warning">Warning</Badge>
            <Badge tone="danger">Danger</Badge>
            <Badge tone="info">Info</Badge>
          </div>

          <div className="flex flex-col gap-2 mt-2">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider m-0">
              Single-Source StatusBadge (Phase A2 Canonical Enum)
            </h4>
            <div className="flex flex-wrap gap-2 items-center">
              <StatusBadge status="Draft" />
              <StatusBadge status="Pending review" />
              <StatusBadge status="Verified" />
              <StatusBadge status="Rejected" />
              <StatusBadge status="Flagged" />
              <StatusBadge status="Reconciled" />
              <StatusBadge status="Discrepancy" />
              <FlagChip label="Outlier (+3.2σ)" severity="danger" />
              <FlagChip label="Missing factor docs" severity="warning" />
            </div>
          </div>

          <div className="flex flex-col gap-2 mt-2">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider m-0">
              Derived Page-Level Badges (Computed from Underlying Data)
            </h4>
            <div className="flex flex-wrap gap-2 items-center">
              <DataHealthBadge cleanRatio={0.99} totalRecords={150} />
              <DataHealthBadge cleanRatio={0.93} totalRecords={150} />
              <DataHealthBadge cleanRatio={0.82} totalRecords={150} />
              <OgmpL5Badge reconciledCount={14} discrepancyCount={0} />
              <OgmpL5Badge reconciledCount={11} discrepancyCount={3} />
              <TargetTrackingBadge actual={850} target={1000} />
              <TargetTrackingBadge actual={1120} target={1000} />
            </div>
          </div>

          <Banner tone="info" title="Information">
            Neutral message.
          </Banner>
          <Banner tone="success" title="Saved">
            The record was saved.
          </Banner>
          <Banner tone="warning" title="Pending review">
            12 records await approval.
          </Banner>
          <Banner tone="danger" title="Failed">
            The upload could not be processed.
          </Banner>
        </Section>

        <Section title="Jargon & Methodology HelpTip (Phase A5)">
          <p className="text-sm text-text-secondary m-0">
            Interactive glossary tooltips accessible via keyboard and touch (bottom sheet on mobile):
          </p>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            <div className="flex items-center justify-between p-3 rounded-md border border-border bg-surface">
              <span className="text-sm font-medium text-text">IPCC Tiers</span>
              <GlossaryHelpTip term="Tier 1/2/3" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-md border border-border bg-surface">
              <span className="text-sm font-medium text-text">SRSS Uncertainty</span>
              <GlossaryHelpTip term="SRSS" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-md border border-border bg-surface">
              <span className="text-sm font-medium text-text">OGMP 2.0 Levels</span>
              <GlossaryHelpTip term="OGMP 2.0 L1-L5" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-md border border-border bg-surface">
              <span className="text-sm font-medium text-text">Gold Standard</span>
              <GlossaryHelpTip term="Gold Standard pathway" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-md border border-border bg-surface">
              <span className="text-sm font-medium text-text">GWP Standard</span>
              <GlossaryHelpTip term="GWP-100/20" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-md border border-border bg-surface">
              <span className="text-sm font-medium text-text">Maker-Checker</span>
              <GlossaryHelpTip term="Maker-Checker" />
            </div>
          </div>
        </Section>

        <Section title="Stat cards">
          <div className="grid gap-4 md:grid-cols-3">
            <StatCard
              label="Gross emissions"
              value={660943.175}
              unit="tCO2e"
              delta={{ value: -0.042, goodWhen: "down", label: "vs 2025" }}
            />
            <StatCard label="Methane" value={23604.7} unit="tCH4" footnote="OGMP 2.0 Level 3" />
            <StatCard label="Loading" value={0} loading />
          </div>
        </Section>

        <Section title="Form controls">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Facility name" hint="As registered in Manage Data" required>
              <Input placeholder="e.g. West facility" />
            </Field>
            <Field label="Quantity" error="Enter a positive number">
              <NumberInput unit="m3" defaultValue="-1" />
            </Field>
            <Field label="Notes">
              <Textarea />
            </Field>
            <div className="flex flex-col gap-4">
              <Switch label="Preview pending records" checked={on} onChange={(e) => setOn(e.target.checked)} />
              <SegmentedControl
                label="GWP horizon"
                value={gwp}
                onChange={setGwp}
                options={[
                  { value: "100", label: "GWP-100" },
                  { value: "20", label: "GWP-20" },
                ]}
              />
              <Select
                aria-label="Process"
                value={sel}
                onChange={setSel}
                options={[
                  { value: "a", label: "Stationary combustion" },
                  { value: "b", label: "Flaring" },
                ]}
              />
            </div>
          </div>
          <RadioCardGroup
            label="GWP standard"
            value={std}
            onChange={setStd}
            options={[
              { value: "ar4", title: "AR4", description: "Legacy frameworks" },
              {
                value: "ar5",
                title: "AR5",
                description: "UNFCCC / EU standard",
                badge: <Badge tone="success">Active</Badge>,
              },
              { value: "ar6", title: "AR6", description: "Latest science" },
            ]}
          />
          <FilterBar activeCount={2} onReset={() => {}}>
            <Badge>Year: 2026</Badge>
            <Badge>Region: rz</Badge>
          </FilterBar>
          <Stepper steps={["Upload", "Map columns", "Review"]} current={1} />
        </Section>

        <Section title="Tabs, table, empty state">
          <Tabs defaultValue="one">
            <TabsList>
              <TabsTrigger value="one">Overview</TabsTrigger>
              <TabsTrigger value="two" badge={3}>
                Pending review
              </TabsTrigger>
            </TabsList>
            <TabsContent value="one">
              <DataTable tableId="gallery" columns={columns} data={rows} caption="Example emissions" />
            </TabsContent>
            <TabsContent value="two">
              <EmptyState icon={Inbox} title="Nothing to review" description="All records are verified." />
            </TabsContent>
          </Tabs>
        </Section>

        <Section title="Overlays and menus">
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setDialog(true)}>
              Dialog
            </Button>
            <Button variant="secondary" onClick={() => setSheet(true)}>
              Side panel
            </Button>
            <Button variant="secondary" onClick={() => setConfirm(true)}>
              Confirm
            </Button>
            <Menu>
              <MenuTrigger asChild>
                <Button variant="secondary">Menu</Button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem>Excel export</MenuItem>
                <MenuItem danger>Delete</MenuItem>
              </MenuContent>
            </Menu>
            <Tooltip content="Tooltip text">
              <Button variant="ghost">Hover or focus me</Button>
            </Tooltip>
          </div>
          <Dialog
            open={dialog}
            onOpenChange={setDialog}
            title="Example dialog"
            description="Focus is trapped and returned."
            footer={<Button onClick={() => setDialog(false)}>Done</Button>}
          >
            <p className="text-base text-text">Dialog body.</p>
          </Dialog>
          <Sheet
            open={sheet}
            onOpenChange={setSheet}
            title="Example panel"
            footer={<Button onClick={() => setSheet(false)}>Close</Button>}
          >
            <p className="text-base text-text">Panel body.</p>
          </Sheet>
          <ConfirmDialog
            open={confirm}
            title="Delete record?"
            message="This cannot be undone."
            confirmLabel="Delete"
            onConfirm={() => setConfirm(false)}
            onCancel={() => setConfirm(false)}
          />
        </Section>

        <Section title="Drawer Form with Progressive Disclosure (Phase B3 & B4)">
          <div className="flex flex-col gap-3">
            <p className="text-sm text-text-secondary m-0">
              Table-first pattern: data forms are housed in a sliding drawer on desktop (modal sheet on mobile) with essential fields first and collapsible AdvancedSection with field counts and memory.
            </p>
            <div>
              <Button onClick={() => setDrawerDemoOpen(true)}>
                <Plus className="size-4" />
                Open Example Form Drawer
              </Button>
            </div>
          </div>
          <Sheet
            open={drawerDemoOpen}
            onOpenChange={setDrawerDemoOpen}
            title="Add Emission Factor"
            description="Register a custom emission factor with uncertainty bounds."
            width="38rem"
            footer={
              <div className="flex justify-end gap-2 w-full">
                <Button variant="secondary" onClick={() => setDrawerDemoOpen(false)}>Cancel</Button>
                <Button onClick={() => setDrawerDemoOpen(false)}>Save Factor</Button>
              </div>
            }
          >
            <div className="flex flex-col gap-5">
              <div className="flex flex-col gap-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 pb-1 border-b border-border/60">
                  Essential Factor Data
                </h4>
                <Field label="Fuel / Activity Name" required>
                  <Input placeholder="e.g. Algerian Natural Gas" />
                </Field>
                <Field label="CO2 Factor (kg/unit)" required>
                  <NumberInput defaultValue="2.145" />
                </Field>
              </div>
              <AdvancedSection id="gallery-advanced-demo" title="Uncertainty & Technical Metadata" fieldCount={3}>
                <Field label="Uncertainty Range (± %)" hint="95% confidence interval half-width">
                  <NumberInput defaultValue="7.5" unit="%" />
                </Field>
                <Field label="Sampling Campaign Date">
                  <Input type="date" defaultValue="2026-03-15" />
                </Field>
                <Field label="Laboratory Certificate ID">
                  <Input placeholder="e.g. CERT-2026-ALG-089" />
                </Field>
              </AdvancedSection>
            </div>
          </Sheet>
        </Section>

        <Section title="Chart Palettes & Threshold Bands (Phase C2 & C3)">
          <div className="flex flex-col gap-4">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 mb-2">
                Unified Scope Color Hierarchy (Phase C2)
              </h4>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="p-3 rounded-lg border border-border bg-surface border-l-4 border-l-brand-700">
                  <p className="text-xs font-semibold text-brand-700 m-0">Scope 1 (Direct)</p>
                  <p className="text-sm font-bold text-text mt-1">Deep Orange · var(--color-scope-1)</p>
                </div>
                <div className="p-3 rounded-lg border border-border bg-surface border-l-4 border-l-blue-600">
                  <p className="text-xs font-semibold text-blue-700 m-0">Scope 2 (Electricity)</p>
                  <p className="text-sm font-bold text-text mt-1">Blue · var(--color-scope-2)</p>
                </div>
                <div className="p-3 rounded-lg border border-border bg-surface border-l-4 border-l-violet-600">
                  <p className="text-xs font-semibold text-violet-700 m-0">Scope 3 (Value Chain)</p>
                  <p className="text-sm font-bold text-text mt-1">Violet · var(--color-scope-3)</p>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 mb-2">
                Threshold-Based Bar Chart (&le;10% green, 10-30% amber, &gt;30% red per Phase C3)
              </h4>
              <div className="h-[280px] w-full">
                <BarChart
                  data={[
                    { name: "Berkine Basin", value: 0.12 },
                    { name: "Hassi Messaoud", value: 0.19 },
                    { name: "Hassi R'Mel", value: 0.28 },
                    { name: "Rhourde Nouss", value: 0.35 },
                  ]}
                  dataKey="value"
                  xKey="name"
                  height={250}
                  horizontal
                  sortDesc
                  thresholds={{
                    warnAt: 0.16,
                    badAt: 0.20,
                    labels: ["Within target (<=0.16%)", "Moderate risk (0.16 - 0.20%)", "Above limit (>0.20%)"],
                  }}
                  referenceValue={0.20}
                  referenceLabel="OGMP 2.0 Target (0.20%)"
                  formatValue={(v) => `${(Number(v) * 100).toFixed(1)}%`}
                />
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 mb-2">
                Waterfall Bridge (Ink Total, Red Increase, Green Reduction)
              </h4>
              <div className="h-[280px] w-full">
                <WaterfallChart
                  startLabel="2025 Start"
                  endLabel="2026 Current"
                  start={1200}
                  end={1050}
                  steps={[
                    { name: "Flaring reduction", delta: -220 },
                    { name: "Compressor venting", delta: 130 },
                    { name: "LDAR repair campaign", delta: -60 },
                  ]}
                  height={250}
                  formatValue={(v) => `${Number(v).toFixed(0)} t`}
                />
              </div>
            </div>
          </div>
        </Section>

        <Section title="Loading placeholder">
          <PageSkeleton />
        </Section>
      </Page>
    </TooltipProvider>
  );
};

export default UiGallery;
