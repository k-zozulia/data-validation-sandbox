import clsx from "clsx";
import { CheckCircle2, CircleAlert, X } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Toast = { id: number; tone: "success" | "error"; title: string; body?: string };
type Push = (t: Omit<Toast, "id">) => void;

const ToastContext = createContext<Push>(() => {});

// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => useContext(ToastContext);

export function Toaster({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = (id: number) => setToasts((ts) => ts.filter((t) => t.id !== id));
  const push = useCallback<Push>((t) => {
    const id = Date.now() + Math.random();
    setToasts((ts) => [...ts.slice(-3), { ...t, id }]);
    setTimeout(() => dismiss(id), t.tone === "error" ? 7000 : 3500);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:items-end">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-zinc-200 bg-white p-3 shadow-lg dark:border-zinc-800 dark:bg-zinc-900"
          >
            {t.tone === "success" ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" />
            ) : (
              <CircleAlert className="mt-0.5 size-4 shrink-0 text-rose-500" />
            )}
            <div className="min-w-0 flex-1 text-sm">
              <div className="font-medium">{t.title}</div>
              {t.body && (
                <div className={clsx("mt-0.5 break-words text-zinc-500 dark:text-zinc-400")}>
                  {t.body}
                </div>
              )}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
              aria-label="Dismiss"
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
