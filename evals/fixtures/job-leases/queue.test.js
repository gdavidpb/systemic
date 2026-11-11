'use strict';

const { test, mock } = require('node:test');
const assert = require('node:assert/strict');

const { Store } = require('./store');
const q = require('./queue');
const { runOne } = require('./worker');

const T0 = 1_000_000;

async function queueWith(...keys) {
  const store = new Store();
  for (const key of keys) await q.enqueue(store, key, { key });
  return store;
}

test('lease hands a queued job to the worker', async () => {
  const store = await queueWith('a');
  const job = await q.lease(store, 'w1', T0);
  assert.equal(job.status, 'leased');
  assert.equal(job.leasedBy, 'w1');
  assert.equal(job.leaseUntil, T0 + q.LEASE_MS);
});

test('enqueueing the same key again keeps one job', async () => {
  const store = new Store();
  const first = await q.enqueue(store, 'invoice-7', { n: 1 });
  const again = await q.enqueue(store, 'invoice-7', { n: 2 });
  assert.equal(again.id, first.id);
  assert.equal((await store.all()).length, 1);
});

test('two workers never hold the same job', async () => {
  const store = await queueWith('a', 'b');
  // two workers polling at the same time
  const first = await q.lease(store, 'w1', T0);
  const second = await q.lease(store, 'w2', T0);
  assert.notEqual(first.id, second.id);
});

test('only the holder can complete the job', async () => {
  const store = await queueWith('a');
  const stats = { completed: 0 };
  const job = await q.lease(store, 'w1', T0);
  await assert.rejects(() => q.complete(store, stats, job.id, 'w2', T0), q.NotHolder);
  assert.equal((await store.get(job.id)).status, 'leased');
});

test('complete is safe to retry', async () => {
  const store = await queueWith('a');
  const stats = { completed: 0 };
  const job = await q.lease(store, 'w1', T0);
  await q.complete(store, stats, job.id, 'w1', T0 + 10);
  await q.complete(store, stats, job.id, 'w1', T0 + 20);
  assert.equal((await store.get(job.id)).status, 'done');
});

test('a store outage during complete does not count the job', async () => {
  const store = await queueWith('a');
  const stats = { completed: 0 };
  const job = await q.lease(store, 'w1', T0);
  mock.method(store, 'save', async () => {
    throw new Error('store down');
  });
  await assert.rejects(() => q.complete(store, stats, job.id, 'w1', T0 + 10));
  assert.equal(stats.completed, 0);
  assert.equal((await store.get(job.id)).status, 'leased');
});

test('an expired lease returns to the queue', async () => {
  const store = await queueWith('a');
  const job = await q.lease(store, 'w1', T0);
  assert.equal(await q.reap(store, T0 + q.LEASE_MS - 1), 0);
  assert.equal(await q.reap(store, T0 + q.LEASE_MS), 1);
  const stored = await store.get(job.id);
  assert.deepEqual([stored.status, stored.leasedBy, stored.leaseUntil], ['queued', null, null]);
  const stats = { completed: 0 };
  await assert.rejects(() => q.complete(store, stats, job.id, 'w1', T0 + q.LEASE_MS + 1), q.NotHolder);
});

test('a renewed lease lasts another full window', async () => {
  const store = await queueWith('a');
  const job = await q.lease(store, 'w1', T0);
  const renewed = await q.renew(store, job.id, 'w1', T0 + 1_000);
  assert.equal(renewed.leaseUntil, T0 + 1_000 + q.LEASE_MS);
});

test('release is refused unless the job is leased', async () => {
  for (const status of ['queued', 'done', 'dead']) {
    const store = new Store();
    const job = await q.enqueue(store, 'a', {});
    await store.save({ ...job, status });
    await assert.rejects(() => q.release(store, job.id, 'w1', T0), q.NotHolder);
    assert.equal((await store.get(job.id)).status, status);
  }
});

test('a failed job goes back to the queue for another attempt', async () => {
  const store = await queueWith('a');
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    const job = await q.lease(store, 'w1', T0);
    await q.fail(store, job.id, 'w1', T0 + 1, 'handler crashed');
  }
  const [job] = await store.all();
  assert.equal(job.status, 'queued');
  assert.equal(job.attempts, 5);
});

test('the worker completes the job and tells the producer', async () => {
  const store = await queueWith('a');
  const stats = { completed: 0 };
  const notify = mock.fn(async () => {});
  await runOne(store, stats, 'w1', async () => {}, notify, () => T0);
  assert.equal(notify.mock.callCount(), 1);
  assert.equal(stats.completed, 1);
});
