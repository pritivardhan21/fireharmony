import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState<boolean>(() => {
    try {
      return localStorage.getItem("fh-theme") === "dark";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("fh-theme", dark ? "dark" : "light");
    } catch {
      /* storage may be unavailable */
    }
  }, [dark]);

  return (
    <div className="mb-3 flex items-center justify-end gap-2 text-xs text-slate-200 sm:absolute sm:right-4 sm:top-4 sm:mb-0">
      <span aria-hidden="true">Light</span>
      <button
        type="button"
        role="switch"
        aria-checked={dark}
        aria-label="Dark theme"
        onClick={() => setDark((d) => !d)}
        className={`relative h-6 w-11 rounded-full border transition-colors ${
          dark ? "border-blue-400 bg-blue-600" : "border-slate-400 bg-slate-600"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full shadow transition-all ${dark ? "left-5" : "left-0.5"}`}
          style={{ backgroundColor: "#ffffff" }}
        />
      </button>
      <span aria-hidden="true">Dark</span>
    </div>
  );
}
