// SSE wrapper — returns a promise + streams intermediate messages.

export function streamJob(url, { onMessage, onVariant, onError, signal } = {}) {
  return new Promise((resolve, reject) => {
    const es = new EventSource(url);
    const close = () => { try { es.close(); } catch {} };
    if (signal) {
      if (signal.aborted) { close(); return reject(new DOMException("aborted", "AbortError")); }
      signal.addEventListener("abort", () => { close(); reject(new DOMException("aborted", "AbortError")); });
    }
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        onMessage && onMessage(data);
      } catch {}
    };
    es.addEventListener("variant", (e) => {
      try {
        const data = JSON.parse(e.data);
        onVariant && onVariant(data);
      } catch {}
    });
    es.addEventListener("done", (e) => {
      close();
      try { resolve(JSON.parse(e.data)); } catch { resolve(null); }
    });
    es.addEventListener("error", (e) => {
      close();
      let err;
      try { err = JSON.parse(e.data).error; } catch { err = "connection closed"; }
      onError && onError(err);
      reject(new Error(err));
    });
  });
}
