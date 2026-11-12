/** One notification refresh at a time. A request made while one is running is kept as a single follow-up. */
export function createNotificationRefreshGate() {
  let inFlight = false;
  let queued = false;

  return async function run(task) {
    if (inFlight) {
      queued = true;
      return;
    }
    inFlight = true;
    try {
      await task();
    } finally {
      inFlight = false;
    }
    if (queued) {
      queued = false;
      await run(task);
    }
  };
}
