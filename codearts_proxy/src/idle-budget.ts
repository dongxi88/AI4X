/**
 * Idle budget watchdog timer for streaming/long reasoning requests.
 * Reset on every byte/chunk received; aborts only if completely silent for idleMs.
 */

export interface IdleBudget {
  signal: AbortSignal;
  touch: () => void;
  done: () => void;
}

export function idleBudget(idleMs: number): IdleBudget {
  const controller = new AbortController();
  let timer: NodeJS.Timeout | null = null;

  const done = () => {
    if (timer) clearTimeout(timer);
    timer = null;
  };

  const touch = () => {
    done();
    timer = setTimeout(() => {
      controller.abort(new Error(`Upstream CodeArts kernel silent for ${idleMs}ms`));
    }, idleMs);
  };

  touch();
  return { signal: controller.signal, touch, done };
}
