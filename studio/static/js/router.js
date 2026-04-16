// Hash-based SPA router with onMount/onUnmount lifecycle.

const routes = new Map();
let currentRoute = null;
let currentUnmount = null;
let mountGeneration = 0; // incremented on every navigation; stale mounts check this

export function register(path, module) {
  routes.set(path, module);
}

export function navigate(path, state = null) {
  if (state) sessionStorage.setItem(`_route_state_${path}`, JSON.stringify(state));
  if (location.hash === `#${path}`) {
    handleRoute();
  } else {
    location.hash = `#${path}`;
  }
}

export function consumeState(path) {
  const key = `_route_state_${path}`;
  const raw = sessionStorage.getItem(key);
  if (!raw) return null;
  sessionStorage.removeItem(key);
  try { return JSON.parse(raw); } catch { return null; }
}

function parseHash() {
  const hash = location.hash.slice(1) || "/home";
  const [path, queryStr] = hash.split("?");
  const query = {};
  if (queryStr) {
    for (const pair of queryStr.split("&")) {
      const [k, v] = pair.split("=");
      query[decodeURIComponent(k)] = decodeURIComponent(v || "");
    }
  }
  return { path, query };
}

async function handleRoute() {
  const { path, query } = parseHash();
  const route = routes.get(path) || routes.get("/home");
  if (!route) return;

  // Claim this navigation slot — any older async mount that finishes
  // after this point will see gen !== mountGeneration and bail out.
  const gen = ++mountGeneration;

  // Unmount previous route
  if (typeof currentUnmount === "function") {
    try { currentUnmount(); } catch (e) { console.error(e); }
    currentUnmount = null;
  }

  // Update sidebar active state
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === path);
  });

  // Replace the outlet element entirely.
  // Any in-flight async mount from the previous route holds a reference to
  // the OLD (now detached) outlet — its DOM writes go nowhere visible.
  const oldOutlet = document.getElementById("outlet");
  const freshOutlet = oldOutlet.cloneNode(false); // same tag + classes, no children
  freshOutlet.classList.remove("content-entrance");
  void freshOutlet.offsetWidth; // force reflow so animation replays
  freshOutlet.classList.add("content-entrance");
  oldOutlet.replaceWith(freshOutlet);

  try {
    const unmount = await route.mount(freshOutlet, {
      query,
      state: consumeState(path),
    });

    // If the user navigated again while this mount was awaiting,
    // discard — a newer handleRoute() already owns the outlet.
    if (gen !== mountGeneration) return;

    currentUnmount = unmount || null;
    currentRoute = path;
  } catch (e) {
    if (gen !== mountGeneration) return;
    console.error(e);
    freshOutlet.innerHTML = `<div class="card"><h2 class="display-m">Error</h2><p class="body-s" style="margin-top:12px">${e.message}</p></div>`;
  }

  window.scrollTo(0, 0);
}

export function start() {
  window.addEventListener("hashchange", handleRoute);
  handleRoute();
}
