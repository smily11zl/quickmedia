import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import zh from "./locales/zh";
import en from "./locales/en";

const detectLanguage = (): string => {
  try {
    const saved = localStorage.getItem("language");
    if (saved === "zh" || saved === "en") return saved;
    const nav: any = navigator;
    const navLang = (nav.language || nav.userLanguage || "").toLowerCase();
    if (navLang.startsWith("zh")) return "zh";
  } catch {}
  return "en";
};

i18n.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    en: { translation: en },
  },
  lng: detectLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
