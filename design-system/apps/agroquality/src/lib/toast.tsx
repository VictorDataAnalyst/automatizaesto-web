import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

type Tone = 'ok' | 'error' | 'warn';
interface ToastMsg { text: string; tone: Tone; }

const Ctx = createContext<(text: string, tone?: Tone, ms?: number) => void>(() => {});

export function useToast() {
  return useContext(Ctx);
}

const toneClass: Record<Tone, string> = {
  ok: 'bg-ink text-bg',
  error: 'bg-danger text-white',
  warn: 'bg-warning text-white',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<ToastMsg | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((text: string, tone: Tone = 'ok', ms = 2600) => {
    setMsg({ text, tone });
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), ms);
  }, []);

  return (
    <Ctx.Provider value={show}>
      {children}
      {msg && (
        <div
          role="status"
          className={
            'fixed bottom-6 left-1/2 z-toast max-w-md -translate-x-1/2 rounded-md px-5 py-3 text-center text-sm font-medium shadow-lg ' +
            toneClass[msg.tone]
          }
        >
          {msg.text}
        </div>
      )}
    </Ctx.Provider>
  );
}
