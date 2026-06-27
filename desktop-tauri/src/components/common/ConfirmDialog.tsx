interface ConfirmDialogProps {
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  open: boolean;
  disabled?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  cancelLabel,
  open,
  disabled = false,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div className="app-modal-root" role="presentation" onMouseDown={onCancel}>
      <section
        className="app-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 id="confirm-dialog-title">{title}</h2>
        <p style={{ color: 'var(--text-2)', lineHeight: 1.6, marginTop: 10 }}>{description}</p>
        <div className="button-row" style={{ justifyContent: 'flex-end', marginTop: 24 }}>
          <button type="button" className="secondary-button" onClick={onCancel} disabled={disabled}>
            {cancelLabel}
          </button>
          <button type="button" className="primary-button" onClick={onConfirm} disabled={disabled}>
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
