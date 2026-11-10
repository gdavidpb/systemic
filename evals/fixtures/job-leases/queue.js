'use strict';

const STATUS = ['queued', 'leased', 'done', 'dead'];
const TERMINAL = ['done', 'dead'];
const LEASE_MS = 30_000;
const MAX_ATTEMPTS = 3;

class NotHolder extends Error {}
class LeaseExpired extends Error {}

function holding(job, workerId, now) {
  if (!job || job.leasedBy !== workerId) {
    throw new NotHolder(`${workerId} does not hold the job`);
  }
  if (job.leaseUntil <= now) {
    throw new LeaseExpired(`the lease of ${workerId} ended at ${job.leaseUntil}`);
  }
}

async function enqueue(store, key, payload) {
  return store.insert(key, payload);
}

async function lease(store, workerId, now) {
  const job = await store.findQueued();
  if (!job) return null;
  job.status = 'leased';
  job.leasedBy = workerId;
  job.leaseUntil = now + LEASE_MS;
  job.attempts += 1;
  await store.save(job);
  return job;
}

async function renew(store, jobId, workerId, now) {
  const job = await store.get(jobId);
  holding(job, workerId, now);
  job.leaseUntil = now + LEASE_MS;
  await store.save(job);
  return job;
}

async function complete(store, stats, jobId, workerId, now) {
  const job = await store.get(jobId);
  holding(job, workerId, now);
  stats.completed += 1;
  job.status = 'done';
  await store.save(job);
  return job;
}

async function fail(store, jobId, workerId, now, reason) {
  const job = await store.get(jobId);
  holding(job, workerId, now);
  job.status = 'queued';
  job.leasedBy = null;
  job.leaseUntil = null;
  job.lastError = reason;
  await store.save(job);
  return job;
}

async function release(store, jobId, workerId, now) {
  const job = await store.get(jobId);
  holding(job, workerId, now);
  job.status = 'queued';
  job.leasedBy = null;
  job.leaseUntil = null;
  await store.save(job);
  return job;
}

async function reap(store, now) {
  let returned = 0;
  for (const job of await store.findExpired(now)) {
    job.status = 'queued';
    job.leasedBy = null;
    job.leaseUntil = null;
    await store.save(job);
    returned += 1;
  }
  return returned;
}

module.exports = {
  STATUS, TERMINAL, LEASE_MS, MAX_ATTEMPTS,
  NotHolder, LeaseExpired,
  enqueue, lease, renew, complete, fail, release, reap,
};
