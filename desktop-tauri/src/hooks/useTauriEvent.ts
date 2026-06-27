import { useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';

export function useTauriEvent<TPayload>(
  eventName: string,
  handler: (payload: TPayload) => void,
  enabled = true,
): void {
  useEffect(() => {
    if (!enabled) return undefined;

    let disposed = false;
    let cleanup: (() => void) | undefined;

    listen<TPayload>(eventName, (event) => {
      handler(event.payload);
    })
      .then((unlisten) => {
        if (disposed) {
          unlisten();
          return;
        }
        cleanup = unlisten;
      })
      .catch((error) => {
        console.error(`Gagal memasang listener ${eventName}:`, error);
      });

    return () => {
      disposed = true;
      cleanup?.();
    };
  }, [enabled, eventName, handler]);
}
