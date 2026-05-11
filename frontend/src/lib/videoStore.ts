// IndexedDB wrapper for offline-storing rendered video blobs.
//
// Schema: DB `lumen_videos`, store `videos`, key=id (string), value=Blob.
// One store, simple CRUD — no migrations needed yet.

const DB_NAME = "lumen_videos";
const STORE = "videos";
const DB_VERSION = 1;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export const videoStore = {
  async put(id: string, blob: Blob): Promise<void> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(blob, id);
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onerror = () => { db.close(); reject(tx.error); };
    });
  },

  async get(id: string): Promise<Blob | undefined> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(id);
      req.onsuccess = () => { db.close(); resolve(req.result as Blob | undefined); };
      req.onerror = () => { db.close(); reject(req.error); };
    });
  },

  async delete(id: string): Promise<void> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onerror = () => { db.close(); reject(tx.error); };
    });
  },

  async listIds(): Promise<string[]> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).getAllKeys();
      req.onsuccess = () => { db.close(); resolve(req.result as string[]); };
      req.onerror = () => { db.close(); reject(req.error); };
    });
  },
};
