import React, { useState, useRef, useEffect } from "react";
import { User, Building, Menu } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useLayout } from "../../context/LayoutContext";
import NotificationCenter from "../NotificationCenter";
import "./TopBar.css";

const TopBar = () => {
  const { user, logout } = useAuth();
  const { topBarLeft, topBarRight, toggleMobileNav } = useLayout();
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
        <button
          className="mobile-hamburger-btn"
          onClick={(e) => {
            e.stopPropagation();
            toggleMobileNav();
          }}
          aria-label="Open navigation menu"
          type="button"
        >
          <Menu size={22} />
        </button>

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

        <div style={{ position: "relative" }} ref={profileRef} className="user-profile-tab-wrapper">
          <button
            className="icon-button user-profile-tab-btn"
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            title="User Profile"
            aria-label="User Profile"
          >
            <User size={18} />
          </button>
          {isProfileOpen && (
            <div className="top-profile-dropdown">
              <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-color)" }}>
                <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "var(--text-primary)" }}>
                  {user?.fullName || user?.email}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {user?.jobTitle || user?.role || ""}
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



