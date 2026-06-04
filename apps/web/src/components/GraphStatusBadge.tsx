type GraphStatusBadgeProps = {
  status: string;
};

const toneByStatus: Record<string, string> = {
  pending: "settings-chip--orange",
  running: "settings-chip--blue",
  waiting_for_human: "settings-chip--orange",
  succeeded: "settings-chip--green",
  failed: "workspace-status--error",
  cancelled: "workspace-status--error",
  approved: "settings-chip--green",
  rejected: "workspace-status--error"
};

export function GraphStatusBadge({ status }: GraphStatusBadgeProps) {
  const tone = toneByStatus[status] ?? "settings-chip--blue";
  return <span className={`settings-chip ${tone}`}>{status}</span>;
}
