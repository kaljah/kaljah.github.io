import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import EmissionResult from '../components/EmissionResult';

describe('EmissionResult component', () => {
  const mockResult = {
    calculation_method: 'API Compendium 2021 Tier 1/2',
    record: {
      equipment: 'Boiler #1',
      processType: 'combustion',
      quantity: 1000,
      unit: 'm3',
    },
    emissions: {
      totalCo2e: 95.658,
      co2: 95.56,
      ch4: 0.0018,
      n2o: 0.00018,
      co: 0,
      uncertainty: 0.05,
      uncertaintyCo2: 0.05,
      uncertaintyCh4: 0.15,
      uncertaintyN2o: 0.30,
    },
  };

  it('renders total CO2e correctly', () => {
    render(<EmissionResult result={mockResult} onClose={() => {}} />);
    expect(screen.getByText('95.658')).toBeInTheDocument();
    expect(screen.getByText('Total CO₂e')).toBeInTheDocument();
  });

  it('returns null if result is null', () => {
    const { container } = render(<EmissionResult result={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('calls onClose when close button clicked', () => {
    const handleClose = vi.fn();
    render(<EmissionResult result={mockResult} onClose={handleClose} />);
    const closeBtn = screen.getByText('×');
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
