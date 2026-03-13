/**
 * Offline Storage Layer — IndexedDB
 * Stores working data locally for offline operation.
 * Sync engine pushes pending changes when connectivity returns.
 */
import { openDB, IDBPDatabase } from 'idb';

const DB_NAME = 'mfi_offline';
const DB_VERSION = 1;

interface SyncQueueItem {
  id: string;
  table: string;
  sync_id: string;
  operation: 'INSERT' | 'UPDATE';
  payload: Record<string, unknown>;
  client_timestamp: string;
  device_id: string;
  status: 'PENDING' | 'SYNCING' | 'SYNCED' | 'FAILED';
  error?: string;
}

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDB(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // Client records cache
        if (!db.objectStoreNames.contains('clients')) {
          const clients = db.createObjectStore('clients', { keyPath: 'id' });
          clients.createIndex('sync_status', 'sync_status');
          clients.createIndex('client_number', 'client_number');
        }
        // Loan records cache
        if (!db.objectStoreNames.contains('loans')) {
          const loans = db.createObjectStore('loans', { keyPath: 'id' });
          loans.createIndex('client_id', 'client_id');
          loans.createIndex('status', 'status');
        }
        // Repayment schedule cache
        if (!db.objectStoreNames.contains('schedules')) {
          db.createObjectStore('schedules', { keyPath: 'id' });
        }
        // Pending repayments (captured offline)
        if (!db.objectStoreNames.contains('pending_repayments')) {
          const repayments = db.createObjectStore('pending_repayments', { keyPath: 'sync_id' });
          repayments.createIndex('status', 'status');
        }
        // Sync queue
        if (!db.objectStoreNames.contains('sync_queue')) {
          const queue = db.createObjectStore('sync_queue', { keyPath: 'id' });
          queue.createIndex('status', 'status');
          queue.createIndex('table', 'table');
        }
        // Metadata (last sync time, device id, etc)
        if (!db.objectStoreNames.contains('metadata')) {
          db.createObjectStore('metadata', { keyPath: 'key' });
        }
      },
    });
  }
  return dbPromise;
}

// ─── Generic CRUD ───

export async function offlineGet<T>(store: string, id: string): Promise<T | undefined> {
  const db = await getDB();
  return db.get(store, id);
}

export async function offlineGetAll<T>(store: string): Promise<T[]> {
  const db = await getDB();
  return db.getAll(store);
}

export async function offlinePut<T>(store: string, data: T): Promise<void> {
  const db = await getDB();
  await db.put(store, data);
}

export async function offlineDelete(store: string, id: string): Promise<void> {
  const db = await getDB();
  await db.delete(store, id);
}

export async function offlineClear(store: string): Promise<void> {
  const db = await getDB();
  await db.clear(store);
}

// ─── Sync Queue ───

export async function addToSyncQueue(item: Omit<SyncQueueItem, 'id' | 'status'>): Promise<string> {
  const db = await getDB();
  const id = crypto.randomUUID();
  await db.put('sync_queue', { ...item, id, status: 'PENDING' });
  return id;
}

export async function getPendingSyncItems(): Promise<SyncQueueItem[]> {
  const db = await getDB();
  return db.getAllFromIndex('sync_queue', 'status', 'PENDING');
}

export async function updateSyncItemStatus(
  id: string, status: SyncQueueItem['status'], error?: string
): Promise<void> {
  const db = await getDB();
  const item = await db.get('sync_queue', id);
  if (item) {
    item.status = status;
    if (error) item.error = error;
    await db.put('sync_queue', item);
  }
}

export async function clearSyncedItems(): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('sync_queue', 'readwrite');
  const index = tx.store.index('status');
  for await (const cursor of index.iterate('SYNCED')) {
    await cursor.delete();
  }
}

// ─── Metadata ───

export async function setMetadata(key: string, value: unknown): Promise<void> {
  const db = await getDB();
  await db.put('metadata', { key, value });
}

export async function getMetadata<T>(key: string): Promise<T | undefined> {
  const db = await getDB();
  const result = await db.get('metadata', key);
  return result?.value;
}

// ─── Bulk Sync (download working set from server) ───

export async function cacheClientsForOffline(clients: unknown[]): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('clients', 'readwrite');
  for (const client of clients) {
    await tx.store.put(client);
  }
  await tx.done;
  await setMetadata('clients_last_sync', new Date().toISOString());
}

export async function cacheLoansForOffline(loans: unknown[]): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('loans', 'readwrite');
  for (const loan of loans) {
    await tx.store.put(loan);
  }
  await tx.done;
  await setMetadata('loans_last_sync', new Date().toISOString());
}

// ─── Offline Repayment Capture ───

export async function captureRepaymentOffline(repayment: {
  loan_id: string;
  amount: number;
  payment_method: string;
  payment_reference?: string;
}): Promise<string> {
  const sync_id = crypto.randomUUID();
  const now = new Date().toISOString();
  const deviceId = await getOrCreateDeviceId();

  const record = {
    sync_id,
    ...repayment,
    received_at: now,
    client_created_at: now,
    device_id: deviceId,
    status: 'PENDING' as const,
  };

  const db = await getDB();
  await db.put('pending_repayments', record);

  // Also add to sync queue
  await addToSyncQueue({
    table: 'repayments',
    sync_id,
    operation: 'INSERT',
    payload: record,
    client_timestamp: now,
    device_id: deviceId,
  });

  return sync_id;
}

// ─── Device ID ───

async function getOrCreateDeviceId(): Promise<string> {
  let deviceId = await getMetadata<string>('device_id');
  if (!deviceId) {
    deviceId = `device_${crypto.randomUUID().slice(0, 8)}`;
    await setMetadata('device_id', deviceId);
  }
  return deviceId;
}

// ─── Connectivity Check ───

export function isOnline(): boolean {
  return typeof navigator !== 'undefined' ? navigator.onLine : true;
}

export function onConnectivityChange(callback: (online: boolean) => void): () => void {
  const handleOnline = () => callback(true);
  const handleOffline = () => callback(false);
  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);
  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  };
}
