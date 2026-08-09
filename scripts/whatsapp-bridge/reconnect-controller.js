/**
 * Single-flight reconnect coordination for the WhatsApp bridge.
 *
 * This module is intentionally independent of Baileys so it can be tested
 * without starting a socket or reading the WhatsApp session directory.
 */

export function createReconnectController({
  onReconnect,
  onError = () => {},
  setTimer = setTimeout,
  clearTimer = clearTimeout,
  random = Math.random,
  baseDelayMs = 3000,
  maxDelayMs = 60000,
} = {}) {
  if (typeof onReconnect !== 'function') {
    throw new TypeError('onReconnect must be a function');
  }

  let timer = null;
  let inFlight = false;
  let attempt = 0;
  let generation = 0;
  let pendingReason = null;

  function nextDelay() {
    const exponential = Math.min(maxDelayMs, baseDelayMs * (2 ** attempt));
    // Keep retry timing non-deterministic across processes so multiple
    // bridges do not reconnect in lockstep after a shared upstream outage.
    const jitter = exponential * 0.25 * ((random() * 2) - 1);
    return Math.max(0, Math.round(exponential + jitter));
  }

  async function run(reason) {
    inFlight = true;
    const socketGeneration = ++generation;
    let failed = false;
    try {
      await onReconnect({ reason, generation: socketGeneration });
    } catch (error) {
      failed = true;
      onError(error, reason);
    } finally {
      inFlight = false;
      if (failed) request('startup-error');
    }
  }

  function request(reason = 'unknown') {
    if (timer || inFlight) return false;
    pendingReason = reason;
    const delay = nextDelay();
    attempt += 1;
    timer = setTimer(() => {
      timer = null;
      const scheduledReason = pendingReason;
      pendingReason = null;
      return run(scheduledReason);
    }, delay);
    return true;
  }

  function startNow(reason = 'initial') {
    if (timer) {
      clearTimer(timer);
      timer = null;
      pendingReason = null;
    }
    if (inFlight) return false;
    void run(reason);
    return true;
  }

  function connected() {
    attempt = 0;
  }

  function invalidate() {
    generation += 1;
    return generation;
  }

  function isCurrent(candidateGeneration) {
    return candidateGeneration === generation;
  }

  function state() {
    return {
      scheduled: Boolean(timer),
      inFlight,
      attempt,
      generation,
      pendingReason,
    };
  }

  return {
    request,
    startNow,
    connected,
    invalidate,
    isCurrent,
    state,
  };
}
