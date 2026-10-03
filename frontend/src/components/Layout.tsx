import clsx from "clsx";
import { Database, History, ListChecks, Moon, ShieldCheck, Sun } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useHealth } from "../api/hooks";
import { useTheme } from "../utils/theme";

const nav = [
  { to: "/datasets", label: "Datasets", icon: Database },
  { to: "/jobs", label: "Validation runs", icon: History },
  { to: "/rule-sets", label: "Rule sets", icon: ListChecks },
];

function HealthDot() {
  const { data, isError } = useHealth();
  const ok = data?.status === "ok";
  const label = isError
    ? "API unreachable"
    : !data
      ? "Checking API…"
      : ok
        ? data.inline_jobs
          ? "API ok · inline jobs"
          : "API, DB, worker queue ok"
        : `Degraded: db ${data.database}, redis ${data.redis}, storage ${data.storage}`;
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400" title={label}>
      <span
        className={clsx(
          "size-2 rounded-full",
          isError ? "bg-rose-500" : !data ? "bg-zinc-400" : ok ? "bg-emerald-500" : "bg-amber-500",
        )}
      />
      <span className="truncate">{label}</span>
    </div>
  );
}

function ThemeToggle() {
  const [theme, toggle] = useTheme();
  return (
    <button
      onClick={toggle}
      className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
      aria-label="Toggle dark mode"
      title="Toggle dark mode"
    >
      {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300"
      : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/70 dark:hover:text-zinc-100",
  );

export default function Layout() {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 hidden h-screen flex-col border-r border-zinc-200 bg-white px-3 py-4 lg:flex dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mb-6 flex items-center gap-2 px-2">
          <ShieldCheck className="size-6 text-indigo-600 dark:text-indigo-400" />
          <div className="leading-tight">
            <div className="text-sm font-semibold">Data Validation</div>
            <div className="text-xs text-zinc-500">Sandbox · v2</div>
          </div>
        </div>
        <nav className="flex flex-col gap-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={linkClass}>
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex items-center justify-between gap-2 border-t border-zinc-200 px-2 pt-3 dark:border-zinc-800">
          <HealthDot />
          <ThemeToggle />
        </div>
      </aside>

      {/* Top bar (mobile) */}
      <header className="sticky top-0 z-20 flex items-center gap-1 overflow-x-auto border-b border-zinc-200 bg-white/90 px-3 py-2 backdrop-blur lg:hidden dark:border-zinc-800 dark:bg-zinc-900/90">
        <ShieldCheck className="mr-1 size-5 shrink-0 text-indigo-600 dark:text-indigo-400" />
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={linkClass}>
            <Icon className="size-4" />
            <span className="hidden sm:inline">{label}</span>
          </NavLink>
        ))}
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </header>

      <main className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
