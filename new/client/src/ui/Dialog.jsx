import React from "react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Button } from "./Button";
import { cn } from "./cn";

// Legacy dropdown/listbox portals live outside the dialog; clicking them must not count as an outside click.
const isForeignPortal = (target) =>
  target instanceof Element && Boolean(target.closest(".dropdown-portal, [role='listbox']"));

const guardOutside = (e) => {
  if (isForeignPortal(e.target)) e.preventDefault();
};

const overlayClass =
  "fixed inset-0 z-(--z-overlay) bg-ink-900/45 backdrop-blur-[2px] data-[state=open]:animate-[ui-fade-in_var(--duration-base)_ease-out]";

const CloseButton = ({ label = "Close" }) => (
  <RadixDialog.Close
    aria-label={label}
    className="inline-flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-ink-100 hover:text-text"
  >
    <X className="size-4" aria-hidden="true" />
  </RadixDialog.Close>
);

/** Centered modal dialog. Focus is trapped and returned, Escape closes, scroll is locked (Radix). */
export const Dialog = ({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  maxWidth = "32rem",
  className,
  dismissible = true,
}) => (
  <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
    <RadixDialog.Portal>
      <RadixDialog.Overlay className={overlayClass} />
      <RadixDialog.Content
        style={{ maxWidth }} // eslint-disable-line no-restricted-syntax -- dynamic width
        onPointerDownOutside={(e) => (dismissible ? guardOutside(e) : e.preventDefault())}
        onInteractOutside={guardOutside}
        onFocusOutside={guardOutside}
        onEscapeKeyDown={(e) => !dismissible && e.preventDefault()}
        className={cn(
          "fixed left-1/2 top-1/2 z-(--z-modal) flex max-h-[90dvh] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col",
          "rounded-lg border border-border bg-surface shadow-overlay",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <RadixDialog.Title className="text-lg font-semibold text-text">{title}</RadixDialog.Title>
            {description ? (
              <RadixDialog.Description className="mt-0.5 text-sm text-text-secondary">
                {description}
              </RadixDialog.Description>
            ) : (
              <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
            )}
          </div>
          <CloseButton />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">{footer}</div>}
      </RadixDialog.Content>
    </RadixDialog.Portal>
  </RadixDialog.Root>
);

/** Side panel (right). Same behavior as Dialog; use for create/edit forms next to a list. */
export const Sheet = ({ open, onOpenChange, title, description, children, footer, width = "34rem", icon: Icon }) => (
  <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
    <RadixDialog.Portal>
      <RadixDialog.Overlay className={overlayClass} />
      <RadixDialog.Content
        style={{ width }} // eslint-disable-line no-restricted-syntax -- dynamic width
        onPointerDownOutside={guardOutside}
        onInteractOutside={guardOutside}
        onFocusOutside={guardOutside}
        className="fixed inset-y-0 right-0 z-(--z-modal) flex max-w-full flex-col border-l border-border bg-surface shadow-overlay"
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-start gap-3">
            {Icon && (
              <span className="mt-0.5 inline-flex size-9 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-700">
                <Icon className="size-5" aria-hidden="true" />
              </span>
            )}
            <div className="min-w-0">
              <RadixDialog.Title className="text-lg font-semibold text-text">{title}</RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="mt-0.5 text-sm text-text-secondary">
                  {description}
                </RadixDialog.Description>
              ) : (
                <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
              )}
            </div>
          </div>
          <CloseButton label="Close panel" />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">{footer}</div>}
      </RadixDialog.Content>
    </RadixDialog.Portal>
  </RadixDialog.Root>
);

/** Yes/no confirmation. confirmVariant: danger | primary | warning (warning renders as primary). */
export const ConfirmDialog = ({
  open,
  title = "Confirm action",
  message = "Are you sure you want to proceed?",
  confirmLabel = "Confirm",
  confirmVariant = "danger",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  loading = false,
}) => (
  <Dialog
    open={open}
    onOpenChange={(o) => !o && !loading && onCancel?.()}
    title={title}
    maxWidth="28rem"
    footer={
      <>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>
          {cancelLabel}
        </Button>
        <Button variant={confirmVariant === "danger" ? "danger" : "primary"} onClick={onConfirm} loading={loading}>
          {loading ? "Processing..." : confirmLabel}
        </Button>
      </>
    }
  >
    <p className="text-base text-text-secondary">{message}</p>
  </Dialog>
);
