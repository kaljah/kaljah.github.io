import React from "react";
import { Card } from "../../ui";
import { cn } from "../../ui/cn";

/** Panel for one Manage Data tab: heading, one-line description and content. */
export const TabCard = ({ title, description, actions, className, children }) => (
  <Card className={cn("manage-card p-6 md:p-8", className)}>
    {(title || actions) && (
      <div className="mb-8 flex flex-wrap items-start justify-between gap-3">
        <div>
          {title && <h2 className="m-0 mb-2 text-xl font-bold text-text">{title}</h2>}
          {description && <p className="m-0 text-base text-text-secondary">{description}</p>}
        </div>
        {actions}
      </div>
    )}
    {children}
  </Card>
);

/** Responsive grid for the add-record form fields. */
export const FormGrid = ({ cols = "md:grid-cols-3", className, children }) => (
  <div className={cn("grid-forms mb-6 grid gap-5 sm:grid-cols-2", cols, className)}>{children}</div>
);

/** Row of form buttons under a FormGrid. */
export const FormActions = ({ className, children }) => <div className={cn("mt-5 flex flex-wrap items-center gap-3", className)}>{children}</div>;

/** Titled, horizontally scrollable table block. Pass the header labels and the body rows. */
export const RecordTable = ({ title, head, children, empty, colSpan, footer, className }) => (
  <div className={cn("table-container mt-10", className)}>
    {title && <h3 className="m-0 mb-3 text-lg font-semibold text-text">{title}</h3>}
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="data-table w-full border-collapse text-base">
        <thead>
          <tr>
            {head.map((h, i) => (
              <th key={i} scope="col" className="whitespace-nowrap border-b border-border bg-ink-50 px-4 py-3 text-left text-sm font-semibold text-text-secondary">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {children}
          {empty && (
            <tr>
              <td colSpan={colSpan || head.length} className="p-10 text-center text-text-secondary">
                {empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
    {footer}
  </div>
);

/** Table body row and cell with the shared spacing. */
export const Tr = ({ className, ...props }) => <tr className={cn("hover:bg-ink-50", className)} {...props} />;
export const Td = ({ className, ...props }) => <td className={cn("border-b border-ink-100 px-4 py-3 align-middle text-text", className)} {...props} />;

const Auto = () => <Badge tone="info" className="px-1.5 py-0 text-[0.65rem]">Auto</Badge>;
const labelWithAuto = (text, auto) => (
  <span className="inline-flex items-center gap-1.5">
    {text}
    {auto && <Auto />}
  </span>
);

/**
 * Activity, Division and Region selectors shared by the production, source and mitigation forms.
 * Non-privileged users with a single option get it pre-selected, so the field is locked and tagged "Auto".
 */
export const ScopeFields = ({ form, setForm, isPrivileged, facilities, ACTIVITY_LABELS, getAvailableActivities, getAvailableDivisions }) => {
  const activities = getAvailableActivities();
  const divisions = getAvailableDivisions(form.activity);
  const regions = facilities.filter((f) => f.activity === form.activity && f.division === form.division);
  const lockActivity = !isPrivileged && activities.length === 1;
  const lockDivision = !isPrivileged && divisions.length === 1;
  const lockRegion = !isPrivileged && regions.length === 1;
  return (
    <>
      <Field label={labelWithAuto("Activity", lockActivity)}>
        <NativeSelect className={controlClass} value={form.activity} onChange={(e) => setForm({ ...form, activity: e.target.value, division: "", facility_id: "" })} disabled={lockActivity}>
          <option value="">Select Activity</option>
          {activities.map((a) => (
            <option key={a} value={a}>
              {ACTIVITY_LABELS[a] || a}
            </option>
          ))}
        </NativeSelect>
      </Field>
      <Field label={labelWithAuto("Division", lockDivision)}>
        <NativeSelect className={controlClass} value={form.division} onChange={(e) => setForm({ ...form, division: e.target.value, facility_id: "" })} disabled={!form.activity || lockDivision}>
          <option value="">Select Division</option>
          {divisions.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </NativeSelect>
      </Field>
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-text">{labelWithAuto("Region", lockRegion)}</span>
        <CustomDropdown
          options={[{ value: "", label: "Select Region" }, ...regions.map((f) => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))]}
          value={form.facility_id}
          onChange={(val) => setForm({ ...form, facility_id: val })}
          placeholder="Select Region"
          disabled={!form.division || lockRegion}
        />
      </div>
    </>
  );
};

/** Region name with its field, resolved from the facilities list. */
export const RegionName = ({ facility, fallback }) =>
  facility ? (
    <>
      {facility.name}
      {facility.field && <span className="ml-1 text-[0.85em] font-normal text-ink-400">-{facility.field}</span>}
    </>
  ) : (
    fallback
  );
