import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Banner } from "../../ui";
import { t } from "../../i18n";

/** Offline and session-timeout notices, stacked instead of drawn on top of each other. */
const BannerStack: React.FC = () => {
  const { sessionWarning } = useAuth() || {};
  const [online, setOnline] = useState<boolean>(typeof navigator !== "undefined" ? navigator.onLine : true);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  if (online && !sessionWarning) return null;
  return (
    <div className="fixed left-1/2 top-4 z-(--z-banner) flex w-[calc(100vw-2rem)] max-w-xl -translate-x-1/2 flex-col gap-2">
      {!online && (
        <Banner id="offline-banner" tone="danger" title={t("Network connection lost")} className="shadow-overlay">
          {t("You are working offline. Changes will not sync until the connection is restored.")}
        </Banner>
      )}
      {sessionWarning && (
        <Banner tone="warning" title={t("Session timeout imminent")} className="shadow-overlay">
          {t("Your session will expire in 60 seconds due to inactivity. Move your mouse or click to stay signed in.")}
        </Banner>
      )}
    </div>
  );
};

export default BannerStack;
