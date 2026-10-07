import '@testing-library/jest-dom/vitest';

class MockResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

if (typeof window !== 'undefined') {
  (window as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
    (window as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver || MockResizeObserver;
}
