# Mutation Testing Audit Report (Phase 5)

- **Total Mutants Evaluated**: 6
- **Killed Mutants**: 6
- **Surviving Mutants**: 0
- **Overall Mutation Score**: 100.0%

## 1. Mutant Evaluation Ledger

| Mutant ID | Target Module | Description | Status | Outcome / Detection |
| :--- | :--- | :--- | :---: | :--- |
| `MUT-01` | `calculations.stoichiometry` | Mutate CO2/C molecular ratio from 44.01/12.011 to 44.0/12.0 | **KILLED** | Killed by test assertion |
| `MUT-02` | `calculations.combustion` | Mutate kg to tonnes conversion divisor (/ 1000.0 to * 1.0) | **KILLED** | Killed by test assertion |
| `MUT-03` | `calculations.combustion` | Mutate destruction slip (1 - eta_d) to (1 + eta_d) | **KILLED** | Killed by test assertion |
| `MUT-04` | `calculations.units` | Mutate lb_to_kg exact constant from 0.45359237 to 0.5 | **KILLED** | Killed by test assertion |
| `MUT-05` | `calculations.constants` | Mutate AR5 CH4 GWP from 28.0 to 25.0 | **KILLED** | Killed by test assertion |
| `MUT-06` | `calculations.indirect` | Mutate net efficiency from b_eff - t_loss to b_eff + t_loss | **KILLED** | Killed by test assertion |
