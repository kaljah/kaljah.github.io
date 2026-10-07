import React, { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  Banner,
  Button,
  DataTable,
  Field,
  IconButton,
  Input,
  Num,
  SegmentedControl,
  StatCard,
  StatusPill,
  Switch,
  Unit,
  cn,
} from "..";
import Modal from "../../components/Modal";
import ConfirmModal from "../../components/ConfirmModal";

describe("cn", () => {
  it("merges conflicting utilities and keeps token font sizes distinct from colors", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
    expect(cn("text-sm", "text-md")).toBe("text-md");
    expect(cn("text-md", "text-brand-700")).toBe("text-md text-brand-700");
  });
});

describe("Button", () => {
  it("renders variants, fires clicks, and is disabled while loading", async () => {
    const onClick = vi.fn();
    const { rerender } = render(<Button onClick={onClick}>Save</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    rerender(
      <Button onClick={onClick} loading>
        Save
      </Button>,
    );
    const btn = screen.getByRole("button", { name: "Save" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
  });

  it("IconButton uses label as its accessible name", () => {
    render(<IconButton label="Close panel">x</IconButton>);
    expect(screen.getByRole("button", { name: "Close panel" })).toBeInTheDocument();
  });

  it("asChild renders the child element with button styles", () => {
    render(
      <Button asChild>
        <a href="/x">Go</a>
      </Button>,
    );
    expect(screen.getByRole("link", { name: "Go" })).toHaveAttribute("href", "/x");
  });
});

describe("StatusPill / Banner", () => {
  it("always shows the status text", () => {
    render(<StatusPill status="Pending" />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("uses role alert for danger and status otherwise", () => {
    const { rerender } = render(<Banner tone="danger">Failed</Banner>);
    expect(screen.getByRole("alert")).toHaveTextContent("Failed");
    rerender(<Banner tone="info">FYI</Banner>);
    expect(screen.getByRole("status")).toHaveTextContent("FYI");
  });
});

describe("Field", () => {
  it("links label, hint and error to the control", () => {
    const { rerender } = render(
      <Field label="Quantity" hint="Volume in period">
        <Input />
      </Field>,
    );
    const input = screen.getByLabelText("Quantity");
    expect(input).toHaveAccessibleDescription("Volume in period");
    rerender(
      <Field label="Quantity" error="Required" required>
        <Input />
      </Field>,
    );
    const invalid = screen.getByLabelText(/Quantity/);
    expect(invalid).toHaveAttribute("aria-invalid", "true");
    expect(invalid).toHaveAccessibleDescription("Required");
  });

  it("Switch exposes role switch with a name", async () => {
    const Demo = () => {
      const [on, setOn] = useState(false);
      return <Switch label="Preview pending" checked={on} onChange={(e) => setOn(e.target.checked)} />;
    };
    render(<Demo />);
    const sw = screen.getByRole("switch", { name: "Preview pending" });
    await userEvent.click(sw);
    expect(sw).toBeChecked();
  });
});

describe("SegmentedControl", () => {
  const Demo = ({ onChange }: { onChange?: (val: string) => void }) => {
    const [v, setV] = useState("100");
    return (
      <SegmentedControl
        label="GWP horizon"
        value={v}
        onChange={(x: any) => {
          setV(x);
          onChange?.(x);
        }}
        options={[
          { value: "100", label: "GWP-100" },
          { value: "20", label: "GWP-20" },
        ]}
      />
    );
  };

  it("is a radiogroup with roving tabindex and arrow-key navigation", async () => {
    const onChange = vi.fn();
    render(<Demo onChange={onChange} />);
    expect(screen.getByRole("radiogroup", { name: "GWP horizon" })).toBeInTheDocument();
    const first = screen.getByRole("radio", { name: "GWP-100" });
    const second = screen.getByRole("radio", { name: "GWP-20" });
    expect(first).toHaveAttribute("tabindex", "0");
    expect(second).toHaveAttribute("tabindex", "-1");
    first.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenCalledWith("20");
    expect(second).toHaveAttribute("aria-checked", "true");
    expect(second).toHaveFocus();
  });
});

describe("Num / Unit / StatCard", () => {
  it("formats numbers and normalizes units", () => {
    render(
      <p>
        <Num value={660943.175} format="compact" /> <Unit>tCO2e</Unit>
      </p>,
    );
    expect(screen.getByText("660.9K")).toHaveAttribute("title", "660,943.175");
    expect(screen.getByText("tCO₂e")).toBeInTheDocument();
  });

  it("colors only the delta and marks decreases as good when goodWhen is down", () => {
    render(<StatCard label="Gross" value={1000} unit="tCO2e" delta={{ value: -0.05, goodWhen: "down" }} />);
    const delta = screen.getByText("5.0%").closest("span[class*='inline-flex']");
    expect(delta?.className).toMatch(/text-success-fg/);
  });
});

describe("Dialog adapters", () => {
  it("Modal is an accessible dialog that closes on Escape", async () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen onClose={onClose} title="Create report">
        <button>Inside</button>
      </Modal>,
    );
    const dialog = screen.getByRole("dialog", { name: "Create report" });
    expect(within(dialog).getByRole("button", { name: "Inside" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("ConfirmModal calls onConfirm and onCancel", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        isOpen
        title="Delete?"
        message="Really?"
        confirmLabel="Delete"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("renders nothing when closed", () => {
    render(<Modal isOpen={false} onClose={() => {}} title="Hidden" />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("DataTable", () => {
  const columns: any[] = [
    { accessorKey: "name", header: "Name" },
    { accessorKey: "co2e", header: "CO2e", meta: { numeric: true } },
    { accessorKey: "note", header: "Note" },
  ];
  const data = [
    { name: "B", co2e: 2, note: "n1" },
    { name: "A", co2e: 10, note: "n2" },
  ];

  it("renders rows, sorts on header click, and right-aligns numeric cells", async () => {
    render(<DataTable columns={columns} data={data} />);
    const rows = () => screen.getAllByRole("row").slice(1);
    expect(rows()[0]).toHaveTextContent("B");
    await userEvent.click(screen.getByRole("button", { name: /Name/ }));
    expect(rows()[0]).toHaveTextContent("A");
    expect(screen.getByText("10").className).toMatch(/text-right/);
  });

  it("hides default-hidden columns and offers them in the Columns menu", async () => {
    render(<DataTable tableId="test-hidden" columns={columns} data={data} defaultHidden={["note"]} />);
    expect(screen.queryByRole("columnheader", { name: /Note/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Columns/ }));
    await userEvent.click(await screen.findByRole("menuitemcheckbox", { name: /Note/ }));
    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("columnheader", { name: /Note/ })).toBeInTheDocument();
  });

  it("shows an empty state when there are no rows", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("No records")).toBeInTheDocument();
  });
});
