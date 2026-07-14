import { useCallback, useEffect, useRef, useState } from 'react';
import { checkEngine } from '../services/engine';
import type { EngineHealth } from '../types/engine';
import type { EngineStatus } from '../types/navigation';

export interface EngineStatusState {
  status: EngineStatus;
  health: EngineHealth | null;
  message: string;
  technicalDetail: string;
  checkedAt: string | null;
  check: () => Promise<void>;
}

function technicalMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}

export function useEngineStatus(): EngineStatusState {
  const [status, setStatus] = useState<EngineStatus>('checking');
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [message, setMessage] = useState('Menyiapkan engine...');
  const [technicalDetail, setTechnicalDetail] = useState('');
  const [checkedAt, setCheckedAt] = useState<string | null>(null);
  const requestSeq = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    return () => {
      mounted.current = false;
    };
  }, []);

  const check = useCallback(async () => {
    const seq = requestSeq.current + 1;
    requestSeq.current = seq;
    setStatus('checking');
    setMessage('Menyiapkan engine...');
    setTechnicalDetail('');

    try {
      const response = await checkEngine();
      if (!mounted.current || requestSeq.current !== seq) return;
      setCheckedAt(new Date().toISOString());

      if (response.ok && response.data) {
        setHealth(response.data);
        setStatus('ready');
        setMessage('Engine siap digunakan.');
        setTechnicalDetail('');
        return;
      }

      setHealth(null);
      setStatus('error');
      setMessage('Engine belum dapat dijalankan. Fitur konversi dijeda sementara.');
      setTechnicalDetail(response.error?.message ?? 'Engine mengembalikan respons gagal tanpa detail.');
    } catch (error) {
      if (!mounted.current || requestSeq.current !== seq) return;
      setCheckedAt(new Date().toISOString());
      setHealth(null);
      setStatus('error');
      setMessage('Engine belum dapat dijalankan. Fitur konversi dijeda sementara.');
      setTechnicalDetail(technicalMessage(error));
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  return {
    status,
    health,
    message,
    technicalDetail,
    checkedAt,
    check,
  };
}
