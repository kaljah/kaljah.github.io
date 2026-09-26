import { describe, it, expect } from 'vitest';
import { formatNumber, formatCompactNumber, calculateTrend } from '../utils/formatters';
import { convertActivityData } from '../utils/emissionFactorsAPI';
import { API_FACTORS } from '../utils/EmissionFactors';

describe('Client Math Parity and Formatters Tests', () => {
  it('normalizes negative zero in formatters', () => {
    expect(formatNumber(-0.00001, 3)).toBe('0.000');
    expect(formatNumber(0, 3)).toBe('0.000');
    expect(formatCompactNumber(-0.00001, 1)).toBe('0');
  });

  it('correctly calculates trend percentage', () => {
    expect(calculateTrend(110, 100)).toBe('+10.0%');
    expect(calculateTrend(90, 100)).toBe('-10.0%');
    expect(calculateTrend(100, 0)).toBe('—');
  });

  it('converts units bidirectionally in convertActivityData', () => {
    // bbl to m3 and m3 to bbl
    const bbl = 100;
    const m3 = convertActivityData(bbl, 'bbl', 'm3');
    expect(m3).toBeCloseTo(15.89873, 3);
    const roundtripBbl = convertActivityData(m3, 'm3', 'bbl');
    expect(roundtripBbl).toBeCloseTo(100, 1);

    // lb to kg and kg to lb
    const lb = 1000;
    const kg = convertActivityData(lb, 'lb', 'kg');
    expect(kg).toBeCloseTo(453.592, 1);
    const roundtripLb = convertActivityData(kg, 'kg', 'lb');
    expect(roundtripLb).toBeCloseTo(1000, 1);

    // mmscf to scf
    expect(convertActivityData(1.5, 'mmscf', 'scf')).toBe(1500000);
    expect(convertActivityData(500000, 'scf', 'mmscf')).toBe(0.5);
  });

  it('aligns mud degassing emission factors with API Section 6.2', () => {
    const waterMud = API_FACTORS["Drilling - Mud Degassing (Water Based)"];
    expect(waterMud).toBeDefined();
    expect(waterMud.ch4).toBe(0.0458);
    expect(waterMud.unit).toBe("t CH4/day");

    const oilMud = API_FACTORS["Drilling - Mud Degassing (Oil Based)"];
    expect(oilMud).toBeDefined();
    expect(oilMud.ch4).toBe(0.0103);
    expect(oilMud.unit).toBe("t CH4/day");
  });

  it('aligns TEG dehydrator emission factors with backend', () => {
    const noCtrl = API_FACTORS["Dehydrator - TEG (No Controls)"];
    expect(noCtrl).toBeDefined();
    expect(noCtrl.ch4).toBe(3.0);

    const flash = API_FACTORS["Dehydrator - TEG (Flash Tank)"];
    expect(flash).toBeDefined();
    expect(flash.ch4).toBe(1.2);

    const cond = API_FACTORS["Dehydrator - TEG (Condenser)"];
    expect(cond).toBeDefined();
    expect(cond.ch4).toBe(0.3);
  });
});
