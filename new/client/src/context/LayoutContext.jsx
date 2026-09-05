import React, { createContext, useContext, useState } from "react";

const LayoutContext = createContext();

export const LayoutProvider = ({ children }) => {
  const [topBarLeft, setTopBarLeft] = useState(null);
  const [topBarRight, setTopBarRight] = useState(null);

  return (
    <LayoutContext.Provider
      value={{
        topBarLeft,
        setTopBarLeft,
        topBarRight,
        setTopBarRight,
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

