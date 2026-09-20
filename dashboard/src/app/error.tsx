"use client";

import { ColdStartNote } from "@/components/ColdStartNote";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl space-y-4 p-10 text-center">
      <h1 className="text-lg font-semibold">Couldn&apos;t load this page</h1>
      <p className="text-sm text-muted">
        The data API didn&apos;t respond in time. It&apos;s probably waking up from idle &mdash; try again in a
        few seconds.
      </p>
      <button
        onClick={reset}
        className="rounded-lg bg-accent-soft px-4 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/20"
      >
        Try again
      </button>
      <ColdStartNote />
    </div>
  );
}
