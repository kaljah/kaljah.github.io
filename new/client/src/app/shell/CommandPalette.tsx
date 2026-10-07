import React, { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Command } from "cmdk";
import * as RadixDialog from "@radix-ui/react-dialog";
import { Calculator, CornerDownLeft, Search } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { ACCESS } from "../access";
import { readRecent } from "../recentPages";
import { ROUTES, type AppRoute } from "../routes.config";

const itemClass =
  "flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-base text-text data-[selected=true]:bg-ink-100";
const headingClass =
  "[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wide [&_[cmdk-group-heading]]:text-text-secondary";

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CommandPalette: React.FC<CommandPaletteProps> = ({ open, onOpenChange }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  // Re-read the recents each time the palette opens
  const recent = useMemo(() => (open ? readRecent() : []), [open]);

  const pages = ROUTES.filter((r) => ACCESS[r.access](user));
  const go = (to: string) => {
    onOpenChange(false);
    navigate(to);
  };

  const actions = ACCESS.nonIT(user)
    ? [
        { label: "New Scope 1 entry", to: "/emissions?scope=scope1" },
        { label: "New Scope 2 entry", to: "/emissions?scope=scope2" },
        { label: "New Scope 3 entry", to: "/emissions?scope=scope3" },
        { label: "Manage custom emission factors", to: "/manage-data" },
      ]
    : [];

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-(--z-overlay) bg-ink-900/45" />
        <RadixDialog.Content
          aria-describedby={undefined}
          className="fixed left-1/2 top-[15vh] z-(--z-modal) w-[calc(100vw-2rem)] max-w-xl -translate-x-1/2 overflow-hidden rounded-lg border border-border bg-surface shadow-overlay"
        >
          <RadixDialog.Title className="sr-only">Search pages and actions</RadixDialog.Title>
          <Command label="Search pages and actions">
            <div className="flex items-center gap-2 border-b border-border px-4">
              <Search className="size-4 shrink-0 text-text-secondary" aria-hidden="true" />
              <Command.Input
                autoFocus
                placeholder="Search pages and actions"
                className="h-12 w-full bg-transparent text-md text-text outline-none placeholder:text-text-disabled"
              />
            </div>
            <Command.List className="max-h-80 overflow-y-auto p-2">
              <Command.Empty className="px-3 py-6 text-center text-base text-text-secondary">No results</Command.Empty>
              {recent.length > 0 && (
                <Command.Group heading="Recent" className={headingClass}>
                  {recent
                    .map((p) => pages.find((r) => r.path === p))
                    .filter((r): r is AppRoute => Boolean(r))
                    .map((r) => (
                      <Command.Item key={`recent-${r.path}`} value={`recent ${r.title}`} onSelect={() => go(r.path)} className={itemClass}>
                        <r.icon className="size-4 text-text-secondary" aria-hidden="true" />
                        {r.title}
                      </Command.Item>
                    ))}
                </Command.Group>
              )}
              <Command.Group heading="Pages" className={headingClass}>
                {pages.map((r) => (
                  <Command.Item key={r.path} value={`${r.title} ${r.group ?? ""}`} onSelect={() => go(r.path)} className={itemClass}>
                    <r.icon className="size-4 text-text-secondary" aria-hidden="true" />
                    {r.title}
                    {r.group && <span className="ml-auto text-sm text-text-secondary">{r.group}</span>}
                  </Command.Item>
                ))}
              </Command.Group>
              {actions.length > 0 && (
                <Command.Group heading="Actions" className={headingClass}>
                  {actions.map((a) => (
                    <Command.Item key={a.label} value={a.label} onSelect={() => go(a.to)} className={itemClass}>
                      <Calculator className="size-4 text-text-secondary" aria-hidden="true" />
                      {a.label}
                      <CornerDownLeft className="ml-auto size-3.5 text-ink-400" aria-hidden="true" />
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
          </Command>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
};

export default CommandPalette;
