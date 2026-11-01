with open('new/client/src/pages/audit-trail/AuditTrailChrome.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Update AuditStats to 5 columns with Other / System
old_stats_def = '''export interface AuditStatsProps {
  stats: {
    totalEvents: number;
    totalLogins: number;
    dataMutations: number;
    securityAlerts: number;
  };
}

/** Four headline counters. */
export const AuditStats: React.FC<AuditStatsProps> = ({ stats }) => (
  <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <StatCard icon={Activity} label={t("Total Events Logged")} valueText={stats.totalEvents.toLocaleString()} />
    <StatCard icon={LogIn} label={t("User Logins")} valueText={stats.totalLogins.toLocaleString()} />
    <StatCard icon={Database} label={t("Data Changes")} valueText={stats.dataMutations.toLocaleString()} />
    <StatCard icon={ShieldAlert} label={t("Security & Alerts")} valueText={stats.securityAlerts.toLocaleString()} />
  </div>
);'''

new_stats_def = '''export interface AuditStatsProps {
  stats: {
    totalEvents: number;
    totalLogins: number;
    dataMutations: number;
    securityAlerts: number;
    otherEvents?: number;
  };
}

/** Five headline counters summing to totalEvents. */
export const AuditStats: React.FC<AuditStatsProps> = ({ stats }) => {
  const otherCount = stats.otherEvents ?? Math.max(0, stats.totalEvents - (stats.totalLogins + stats.dataMutations + stats.securityAlerts));
  return (
    <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard icon={Activity} label={t("Total Events Logged")} valueText={stats.totalEvents.toLocaleString()} />
      <StatCard icon={LogIn} label={t("User Logins")} valueText={stats.totalLogins.toLocaleString()} />
      <StatCard icon={Database} label={t("Data Changes")} valueText={stats.dataMutations.toLocaleString()} />
      <StatCard icon={ShieldAlert} label={t("Security & Alerts")} valueText={stats.securityAlerts.toLocaleString()} />
      <StatCard icon={Shield} label={t("Other / System")} valueText={otherCount.toLocaleString()} />
    </div>
  );
};'''

assert old_stats_def in c, "old_stats_def not found"
c = c.replace(old_stats_def, new_stats_def)

# 2. Update AuditIntegrityCheck with Verified / Broken status, last verified timestamp, timeout and error handling
old_integrity = '''/** Runs the hash-chain check of the whole log (GET /audit/verify-chain) and shows the outcome. */
export const AuditIntegrityCheck: React.FC = () => {
  const [result, setResult] = React.useState<ChainResult | null>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const verify = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.get("/audit/verify-chain");
      setResult(res.data);
    } catch (err: any) {
      setResult(null);
      setError(err.response?.data?.error || t("The log could not be verified."));
    } finally {
      setBusy(false);
    }
  };

  React.useEffect(() => {
    verify();
  }, []);

  return (
    <Card className="mb-6 border-l-4 border-l-brand-500 bg-surface/80 p-5 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <Shield className="size-5" aria-hidden="true" />
          </span>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h3 className="m-0 text-base font-bold text-text">{t("Cryptographic Hash Chain Integrity")}</h3>
              {result?.status === "verified" && (
                <Badge tone="success" className="gap-1 px-2 py-0.5 text-xs font-semibold">
                  <CheckCircle2 className="size-3" aria-hidden="true" />
                  {t("Chain Intact")}
                </Badge>
              )}
              {result?.status === "tampered" && (
                <Badge tone="danger" className="gap-1 px-2 py-0.5 text-xs font-semibold">
                  <ShieldAlert className="size-3" aria-hidden="true" />
                  {t("Tampering Detected")}
                </Badge>
              )}
            </div>
            <p className="m-0 text-xs text-text-secondary leading-normal">
              {t("Every audit record is sealed with a SHA-256 hash linked to the previous block, ensuring tamper-evident non-repudiation.")}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {result?.chain_head_hash && (
            <div className="hidden sm:flex items-center gap-1.5 rounded-lg border border-border bg-ink-50 px-2.5 py-1 text-xs">
              <span className="text-text-secondary">{t("Head:")}</span>
              <span className="font-mono font-semibold text-text" title={result.chain_head_hash}>
                {result.chain_head_hash.slice(0, 10)}…{result.chain_head_hash.slice(-6)}
              </span>
            </div>
          )}
          <Button variant="secondary" size="sm" onClick={verify} disabled={busy} className="gap-1.5">
            <RefreshCw className={cn("size-3.5", busy && "animate-spin")} aria-hidden="true" />
            {busy ? t("Verifying...") : t("Verify Chain")}
          </Button>
        </div>
      </div>

      {error && <Banner tone="danger" className="mt-3">{error}</Banner>}

      {result && result.status === "verified" && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs text-text-secondary">
          <span>
            {t("Validated")} <strong className="text-text">{result.total_records.toLocaleString()}</strong> {t("sequential cryptographic blocks.")}
          </span>
          <span className="font-mono text-[11px] text-text-secondary">
            {t("Seal HMAC:")} {result.checkpoint_hmac ? `${result.checkpoint_hmac.slice(0, 12)}…` : "Verified"}
          </span>
        </div>
      )}

      {result && result.status === "tampered" && (
        <div className="mt-3 border-t border-border pt-3">
          <Banner tone="danger" title={t("Tampering Alert: {{count}} issues detected", { count: result.issue_count })}>
            <ul className="m-0 mt-1 list-disc pl-5">
              {result.issues.map((i) => (
                <li key={`${i.id}-${i.problem}`}>
                  {t("Block #")}{i.id}: {i.detail}
                </li>
              ))}
            </ul>
          </Banner>
        </div>
      )}
    </Card>
  );
};'''

new_integrity = '''/** Runs the hash-chain check of the whole log (GET /audit/verify-chain) and shows the outcome. */
export const AuditIntegrityCheck: React.FC = () => {
  const [result, setResult] = React.useState<ChainResult | null>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [lastVerified, setLastVerified] = React.useState<string | null>(null);

  const verify = async () => {
    setBusy(true);
    setError("");
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const res = await api.get("/audit/verify-chain", { signal: controller.signal });
      clearTimeout(timeoutId);
      setResult(res.data);
      setLastVerified(res.data?.verified_at ? new Date(res.data.verified_at).toLocaleTimeString() : new Date().toLocaleTimeString());
    } catch (err: any) {
      clearTimeout(timeoutId);
      setResult(null);
      if (err.name === "CanceledError" || err.name === "AbortError" || controller.signal.aborted) {
        setError(t("Verification request timed out after 10 seconds. Click Verify Chain to retry."));
      } else {
        setError(err.response?.data?.error || t("The audit hash chain could not be verified."));
      }
    } finally {
      setBusy(false);
    }
  };

  React.useEffect(() => {
    verify();
  }, []);

  const firstBroken = result?.issues?.[0];

  return (
    <Card className="mb-6 border-l-4 border-l-brand-500 bg-surface/80 p-5 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <Shield className="size-5" aria-hidden="true" />
          </span>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h3 className="m-0 text-base font-bold text-text">{t("Cryptographic Hash Chain Integrity")}</h3>
              {busy ? (
                <Badge tone="neutral" className="gap-1 px-2 py-0.5 text-xs font-semibold">
                  <RefreshCw className="size-3 animate-spin" aria-hidden="true" />
                  {t("Verifying...")}
                </Badge>
              ) : result?.status === "verified" ? (
                <Badge tone="success" className="gap-1 px-2 py-0.5 text-xs font-semibold">
                  <CheckCircle2 className="size-3" aria-hidden="true" />
                  {t("Verified (Chain Intact)")}
                </Badge>
              ) : result?.status === "tampered" ? (
                <Badge tone="danger" className="gap-1 px-2 py-0.5 text-xs font-semibold">
                  <ShieldAlert className="size-3" aria-hidden="true" />
                  {t("Broken (Tampering Detected)")}
                </Badge>
              ) : error ? (
                <Badge tone="danger" className="gap-1 px-2 py-0.5 text-xs font-semibold">
                  <XCircle className="size-3" aria-hidden="true" />
                  {t("Verification Error")}
                </Badge>
              ) : null}
            </div>
            <p className="m-0 text-xs text-text-secondary leading-normal">
              {t("Every audit record is sealed with a SHA-256 hash linked to the previous block, ensuring tamper-evident non-repudiation.")}
              {lastVerified && ` • ${t("Last verified at")} ${lastVerified}`}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {result?.chain_head_hash && (
            <div className="hidden sm:flex items-center gap-1.5 rounded-lg border border-border bg-ink-50 px-2.5 py-1 text-xs">
              <span className="text-text-secondary">{t("Head:")}</span>
              <span className="font-mono font-semibold text-text" title={result.chain_head_hash}>
                {result.chain_head_hash.slice(0, 10)}…{result.chain_head_hash.slice(-6)}
              </span>
            </div>
          )}
          <Button variant="secondary" size="sm" onClick={verify} disabled={busy} className="gap-1.5">
            <RefreshCw className={cn("size-3.5", busy && "animate-spin")} aria-hidden="true" />
            {busy ? t("Verifying...") : t("Verify Chain")}
          </Button>
        </div>
      </div>

      {error && <Banner tone="danger" className="mt-3">{error}</Banner>}

      {result && result.status === "verified" && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs text-text-secondary">
          <span>
            {t("Validated")} <strong className="text-text">{result.total_records.toLocaleString()}</strong> {t("sequential cryptographic blocks.")}
          </span>
          <span className="font-mono text-[11px] text-text-secondary">
            {t("Seal HMAC:")} {result.checkpoint_hmac ? `${result.checkpoint_hmac.slice(0, 12)}…` : "Verified"}
          </span>
        </div>
      )}

      {result && result.status === "tampered" && (
        <div className="mt-3 border-t border-border pt-3">
          <Banner tone="danger" title={t("Tampering Alert: Broken at Block #{{id}} ({{count}} total issues)", { id: firstBroken?.id ?? "unknown", count: result.issue_count })}>
            <ul className="m-0 mt-1 list-disc pl-5">
              {result.issues.map((i) => (
                <li key={`${i.id}-${i.problem}`}>
                  {t("Block #")}{i.id}: {i.detail}
                </li>
              ))}
            </ul>
          </Banner>
        </div>
      )}
    </Card>
  );
};'''

assert old_integrity in c, "old_integrity not found"
c = c.replace(old_integrity, new_integrity)

with open('new/client/src/pages/audit-trail/AuditTrailChrome.tsx', 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)
print("Updated AuditTrailChrome.tsx")
