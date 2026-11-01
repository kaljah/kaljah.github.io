# Patch AuditTrail.tsx
at_path = 'new/client/src/pages/AuditTrail.tsx'
with open(at_path, 'r', encoding='utf-8') as f:
    at_content = f.read()

old_cols = '''  const tableColumns: ColumnDef<AuditLog, any>[] = [
    {
      id: "time",
      header: t("Time"),
      accessorFn: (l: AuditLog) => l.timestamp,
      cell: (c) => (
        <span title={formatFullDateTime(c.getValue())} className="text-text-secondary">
          {formatTimestamp(c.getValue())}
        </span>
      ),
    },
    { id: "user", header: t("User"), accessorFn: (l: AuditLog) => l.user || t("System") },
    {
      id: "action",
      header: t("Action"),
      accessorFn: (l: AuditLog) => l.action,
      cell: (c) => <Badge tone={actionTone(c.getValue())}>{c.getValue()}</Badge>,
    },
    { id: "entity", header: t("Entity"), accessorFn: (l: AuditLog) => l.entity || "-" },
    {
      id: "description",
      header: t("Description"),
      accessorFn: (l: AuditLog) => formatAuditDescription(l.description || l.details) || t("No details recorded"),
      cell: (c) => <span className="block max-w-[32rem] truncate" title={c.getValue()}>{c.getValue()}</span>,
    },
    { id: "ref", header: t("Ref"), accessorFn: (l: AuditLog) => l.entityId || l.recordId || "-" },
    { id: "ip", header: t("IP"), accessorFn: (l: AuditLog) => l.ipAddress || t("Local / System") },'''

new_cols = '''  const tableColumns: ColumnDef<AuditLog, any>[] = [
    {
      id: "eventId",
      header: t("Event #"),
      accessorFn: (l: AuditLog) => `#${l.id}`,
      cell: (c) => <span className="font-mono text-xs font-semibold text-text">{c.getValue()}</span>,
    },
    {
      id: "time",
      header: t("Time"),
      accessorFn: (l: AuditLog) => l.timestamp,
      cell: (c) => (
        <span title={formatFullDateTime(c.getValue())} className="text-text-secondary">
          {formatTimestamp(c.getValue())}
        </span>
      ),
    },
    { id: "user", header: t("User"), accessorFn: (l: AuditLog) => l.user || t("System") },
    {
      id: "action",
      header: t("Action"),
      accessorFn: (l: AuditLog) => l.action,
      cell: (c) => <Badge tone={actionTone(c.getValue())}>{c.getValue()}</Badge>,
    },
    { id: "entity", header: t("Entity"), accessorFn: (l: AuditLog) => l.entity || "-" },
    {
      id: "description",
      header: t("Description"),
      accessorFn: (l: AuditLog) => formatAuditDescription(l.description || l.details) || t("No details recorded"),
      cell: (c) => <span className="block max-w-[28rem] truncate" title={c.getValue()}>{c.getValue()}</span>,
    },
    {
      id: "ref",
      header: t("Target ID"),
      accessorFn: (l: AuditLog) => l.entityId || l.recordId || "-",
      cell: (c) => (
        <span
          title={t("Target Entity Record ID: ID of the modified {{entity}}", { entity: c.row.original.entity || "record" })}
          className="font-mono text-xs text-text-secondary"
        >
          {c.row.original.entity ? `${c.row.original.entity} #${c.getValue()}` : `#${c.getValue()}`}
        </span>
      ),
    },
    { id: "ip", header: t("IP"), accessorFn: (l: AuditLog) => l.ipAddress || t("Local / System") },'''

assert old_cols in at_content, "old_cols not found in AuditTrail.tsx"
at_content = at_content.replace(old_cols, new_cols)

with open(at_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(at_content)
print("Updated AuditTrail.tsx columns")


# Patch AuditTrailAuditTimeline.tsx
att_path = 'new/client/src/pages/audit-trail/AuditTrailAuditTimeline.tsx'
with open(att_path, 'r', encoding='utf-8') as f:
    att_content = f.read()

old_att_header = '''              <div className="flex flex-wrap items-center gap-2.5">
                <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-ink-50 px-2 py-0.5 text-base font-bold text-ink-800">
                  <UserIcon className="size-3 text-ink-500" aria-hidden="true" /> {log.user}
                </span>'''

new_att_header = '''              <div className="flex flex-wrap items-center gap-2.5">
                <span className="font-mono text-xs font-bold text-text-secondary">
                  #{log.id}
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-ink-50 px-2 py-0.5 text-base font-bold text-ink-800">
                  <UserIcon className="size-3 text-ink-500" aria-hidden="true" /> {log.user}
                </span>'''

assert old_att_header in att_content, "old_att_header not found in AuditTrailAuditTimeline.tsx"
att_content = att_content.replace(old_att_header, new_att_header)

old_att_ref = '<Meta icon={Database}>{t("Ref: #")}{log.entityId || log.recordId || "N/A"}</Meta>'
new_att_ref = '<Meta icon={Database} title={t("Target Entity Record ID")}>{t("Target:")} {log.entity ? `${log.entity} #${log.entityId || log.recordId}` : `#${log.entityId || log.recordId || "N/A"}`}</Meta>'

assert old_att_ref in att_content, "old_att_ref not found in AuditTrailAuditTimeline.tsx"
att_content = att_content.replace(old_att_ref, new_att_ref)

with open(att_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(att_content)
print("Updated AuditTrailAuditTimeline.tsx")
