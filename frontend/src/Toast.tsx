import { useEffect } from "react";

const COLORS: Record<string, string> = {
  info: "#cc785c",
  error: "#c64545",
  success: "#5db872",
};

interface Props {
  message: string;
  type?: "info" | "error" | "success";
  onClose: () => void;
}

export default function Toast({ message, type = "info", onClose }: Props) {
  useEffect(() => {
    const timer = setTimeout(onClose, 2500);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bg = COLORS[type] || COLORS.info;

  return (
    <div
      data-type={type}
      role="status"
      style={{
        position: "fixed",
        top: "16px",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9999,
        backgroundColor: bg,
        color: "#ffffff",
        padding: "8px 20px",
        borderRadius: "8px",
        fontSize: "14px",
        fontFamily: "'Inter', sans-serif",
        fontWeight: 500,
        boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
        maxWidth: "90vw",
      }}
    >
      {message}
    </div>
  );
}
