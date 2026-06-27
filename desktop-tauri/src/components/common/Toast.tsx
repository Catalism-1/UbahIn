import './Toast.css';

export type ToastTone = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  title: string;
  message?: string;
  tone: ToastTone;
}

interface ToastProps {
  messages: ToastMessage[];
}

export function Toast({ messages }: ToastProps) {
  if (messages.length === 0) return null;
  return (
    <div className="toast-stack" aria-live="polite" aria-atomic="true">
      {messages.map((toast) => (
        <div key={toast.id} className={`toast ${toast.tone}`}>
          <strong>{toast.title}</strong>
          {toast.message ? <span>{toast.message}</span> : null}
        </div>
      ))}
    </div>
  );
}
