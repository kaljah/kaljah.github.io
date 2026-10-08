// A heating value entered in the form -> (Btu value, its basis). Gas volume units go to Btu/scf (the
// flaring and venting paths read the HHV as Btu/scf), liquid ones to Btu/gal, mass ones to Btu/lb.
export interface HhvBtu {
  hhv: number;
  hhvUnit: "BTU/scf" | "BTU/gal" | "BTU/lb";
}

export const hhvToBtu = (value: number, unit: string): HhvBtu => {
  switch (unit) {
    case "MJ/m3":
      return { hhv: (value * 947.817) / 35.3147, hhvUnit: "BTU/scf" };
    case "kcal/m3":
      return { hhv: (value * 3.96567) / 35.3147, hhvUnit: "BTU/scf" };
    case "MJ/kg":
      return { hhv: (value * 947.817) / 2.20462, hhvUnit: "BTU/lb" };
    case "BTU/gal":
      return { hhv: value, hhvUnit: "BTU/gal" };
    case "BTU/lb":
      return { hhv: value, hhvUnit: "BTU/lb" };
    default:
      return { hhv: value, hhvUnit: "BTU/scf" };
  }
};
