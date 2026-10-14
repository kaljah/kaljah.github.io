// A heating value entered in the form -> (Btu value, its basis). Gas volume units go to Btu/scf (the
// flaring and venting paths read the HHV as Btu/scf), liquid ones to Btu/gal, mass ones to Btu/lb.
export interface HhvBtu {
  hhv: number;
  hhvUnit: "BTU/scf" | "BTU/gal" | "BTU/lb";
}

// Exact factors, equal to the server's calculations/units.py (1 MJ = 947.81712 Btu, 1 m3 = 35.3146667 scf,
// 1 kg = 2.20462262 lb, 1 kcal = 4184 J)
const BTU_PER_MJ = 947.8171203133172;
const SCF_PER_M3 = 35.314666721;
const LB_PER_KG = 2.2046226218487757;
const BTU_PER_KCAL = 4184 / 1055.05585262;

export const hhvToBtu = (value: number, unit: string): HhvBtu => {
  switch (unit) {
    case "MJ/m3":
      return { hhv: (value * BTU_PER_MJ) / SCF_PER_M3, hhvUnit: "BTU/scf" };
    case "kcal/m3":
      return { hhv: (value * BTU_PER_KCAL) / SCF_PER_M3, hhvUnit: "BTU/scf" };
    case "MJ/kg":
      return { hhv: (value * BTU_PER_MJ) / LB_PER_KG, hhvUnit: "BTU/lb" };
    case "BTU/gal":
      return { hhv: value, hhvUnit: "BTU/gal" };
    case "BTU/lb":
      return { hhv: value, hhvUnit: "BTU/lb" };
    default:
      return { hhv: value, hhvUnit: "BTU/scf" };
  }
};
