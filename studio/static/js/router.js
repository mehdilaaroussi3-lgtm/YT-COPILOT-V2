// Hash-based SPA router with onMount/onUnmount lifecycle.

const routes = new Map();
let currentRoute = null;
let currentUnmount = null;

export function register(path, module) {
  routes.set(path, module);
}

export function navigate(path, state = null) {
  // Pass state via sessionStorage (survives hash change, not page reload)
  if (state) sessionStorage.setItem(`_route_state_${path}`, JSON.stringify(state));
  if (location.hash === `#${path}`) {
    // Same route — force re-mount
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

  // Unmount previous
  if (typeof currentUnmount === "function") {
    try { currentUnmount(); } catch (e) { console.error(e); }
  }

  // Update sidebar active state
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === path);
  });

  // Mount new
  const outlet = document.getElementById("outlet");
  outlet.innerHTML = "";
  outlet.classList.remove("content-entrance");
  // Force reflow so animation replays
  void outlet.offsetWidth;
  outlet.classList.add("content-entrance");

  try {
    currentUnmount = await route.mount(outlet, {
      query,
      state: consumeState(path),
    });
    currentRoute = path;
  } catch (e) {
    console.error(e);
    outlet.innerHTML = `<div class="card"><h2 class="display-m">Error</h2><p class="body-s" style="margin-top:12px">${e.message}</p></div>`;
  }

  // Scroll to top on navigation
  window.scrollTo(0, 0);
}

export function start() {
  window.addEventListener("hashchange", handleRoute);
  handleRoute();
}
