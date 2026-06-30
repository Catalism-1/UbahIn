import { useEffect, useRef } from 'react';
import { listen } from '@tauri-apps/api/event';

/**
 * Subscribe to a Tauri event and call `handler` on each emission.
 *
 * The listener is registered ONCE when `enabled` becomes true and is only
 * torn down when `enabled` becomes false or the component unmounts.
 * We keep the handler in a ref so the latest version is always called
 * without requiring a re-subscription.
 */
export function useTauriEvent<TPayload>(
  eventName: string,
  handler: (payload: TPayload) => void,
  enabled = true,
): void {
  // Always keep a reference to the latest handler without causing re-effects
  const handlerRef = useRef(handler);
  useEffect(() => {
    handlerRef.current = handler;
  });

  useEffect(() => {
    if (!enabled) return undefined;

    let disposed = false;
    let unlisten: (() => void) | undefined;

    listen<TPayload>(eventName, (event) => {
      handlerRef.current(event.payload);
    })
      .then((fn) => {
        if (disposed) {
          fn();
          return;
        }
        unlisten = fn;
      })
      .catch((error) => {
        console.error(`Gagal memasang listener ${eventName}:`, error);
      });

    return () => {
      disposed = true;
      unlisten?.();
    };
    // Only re-subscribe when the event name or enabled flag changes —
    // NOT when the handler changes (it's accessed via ref).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventName, enabled]);
}
