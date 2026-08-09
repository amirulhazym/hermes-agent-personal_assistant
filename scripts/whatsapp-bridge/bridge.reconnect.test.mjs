/**
 * Regression tests for reconnect storm prevention.
 * These tests do not start Baileys or touch WhatsApp session state.
 */
import { strict as assert } from 'node:assert';
import { createReconnectController } from './reconnect-controller.js';

function fakeTimers() {
  const timers = [];
  return {
    timers,
    setTimer(fn, delay) {
      const timer = { fn, delay, cancelled: false };
      timers.push(timer);
      return timer;
    },
    clearTimer(timer) {
      if (timer) timer.cancelled = true;
    },
    async runNext() {
      const timer = timers.find(item => !item.cancelled && !item.ran);
      assert.ok(timer, 'expected a scheduled timer');
      timer.ran = true;
      await timer.fn();
    },
  };
}

// Repeated close events must produce only one pending reconnect.
{
  const clock = fakeTimers();
  let starts = 0;
  const controller = createReconnectController({
    onReconnect: async () => { starts += 1; },
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
    random: () => 0.5,
  });

  assert.equal(controller.request('405'), true);
  assert.equal(controller.request('405'), false);
  assert.equal(controller.request('503'), false);
  assert.equal(clock.timers.filter(t => !t.cancelled && !t.ran).length, 1);

  await clock.runNext();
  assert.equal(starts, 1);
  assert.equal(controller.request('405'), true, 'a later failure may schedule a new retry');
  assert.equal(clock.timers.filter(t => !t.cancelled && !t.ran).length, 1);
}

// A failed startup must retry, and a successful connection resets backoff.
{
  const clock = fakeTimers();
  let starts = 0;
  let rejectFirst;
  const controller = createReconnectController({
    onReconnect: async () => {
      starts += 1;
      if (starts === 1) throw new Error('startup failed');
    },
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
    random: () => 0.5,
  });

  assert.equal(controller.request('405'), true);
  assert.equal(clock.timers[0].delay, 3000);
  await clock.runNext();
  assert.equal(starts, 1);
  assert.equal(clock.timers.filter(t => !t.cancelled && !t.ran).length, 1);
  assert.equal(clock.timers.find(t => !t.cancelled && !t.ran).delay, 6000);

  await clock.runNext();
  assert.equal(starts, 2);
  controller.connected();
  assert.equal(controller.state().attempt, 0);
  rejectFirst = undefined;
}

console.log('✅ reconnect-controller regression tests passed');
