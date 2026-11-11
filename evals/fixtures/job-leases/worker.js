'use strict';

const { lease, complete, fail } = require('./queue');

// One iteration of a worker: take a job, run it, report the result and tell
// the producer. Returns false when the queue is empty.
async function runOne(store, stats, workerId, handler, notify, clock) {
  const job = await lease(store, workerId, clock());
  if (!job) return false;
  try {
    await handler(job.payload);
    await complete(store, stats, job.id, workerId, clock());
    await notify(job.id);
  } catch (err) {
    await fail(store, job.id, workerId, clock(), String(err.message));
  }
  return true;
}

// A worker process drains the queue and exits.
async function drain(store, stats, workerId, handler, notify, clock) {
  let ran = 0;
  while (await runOne(store, stats, workerId, handler, notify, clock)) {
    ran += 1;
  }
  return ran;
}

module.exports = { runOne, drain };
