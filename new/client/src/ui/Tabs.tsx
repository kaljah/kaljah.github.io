import React from "react";
import * as RadixTabs from "@radix-ui/react-tabs";
import { useSearchParams } from "react-router-dom";
import { cn } from "./cn";

export interface TabsProps extends React.ComponentPropsWithoutRef<typeof RadixTabs.Root> {}

export const Tabs: React.FC<TabsProps> = ({ className, ...props }) => (
  <RadixTabs.Root className={cn("flex flex-col", className)} {...props} />
);

export interface TabsListProps extends React.ComponentPropsWithoutRef<typeof RadixTabs.List> {}

export const TabsList: React.FC<TabsListProps> = ({ className, ...props }) => (
  <RadixTabs.List
    className={cn("flex gap-1 overflow-x-auto border-b border-border", className)}
    {...props}
  />
);

export interface TabsTriggerProps extends React.ComponentPropsWithoutRef<typeof RadixTabs.Trigger> {
  badge?: React.ReactNode;
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({ className, badge, children, ...props }) => (
  <RadixTabs.Trigger
    className={cn(
      "-mb-px inline-flex shrink-0 cursor-pointer items-center gap-2 border-0 border-b-2 border-transparent bg-transparent px-4 py-2.5 text-base font-semibold",
      "text-text-secondary transition-colors hover:text-text",
      "data-[state=active]:border-primary data-[state=active]:text-selected-fg",
      className,
    )}
    {...props}
  >
    {children}
    {badge != null && badge !== 0 && (
      <span className="rounded-full bg-brand-50 px-1.5 text-xs font-bold text-brand-700">{badge}</span>
    )}
  </RadixTabs.Trigger>
);

export interface TabsContentProps extends React.ComponentPropsWithoutRef<typeof RadixTabs.Content> {}

export const TabsContent: React.FC<TabsContentProps> = ({ className, ...props }) => (
  <RadixTabs.Content className={cn("pt-4", className)} {...props} />
);

/** Keeps the selected tab in the URL (?tab=...), so links are shareable and Back works. */
export const useTabParam = <T extends string>(
  values: readonly T[] | T[],
  fallback: T = values[0],
  key: string = "tab",
): [T, (next: T) => void] => {
  const [params, setParams] = useSearchParams();
  const raw = params.get(key);
  const value = (values as readonly string[]).includes(raw || "") ? (raw as T) : fallback;
  const setValue = (next: T) =>
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        p.set(key, next);
        return p;
      },
      { replace: true },
    );
  return [value, setValue];
};
