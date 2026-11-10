'use strict';

// The jobs table. Reads return copies and writes replace the stored row, like
// a database round trip: two callers that read the same job share nothing.
class Store {
  constructor() {
    this.rows = new Map();
    this.keys = new Map();
    this.nextId = 1;
  }

  async insert(key, payload) {
    if (this.keys.has(key)) {
      return this.get(this.keys.get(key));
    }
    const job = {
      id: `job-${this.nextId++}`,
      key,
      payload,
      status: 'queued',
      attempts: 0,
      leasedBy: null,
      leaseUntil: null,
      lastError: null,
    };
    this.rows.set(job.id, job);
    this.keys.set(key, job.id);
    return structuredClone(job);
  }

  async get(id) {
    const row = this.rows.get(id);
    return row ? structuredClone(row) : null;
  }

  async findQueued() {
    for (const row of this.rows.values()) {
      if (row.status === 'queued') return structuredClone(row);
    }
    return null;
  }

  async findExpired(now) {
    const expired = [];
    for (const row of this.rows.values()) {
      if (row.status === 'leased' && row.leaseUntil <= now) expired.push(structuredClone(row));
    }
    return expired;
  }

  async save(job) {
    this.rows.set(job.id, structuredClone(job));
  }

  async all() {
    return [...this.rows.values()].map((row) => structuredClone(row));
  }
}

module.exports = { Store };
