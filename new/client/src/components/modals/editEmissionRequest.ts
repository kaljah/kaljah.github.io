/**
 * Which endpoint an edited record goes to, and with which fields.
 *
 * Records reach the edit dialog from the Reports and Review lists, whose ids carry their scope
 * (s1_12, s2_7, s3_28). Each scope has its own table and its own update route: a Scope 3 record
 * sent to /emissions/<n> would be read as Scope 1 record <n>.
 */
export interface EditFormData {
  year: number | string;
  month: number | string;
  facility_id: string;
  process_type: string;
  fuel: string;
  amount: number | string;
  unit: string;
  electricity_kwh?: number | string;
  grid_region?: string;
  market_instrument_type?: string;
  market_emission_factor?: number | string;
}

export type EditScope = 1 | 2 | 3;

export function editScope(emission: { id?: unknown; scope?: unknown; grid_region?: unknown }): EditScope {
  const id = String(emission.id ?? "");
  if (id.startsWith("s3_")) return 3;
  if (id.startsWith("s2_")) return 2;
  if (id.startsWith("s1_")) return 1;
  const scope = Number(String(emission.scope ?? "").replace(/\D/g, ""));
  if (scope === 3) return 3;
  if (scope === 2 || emission.grid_region) return 2;
  return 1;
}

export function editRequest(
  emission: { id?: unknown; scope?: unknown; grid_region?: unknown },
  form: EditFormData,
): { scope: EditScope; url: string; payload: Record<string, unknown> } {
  const scope = editScope(emission);
  const id = String(emission.id).replace(/^s[123]_/, "");
  const payload: Record<string, unknown> = {
    year: Number(form.year),
    facility_id: form.facility_id ? Number(form.facility_id) : undefined,
  };

  if (scope === 3) {
    // Scope 3 records are yearly; the category and sub-category show in the process / source fields.
    payload.category = form.process_type || undefined;
    payload.sub_category = form.fuel || undefined;
    payload.activity_data = Number(form.amount);
    payload.unit = form.unit;
    return { scope, url: `/scope3/${id}`, payload };
  }

  payload.month = Number(form.month);
  if (scope === 2) {
    payload.electricity_kwh = Number(form.amount || form.electricity_kwh);
    payload.grid_region = form.grid_region || undefined;
    payload.market_instrument_type = form.market_instrument_type || undefined;
    if (form.market_emission_factor) payload.market_emission_factor = Number(form.market_emission_factor);
    return { scope, url: `/scope2/${id}`, payload };
  }

  payload.process_type = form.process_type;
  payload.fuel = form.fuel;
  payload.fuel_type = form.fuel;
  payload.amount = Number(form.amount);
  payload.quantity = Number(form.amount);
  payload.unit = form.unit;
  payload.recalculate = true;
  if (form.process_type) {
    payload.calc_inputs = {
      [form.process_type]: { amount: Number(form.amount), unit: form.unit, fuel: form.fuel },
    };
  }
  return { scope, url: `/emissions/${id}`, payload };
}
