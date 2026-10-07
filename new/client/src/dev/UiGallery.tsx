import React, { useState } from "react";
import { Inbox } from "lucide-react";
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
  StatCard,
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

// Development-only catalogue of design tokens and components (route /__ui).
const SWATCHES: [string, string][] = [
  ["brand-500", "#ff6600"],
  ["brand-600", "#e65c00"],
  ["brand-700", "#c2410c"],
  ["brand-50", "#fff7ed"],
  ["ink-900", "#0f172a"],
  ["ink-600", "#475569"],
  ["ink-500", "#64748b"],
  ["ink-400", "#94a3b8"],
  ["ink-200", "#e2e8f0"],
  ["ink-100", "#f1f5f9"],
  ["green-500", "#10b981"],
  ["green-700", "#2e7d32"],
  ["blue-500", "#3b82f6"],
  ["blue-700", "#1d4ed8"],
  ["amber-500", "#f59e0b"],
  ["amber-700", "#b45309"],
  ["red-500", "#ef4444"],
  ["red-700", "#b91c1c"],
  ["violet-500", "#8b5cf6"],
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
                    {hex} &middot; {contrast(hex, "#ffffff")}:1
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
          <div className="flex flex-wrap gap-2">
            <Badge>Neutral</Badge>
            <Badge tone="brand">Brand</Badge>
            <Badge tone="success">Success</Badge>
            <Badge tone="warning">Warning</Badge>
            <Badge tone="danger">Danger</Badge>
            <Badge tone="info">Info</Badge>
            <StatusPill status="Verified" />
            <StatusPill status="Pending" />
            <StatusPill status="Draft" />
            <StatusPill status="Rejected" />
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

        <Section title="Loading placeholder">
          <PageSkeleton />
        </Section>
      </Page>
    </TooltipProvider>
  );
};

export default UiGallery;
