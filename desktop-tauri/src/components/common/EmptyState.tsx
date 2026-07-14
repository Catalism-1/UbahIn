interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="empty-card">
      <span className="empty-icon">{icon}</span>
      <h2>{title}</h2>
      <p>{description}</p>
      {actionLabel && onAction ? (
        <button type="button" className="primary-button" style={{ marginTop: 18 }} onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
