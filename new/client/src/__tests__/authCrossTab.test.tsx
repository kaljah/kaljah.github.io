import React from "react";
import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../context/AuthContext";
import api from "../api";

vi.mock("../api", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
  fetchCsrfToken: vi.fn(() => Promise.resolve()),
}));

// In-memory BroadcastChannel: messages reach every other channel of the same name.
class FakeChannel {
  static all: FakeChannel[] = [];
  onmessage: ((e: MessageEvent) => void) | null = null;
  constructor(public name: string) {
    FakeChannel.all.push(this);
  }
  postMessage(data: unknown) {
    FakeChannel.all
      .filter((c) => c !== this && c.name === this.name)
      .forEach((c) => c.onmessage?.({ data } as MessageEvent));
  }
  close() {
    FakeChannel.all = FakeChannel.all.filter((c) => c !== this);
  }
}

describe("AuthContext cross-tab session (audit 2026-10-14 BUG-0014 / BUG-0039)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeChannel.all = [];
    vi.stubGlobal("BroadcastChannel", FakeChannel);
    vi.mocked(api.get).mockImplementation((url: string) =>
      Promise.resolve({ data: url === "/auth/me" ? { id: 7, role: "admin", email: "a@x" } : {} }),
    );
    vi.mocked(api.post).mockResolvedValue({ data: {} });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("activity in another tab keeps this tab signed in", async () => {
    render(<AuthProvider><div /></AuthProvider>);
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    const otherTab = new FakeChannel("ghg_auth_channel");

    await act(async () => { await vi.advanceTimersByTimeAsync(9.5 * 60 * 1000); });
    act(() => otherTab.postMessage({ type: "ACTIVITY", timestamp: Date.now() }));
    await act(async () => { await vi.advanceTimersByTimeAsync(1.5 * 60 * 1000); });

    expect(api.post).not.toHaveBeenCalledWith("/auth/logout");
  });

  it("this tab still signs out after 10 idle minutes in every tab", async () => {
    render(<AuthProvider><div /></AuthProvider>);
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    await act(async () => { await vi.advanceTimersByTimeAsync(10 * 60 * 1000 + 10); });
    expect(api.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("a sign-in with another account in another tab reloads this tab", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    render(<AuthProvider><div /></AuthProvider>);
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    const otherTab = new FakeChannel("ghg_auth_channel");
    act(() => otherTab.postMessage({ type: "LOGIN", userId: 7 }));
    expect(assign).not.toHaveBeenCalled();
    act(() => otherTab.postMessage({ type: "LOGIN", userId: 8 }));
    expect(assign).toHaveBeenCalledWith("/");
  });
});
