import type { ReactNode } from 'react';
import './Tooltip.css';

interface TooltipProps {
  label: string;
  children: ReactNode;
  disabled?: boolean;
}

export function Tooltip({ label, children, disabled = false }: TooltipProps) {
  if (disabled) {
    return <>{children}</>;
  }
  return (
    <span className="tooltip-wrap">
      {children}
      <span className="tooltip" role="tooltip">
        {label}
      </span>
    </span>
  );
}
