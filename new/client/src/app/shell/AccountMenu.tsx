import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, History, KeyRound, Languages, LogOut, Settings } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import api from "../../api";
import { Menu, MenuContent, MenuItem, MenuLabel, MenuSeparator, MenuTrigger } from "../../ui";
import { ACCESS } from "../access";
import ChangePasswordDialog from "./ChangePasswordDialog";
import { LANGUAGES, currentLanguage, setLanguage, t, type Language } from "../../i18n";

/** Keep the choice on the account too, so it follows the user to another browser. */
async function chooseLanguage(language: Language) {
  if (language === currentLanguage()) return;
  try {
    await api.put("/auth/settings", { language });
  } catch {
    /* the browser still remembers it */
  }
  setLanguage(language);
}

const AccountMenu: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const name = user?.fullName || user?.full_name || user?.email || "User";
  const initial = name.trim()[0]?.toUpperCase() || "U";
  const [passwordOpen, setPasswordOpen] = useState(false);

  return (
    <>
    <Menu>
      <MenuTrigger asChild>
        <button
          type="button"
          aria-label={t("Account menu for {{name}}", { name })}
          className="flex cursor-pointer items-center gap-2 rounded-full border-0 bg-transparent py-1 pl-1 pr-3 transition-colors hover:bg-ink-100"
        >
          <span className="flex size-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-on-primary">
            {initial}
          </span>
          <span className="hidden text-base font-semibold text-text md:inline">{name.split(" ")[0]}</span>
        </button>
      </MenuTrigger>
      <MenuContent className="w-64">
        <div className="px-3 py-2">
          <p className="truncate text-base font-semibold text-text">{name}</p>
          {user?.email && <p className="truncate text-sm text-text-secondary">{user.email}</p>}
          <p className="mt-0.5 truncate text-xs text-text-secondary">{(user as any)?.jobTitle || user?.role}</p>
        </div>
        <MenuSeparator />
        {ACCESS.nonIT(user) && (
          <MenuItem icon={Settings} onSelect={() => navigate("/settings")}>
            {t("Settings & Standards")}
          </MenuItem>
        )}
        {ACCESS.audit(user) && (
          <MenuItem icon={History} onSelect={() => navigate("/audit-trail")}>
            {t("Audit Trail")}
          </MenuItem>
        )}
        <MenuItem icon={KeyRound} onSelect={() => setPasswordOpen(true)}>
          {t("Change password")}
        </MenuItem>
        <MenuSeparator />
        <MenuLabel className="flex items-center gap-1.5">
          <Languages className="size-3.5" aria-hidden="true" /> {t("Language")}
        </MenuLabel>
        {LANGUAGES.map((l) => (
          <MenuItem
            key={l.value}
            lang={l.value}
            onSelect={() => void chooseLanguage(l.value)}
            aria-current={l.value === currentLanguage() ? "true" : undefined}
          >
            <span className="flex w-full items-center justify-between">
              {l.label}
              {l.value === currentLanguage() && <Check className="size-4 text-brand-700" aria-hidden="true" />}
            </span>
          </MenuItem>
        ))}
        <MenuSeparator />
        <MenuItem icon={LogOut} danger onSelect={() => logout()}>
          {t("Sign out")}
        </MenuItem>
      </MenuContent>
    </Menu>
    <ChangePasswordDialog open={passwordOpen} onClose={() => setPasswordOpen(false)} />
    </>
  );
};

export default AccountMenu;
