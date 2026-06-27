import type { ReactNode } from 'react';
import './Tooltip.css';

interface TooltipProps {
  label: string;
  children: ReactNode;
}

export function Tooltip({ label, children }: TooltipProps) {
  return (
    <span className="tooltip-wrap">
      {children}
      <span className="tooltip" role="tooltip">
        {label}
      </span>
    </span>
  );
}
