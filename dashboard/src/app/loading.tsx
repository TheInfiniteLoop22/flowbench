import { ColdStartNote } from "@/components/ColdStartNote";

export default function Loading() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6" role="status" aria-live="polite">
      <div className="space-y-2">
        <div className="fb-skeleton h-6 w-64" />
        <div className="fb-skeleton h-4 w-96 max-w-full" />
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="fb-skeleton h-20" />
        ))}
      </div>
      <div className="fb-skeleton h-72" />
      <ColdStartNote />
      <span className="sr-only">Loading</span>
    </div>
  );
}
