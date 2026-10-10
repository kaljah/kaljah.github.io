import React, { useState } from "react";
import { Dialog, Button, Field, Input } from "../../ui";
import api from "../../api";
import { useToast } from "../../components/Toast";
import { apiError } from "../../utils/apiError";
import { t } from "../../i18n";

interface ChangePasswordDialogProps {
  open: boolean;
  onClose: () => void;
}

// Every role changes its own password here (POST /api/auth/change-password). The server applies the
// password policy; other sessions of the account end, this one stays signed in.
const ChangePasswordDialog: React.FC<ChangePasswordDialogProps> = ({ open, onClose }) => {
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const close = () => {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError("");
    onClose();
  };

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!current || !next) return setError(t("Enter your current and new password."));
    if (next !== confirm) return setError(t("The new passwords do not match."));
    setSaving(true);
    setError("");
    try {
      await api.post("/auth/change-password", { currentPassword: current, newPassword: next });
      toast.success(t("Password changed. Your other sessions have been signed out."));
      close();
    } catch (err) {
      setError(apiError(err, t("The password could not be changed.")));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => !o && close()}
      title={t("Change password")}
      description={t("At least 10 characters, with upper- and lower-case letters, a digit and a special character.")}
      maxWidth="28rem"
      footer={
        <>
          <Button variant="secondary" onClick={close} disabled={saving}>
            {t("Cancel")}
          </Button>
          <Button onClick={() => submit()} loading={saving} disabled={saving}>
            {t("Change password")}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={t("Current password")}>
          <Input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </Field>
        <Field label={t("New password")}>
          <Input type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        </Field>
        <Field label={t("Confirm new password")}>
          <Input type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
        {error && (
          <p role="alert" className="text-sm text-danger-fg">
            {error}
          </p>
        )}
        <button type="submit" hidden />
      </form>
    </Dialog>
  );
};

export default ChangePasswordDialog;
