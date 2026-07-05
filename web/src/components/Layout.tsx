import { clsx } from "clsx";
import { BarChart3, ListChecks, Moon, Sun } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { ApiKeyMenu } from "./ApiKeyMenu";
import { useTheme } from "@/hooks/useTheme";

const navItems = [
  { to: "/", label: "Jobs", icon: ListChecks, end: true },
  { to: "/analytics", label: "Analytics", icon: BarChart3, end: false },
];

export function Layout({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
              <img src="/spider.svg" alt="" className="size-5" />
              Scrapyard
            </div>
            <nav className="flex items-center gap-1">
              {navItems.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                        : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
                    )
                  }
                >
                  <Icon className="size-4" />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-1">
            <ApiKeyMenu />
            <button
              onClick={toggle}
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              title="Toggle theme"
            >
              {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
