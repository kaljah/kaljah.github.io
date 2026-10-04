import React, { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Modal from "../../components/Modal";
import CustomDropdown from "../../components/CustomDropdown";

const Demo = ({ onClose, onPick }) => {
  const [v, setV] = useState("a");
  return (
    <Modal isOpen onClose={onClose} title="With dropdown">
      <CustomDropdown
        aria-label="Process"
        value={v}
        onChange={(x) => {
          setV(x);
          onPick(x);
        }}
        options={[
          { value: "a", label: "Combustion" },
          { value: "b", label: "Flaring" },
        ]}
      />
    </Modal>
  );
};

describe("CustomDropdown inside Modal", () => {
  it("selecting an option from the body portal does not close the dialog", async () => {
    const onClose = vi.fn();
    const onPick = vi.fn();
    render(<Demo onClose={onClose} onPick={onPick} />);
    await userEvent.click(screen.getByRole("button", { name: /Process|Combustion/ }));
    await userEvent.click(await screen.findByRole("option", { name: "Flaring" }));
    expect(onPick).toHaveBeenCalledWith("b");
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog", { name: "With dropdown" })).toBeInTheDocument();
  });
});
