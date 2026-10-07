// API Compendium 2021 Table 6-8: associated gas venting basin factors (used by the Tier 1 form)
export interface Table68Basin {
  value: string;
  label: string;
  basinKey: string;
  ef_ch4_kg_bbl: number;
  whole_gas_scf_bbl: number;
  ch4_mol_basis: number;
}

export const TABLE_6_8_BASINS: Table68Basin[] = [
  {
    value: "Associated Gas Venting - US Average",
    label: "US Average",
    basinKey: "us_average",
    ef_ch4_kg_bbl: 1.4,
    whole_gas_scf_bbl: 89.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Gulf Coast Basin (Basin 220)",
    label: "Gulf Coast Basin - Basin 220",
    basinKey: "gulf_coast",
    ef_ch4_kg_bbl: 0.7,
    whole_gas_scf_bbl: 47.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Anadarko Basin (Basin 360)",
    label: "Anadarko Basin - Basin 360",
    basinKey: "anadarko",
    ef_ch4_kg_bbl: 9.7,
    whole_gas_scf_bbl: 622.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Williston Basin (Basin 395)",
    label: "Williston Basin - Basin 395",
    basinKey: "williston",
    ef_ch4_kg_bbl: 8.9,
    whole_gas_scf_bbl: 570.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Permian Basin (Basin 430)",
    label: "Permian Basin - Basin 430",
    basinKey: "permian",
    ef_ch4_kg_bbl: 6.5,
    whole_gas_scf_bbl: 419.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Other US Basins",
    label: "Other US Basins",
    basinKey: "other",
    ef_ch4_kg_bbl: 0.4,
    whole_gas_scf_bbl: 26.0,
    ch4_mol_basis: 81.6,
  },
];
