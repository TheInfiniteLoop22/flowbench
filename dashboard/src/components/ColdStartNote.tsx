export function ColdStartNote() {
  return (
    <p className="text-xs text-muted">
      The API runs on a free tier and sleeps when idle &mdash; the first load after a quiet period can take
      up to a minute while it wakes up.
    </p>
  );
}
