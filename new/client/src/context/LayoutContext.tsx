import React, { createContext, useContext, useState, useCallback } from "react";

export interface LayoutContextType {
  topBarLeft: React.ReactNode;
  setTopBarLeft: React.Dispatch<React.SetStateAction<React.ReactNode>>;
  topBarRight: React.ReactNode;
  setTopBarRight: React.Dispatch<React.SetStateAction<React.ReactNode>>;
  breadcrumbExtra: React.ReactNode;
  setBreadcrumbExtra: React.Dispatch<React.SetStateAction<React.ReactNode>>;
  isMobileNavOpen: boolean;
  setIsMobileNavOpen: React.Dispatch<React.SetStateAction<boolean>>;
  toggleMobileNav: () => void;
  closeMobileNav: () => void;
  openMobileNav: () => void;
}

const LayoutContext = createContext<LayoutContextType | null>(null);

export interface LayoutProviderProps {
  children: React.ReactNode;
}

export const LayoutProvider: React.FC<LayoutProviderProps> = ({ children }) => {
  const [topBarLeft, setTopBarLeft] = useState<React.ReactNode>(null);
  const [topBarRight, setTopBarRight] = useState<React.ReactNode>(null);
  const [breadcrumbExtra, setBreadcrumbExtra] = useState<React.ReactNode>(null);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

  const toggleMobileNav = useCallback(() => setIsMobileNavOpen((prev) => !prev), []);
  const closeMobileNav = useCallback(() => setIsMobileNavOpen(false), []);
  const openMobileNav = useCallback(() => setIsMobileNavOpen(true), []);

  return (
    <LayoutContext.Provider
      value={{
        topBarLeft,
        setTopBarLeft,
        topBarRight,
        setTopBarRight,
        breadcrumbExtra,
        setBreadcrumbExtra,
        isMobileNavOpen,
        setIsMobileNavOpen,
        toggleMobileNav,
        closeMobileNav,
        openMobileNav,
      }}
    >
      {children}
    </LayoutContext.Provider>
  );
};

export const useLayout = (): LayoutContextType => {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error("useLayout must be used within a LayoutProvider");
  }
  return context;
};
