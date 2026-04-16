/**
 * StylePicker — unified style selector for all generation entry points.
 *
 * Usage:
 *   import { stylePicker } from "../components/style_picker.js";
 *   const picker = await stylePicker({ selected: "dna:UCxxxx", onChange: (id) => {} });
 *   form.appendChild(picker.el);
 *   picker.getValue();   // returns current style_id string
 *
 * The picker fetches /api/styles once, then renders three tabs:
 *   DNA | Presets | Custom
 * Each tab shows its items as a scrollable list. The selected item is
 * highlighted. "Custom" tab has an "Upload new style" button at the bottom.
 */

import { h, icons, toast } from "../components.js";
import { api } from "../api.js";

export async function stylePicker({ selected = "", onChange } = {}) {
    const allStyles = (await api.styles()).items;
    return _buildPicker(allStyles, selected, onChange);
}

// Synchronous variant — call after you already have styles loaded.
export function stylePickerSync(allStyles, { selected = "", onChange } = {}) {
    return _buildPicker(allStyles, selected, onChange);
}

function _buildPicker(allStyles, selected, onChange) {
    let value = selected || "";
    let activeTab = _tabFor(value) || "dna";

    const dnaItems    = allStyles.filter(s => s.style_type === "dna");
    const presetItems = allStyles.filter(s => s.style_type === "preset");
    const customItems = allStyles.filter(s => s.style_type === "custom");

    // ── Build trigger button (shows selected style name) ──────────────────
    const caret = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><polyline points="6 9 12 15 18 9"/></svg>`;

    const triggerLabel = h("span", { class: "sp-trigger-label" }, [_labelFor(value, allStyles)]);
    const trigger = h("button", {
        type: "button", class: "ch-picker-trigger",  // reuse existing CSS
        onclick: (e) => { e.stopPropagation(); toggle(); },
    }, [triggerLabel, h("span", { class: "ch-picker-caret", html: caret })]);

    // ── Tabs ──────────────────────────────────────────────────────────────
    const tabDna    = _tab("DNA",     "dna");
    const tabPreset = _tab("Presets", "preset");
    const tabCustom = _tab("Custom",  "custom");

    const tabBar = h("div", { class: "sp-tabs" }, [tabDna, tabPreset, tabCustom]);

    // ── List areas ────────────────────────────────────────────────────────
    const listEl = h("div", { class: "sp-list" });

    // ── Upload panel (shown in Custom tab at bottom) ───────────────────────
    const uploadPanel = _buildUploadPanel(async (newStyle) => {
        allStyles.push(newStyle);
        customItems.push(newStyle);
        set(newStyle.id);
        renderList();
        close();
        toast(`Custom style "${newStyle.name}" created`, { kind: "success" });
    });

    // ── Menu portal ───────────────────────────────────────────────────────
    const menu = h("div", { class: "ch-picker-menu ch-picker-menu-portal hidden sp-menu" }, [
        tabBar,
        listEl,
        uploadPanel,
    ]);
    document.body.appendChild(menu);

    const wrap = h("div", { class: "ch-picker" }, [trigger]);

    function _tab(label, tabId) {
        const btn = h("button", {
            type: "button",
            class: `sp-tab${tabId === activeTab ? " active" : ""}`,
            onclick: () => { activeTab = tabId; syncTabs(); renderList(); },
        }, [label]);
        btn.dataset.tabId = tabId;
        return btn;
    }

    function syncTabs() {
        for (const btn of tabBar.querySelectorAll(".sp-tab")) {
            btn.classList.toggle("active", btn.dataset.tabId === activeTab);
        }
        uploadPanel.style.display = activeTab === "custom" ? "" : "none";
    }

    function renderList() {
        listEl.innerHTML = "";
        const items =
            activeTab === "dna"    ? dnaItems :
            activeTab === "preset" ? presetItems :
                                     customItems;

        if (!items.length) {
            listEl.appendChild(h("div", { class: "ch-picker-empty" }, [
                activeTab === "custom"
                    ? "No custom styles yet — upload one below."
                    : "None available.",
            ]));
            return;
        }

        for (const s of items) {
            const isActive = s.id === value;
            const row = h("button", {
                type: "button",
                class: `ch-picker-item${isActive ? " active" : ""}`,
                onclick: () => { set(s.id); close(); },
            }, [
                s.thumbnail_url
                    ? h("img", { src: s.thumbnail_url, class: "sp-thumb", alt: "" })
                    : null,
                h("span", { class: "ch-picker-item-label" }, [s.name]),
                isActive ? h("span", { class: "ch-picker-item-check", html: icons.check }) : null,
            ].filter(Boolean));
            listEl.appendChild(row);
        }
    }

    function set(v) {
        value = v;
        activeTab = _tabFor(v) || activeTab;
        triggerLabel.textContent = _labelFor(v, allStyles);
        syncTabs();
        renderList();
        onChange && onChange(value);
    }

    function positionMenu() {
        const r = trigger.getBoundingClientRect();
        menu.style.position = "fixed";
        menu.style.top  = `${r.bottom + 6}px`;
        menu.style.left = `${r.left}px`;
        menu.style.width = `${Math.max(r.width, 320)}px`;
    }

    let open = false;
    function openMenu() {
        open = true;
        positionMenu();
        menu.classList.remove("hidden");
        syncTabs();
        renderList();
    }
    function close() { open = false; menu.classList.add("hidden"); }
    function toggle() { open ? close() : openMenu(); }

    document.addEventListener("click", (e) => {
        if (open && !wrap.contains(e.target) && !menu.contains(e.target)) close();
    });
    window.addEventListener("resize",  () => { if (open) positionMenu(); });
    window.addEventListener("scroll",  () => { if (open) positionMenu(); }, true);

    // Set initial tab label
    triggerLabel.textContent = _labelFor(value, allStyles) || "Select a style";

    return {
        el: wrap,
        getValue: () => value,
        setValue: (v) => set(v),
    };
}

function _tabFor(styleId) {
    if (!styleId) return null;
    const [prefix] = styleId.split(":");
    return prefix === "preset" ? "preset" : prefix === "custom" ? "custom" : "dna";
}

function _labelFor(styleId, items) {
    if (!styleId) return "Select a style";
    const found = items.find(s => s.id === styleId);
    return found ? found.name : styleId;
}

function _buildUploadPanel(onCreated) {
    const nameIn = h("input", { type: "text", class: "input sp-upload-name", placeholder: "Style name" });
    const descIn = h("input", { type: "text", class: "input sp-upload-desc", placeholder: "Brief description (optional)" });
    const fileIn = h("input", { type: "file", accept: "image/*", multiple: true, class: "sp-upload-file" });
    const fileChip = h("label", { class: "file-chip" }, [
        h("span", { html: icons.plus }), " Choose images (1–5)", fileIn,
    ]);
    fileIn.addEventListener("change", () =>
        fileChip.classList.toggle("has-file", fileIn.files.length > 0)
    );
    const uploadBtn = h("button", { type: "button", class: "btn primary sm" }, ["Create style"]);
    const errEl = h("div", { class: "caption", style: { color: "var(--danger)" } }, [""]);

    uploadBtn.addEventListener("click", async () => {
        const name = nameIn.value.trim();
        if (!name) { errEl.textContent = "Name required"; return; }
        if (!fileIn.files.length) { errEl.textContent = "At least 1 image required"; return; }
        if (fileIn.files.length > 5) { errEl.textContent = "Maximum 5 images"; return; }
        errEl.textContent = "";
        uploadBtn.disabled = true;
        uploadBtn.textContent = "Creating…";
        try {
            const fd = new FormData();
            fd.append("name", name);
            fd.append("description", descIn.value.trim());
            for (const f of fileIn.files) fd.append("images", f);
            const res = await fetch("/api/styles", { method: "POST", body: fd });
            if (!res.ok) throw new Error(await res.text());
            const newStyle = await res.json();
            newStyle.style_type = "custom";
            onCreated(newStyle);
            // Reset form
            nameIn.value = "";
            descIn.value = "";
            fileIn.value = "";
            fileChip.classList.remove("has-file");
        } catch (e) {
            errEl.textContent = `Error: ${e.message}`;
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = "Create style";
        }
    });

    const panel = h("div", { class: "sp-upload-panel" }, [
        h("div", { class: "sp-upload-title" }, ["Upload new custom style"]),
        nameIn, descIn, fileChip, errEl, uploadBtn,
    ]);
    panel.style.display = "none";  // shown only on Custom tab
    return panel;
}
