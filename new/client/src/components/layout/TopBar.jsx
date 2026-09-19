import React, { useState, useRef, useEffect } from "react";
import { User, Building } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useLayout } from "../../context/LayoutContext";
import NotificationCenter from "../NotificationCenter";
import "./TopBar.css";

const TopBar = () => {
  const { user, logout } = useAuth();
  const { topBarLeft, topBarRight } = useLayout();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setIsProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="top-bar">
      <div className="top-bar-left-section">
        <div className="breadcrumbs">
          <Building size={16} style={{ color: "var(--accent-color, #ff6600)" }} />
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Corporate ESG</span>
        </div>

        {topBarLeft && (
          <div className="top-bar-injected-left">{topBarLeft}</div>
        )}
      </div>

      <div className="top-actions">
        {topBarRight}

        <NotificationCenter />

        <div style={{ position: "relative" }} ref={profileRef}>
          <button
            className="icon-button"
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            title="User Profile"
          >
            <User size={18} />
          </button>
          {isProfileOpen && (
            <div className="top-profile-dropdown">
              <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-color)" }}>
                <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "var(--text-primary)" }}>
                  {user?.fullName || user?.email}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", textTransform: "uppercase", marginTop: "2px" }}>
                  Role: {user?.role}
                </div>
              </div>
              <button className="top-drop-item logout-btn-top" onClick={logout} style={{ width: "100%", textAlign: "left", padding: "10px 14px" }}>
                Sign Out
              </button>
            </div>
          )}
        </div>
        <span className="user-name-top">
          {user?.fullName?.split(" ")[0] || "User"}
        </span>
      </div>
    </header>
  );
};

export default TopBar;



