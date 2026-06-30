const S = { c: "#faf9f5", h: "#e6dfd8", i: "#141413", m: "#6c6a64", ms: "#8e8b82", r: "#cc785c", w: "#fff" };
import { useTranslation } from "react-i18next";
const CORAL = "#cc785c";
const ERROR = "#c64545";
const DISABLED = "#e6dfd8";

interface Props {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  confirmColor?: "coral" | "error";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  title,
  message,
  confirmText = "",
  cancelText = "",
  confirmColor = "coral",
  loading = false,
  onConfirm,
  onCancel,
}: Props) {
  const { t } = useTranslation();
  const color = confirmColor === "error" ? ERROR : CORAL;

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onCancel} />
      <div
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ backgroundColor: "rgba(0,0,0,0.15)" }}
      >
        <div
          className="rounded-xl p-5 w-80 shadow-lg border"
          style={{ backgroundColor: S.c, borderColor: S.h }}
        >
          <h3 className="text-sm font-medium mb-2" style={{ color: S.i, fontFamily: "'Inter', sans-serif" }}>
            {title}
          </h3>
          <p className="text-xs mb-4" style={{ color: S.m, fontFamily: "'Inter', sans-serif" }}>
            {message}
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={onCancel}
              disabled={loading}
              className="text-xs px-4 py-1.5 rounded-md border"
              style={{
                fontFamily: "'Inter', sans-serif",
                color: S.m,
                borderColor: S.h,
                backgroundColor: S.c,
              }}
            >
              {(cancelText || t("common.cancel"))}
            </button>
            <button
              onClick={onConfirm}
              disabled={loading}
              data-color={confirmColor}
              className="text-xs px-4 py-1.5 rounded-md font-medium"
              style={{
                fontFamily: "'Inter', sans-serif",
                backgroundColor: loading ? DISABLED : color,
                color: S.w,
              }}
            >
              {loading ? t("common.processing") : confirmText}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
