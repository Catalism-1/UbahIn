import { useCallback, useState } from 'react';
import type { ToastMessage, ToastTone } from '../components/common/Toast';

function createId(): string {
  return `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useToasts(timeoutMs = 4200) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback(
    (title: string, tone: ToastTone = 'info', message?: string) => {
      const id = createId();
      setToasts((current) => [...current.slice(-2), { id, title, message, tone }]);
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
      }, timeoutMs);
    },
    [timeoutMs],
  );

  return { toasts, addToast };
}
