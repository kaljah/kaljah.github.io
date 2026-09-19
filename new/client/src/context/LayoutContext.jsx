import React, { createContext, useContext, useState, useCallback } from "react";

const LayoutContext = createContext();

export const LayoutProvider = ({ children }) => {
  const [topBarLeft, setTopBarLeft] = useState(null);
  const [topBarRight, setTopBarRight] = useState(null);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

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

export const useLayout = () => {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error("useLayout must be used within a LayoutProvider");
  }
  return context;
};

