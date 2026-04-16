// My Styles — browse, create, and manage custom visual styles.

import { api } from "../api.js";
import { h, icons, emptyState, pageHeader, toast, $ } from "../components.js";

let grid;
let styleOverlay;

export async function mount(outlet) {
  const page = h("div", { class: "page" }, [
    pageHeader({
      kicker: "My Studio",
      title: "My Styles",
      subtitle: "Create and manage visual styles for your content. Each style includes a DNA profile, reference images, and AI-generated prompts.",
    }),

    h("div", { class: "channel-cards-grid", id: "ms-grid" }),
  ]);

  outlet.appendChild(page);
  grid = $("#ms-grid");

  loadStyles();
}

async function loadStyles() {
  grid.innerHTML = h("div", { class: "ms-spinner" }).outerHTML;

  try {
    const r = await api.stylesCustom();
    const items = r.items || [];
    renderGrid(items);
  } catch (err) {
    grid.innerHTML = emptyState(`Failed to load styles: ${err.message}`).outerHTML;
  }
}

function renderGrid(items) {
  grid.innerHTML = "";

  // Add prominent "Create New Style" card first
  grid.appendChild(createNewStyleCard());

  if (!items.length) {
    return;
  }

  for (const s of items) {
    grid.appendChild(styleCard(s));
  }
}

function createNewStyleCard() {
  const card = h("div", { class: "ms-card ms-card-create" }, [
    h("div", { class: "ms-card-create-icon", html: icons.sparkle || "✨" }),
    h("div", { class: "ms-card-create-body" }, [
      h("div", { class: "ms-card-create-title" }, ["Create New Style"]),
      h("div", { class: "ms-card-create-desc" }, [
        "Upload reference images and AI will analyze your unique visual style",
      ]),
    ]),
    h("button", {
      class: "btn primary ms-card-create-btn",
      onclick: (e) => {
        e.stopPropagation();
        openCreateModal();
      },
    }, ["Start Creating"]),
  ]);
  return card;
}

function styleCard(s) {
  const card = h("div", { class: "ms-card" });

  // Preview image or placeholder
  const preview = s.preview_image_path
    ? h("img", {
        class: "ms-card-preview",
        src: api.stylePreviewImageUrl(s.uuid),
        alt: s.name,
      })
    : h("div", { class: "ms-card-preview-placeholder" }, [
        s.type === "preset" ? "Preset Style" : "Preview pending…",
      ]);

  // Body: name + description
  const body = h("div", { class: "ms-card-body" }, [
    h("div", { class: "ms-card-name" }, [s.name]),
    s.description ? h("p", { class: "ms-card-desc" }, [s.description]) : null,
  ].filter(Boolean));

  // Reference images strip
  const refStrip = h("div", { class: "ms-card-refs" });
  const imagePaths = s.image_paths || [];
  for (let i = 0; i < Math.min(3, imagePaths.length); i++) {
    refStrip.appendChild(
      h("img", {
        class: "ms-card-ref-img",
        src: api.styleRefImageUrl(s.uuid, i),
        alt: `Ref ${i + 1}`,
      })
    );
  }

  // Actions
  const actions = h("div", { class: "ms-card-actions" }, [
    h("button", {
      class: "btn primary ms-use-btn",
      onclick: (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(s.id).then(() => {
          toast(`Style ID copied: ${s.id}`, { kind: "success" });
        });
      },
    }, ["Use in Production"]),
  ]);

  card.appendChild(preview);
  card.appendChild(body);
  card.appendChild(refStrip);
  card.appendChild(actions);

  // Click card (not button) to open overlay
  card.addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") {
      openStyleOverlay(s);
    }
  });

  return card;
}

function openStyleOverlay(s) {
  const backdrop = h("div", { class: "ch-ov-backdrop" });
  const panel = h("div", { class: "ms-ov-panel" });

  // Header: preview + identity + close + delete
  const headerPreview = s.preview_image_path
    ? h("img", {
        class: "ms-ov-preview",
        src: api.stylePreviewImageUrl(s.uuid),
        alt: s.name,
      })
    : h("div", { class: "ms-ov-preview ms-card-preview-placeholder" }, [
        "Preview pending",
      ]);

  const identity = h("div", { class: "ms-ov-identity" }, [
    h("div", { class: "ms-ov-name" }, [s.name]),
    s.description ? h("div", { class: "ms-ov-desc" }, [s.description]) : null,
  ].filter(Boolean));

  const headerActions = h("div", { class: "ms-ov-header-actions" }, [
    h("button", {
      class: "btn ghost small",
      html: icons.close,
      onclick: () => backdrop.remove(),
    }),
    // Only show delete for custom styles
    ...(s.type === "custom" ? [
      h("button", {
        class: "btn ghost small",
        html: icons.trash,
        onclick: () => deleteStyle(s.uuid),
      }),
    ] : []),
  ]);

  const header = h("div", { class: "ms-ov-header" }, [
    headerPreview,
    headerActions,
    h("div", { class: "ms-ov-identity-row" }, [identity]),
  ]);

  // Sections
  const sections = [];

  // Style Brief
  sections.push(
    h("div", {}, [
      h("div", { class: "ms-ov-section-label" }, ["Style Brief"]),
      h("pre", { class: "ms-ov-brief" }, [s.style_brief || "(No brief)"]),
    ])
  );

  // Image Prompt Prefix (copyable)
  const prefixWrap = h("div", { class: "ms-ov-prefix-wrap" }, [
    h("pre", { class: "ms-ov-prefix" }, [s.image_prompt_prefix || "(No prefix)"]),
    h("button", {
      class: "btn ghost small ms-ov-copy-btn",
      html: icons.copy,
      onclick: () => {
        navigator.clipboard.writeText(s.image_prompt_prefix || "").then(() => {
          toast("Prefix copied", { kind: "success" });
        });
      },
    }),
  ]);
  sections.push(
    h("div", {}, [
      h("div", { class: "ms-ov-section-label" }, ["Image Prompt Prefix"]),
      prefixWrap,
    ])
  );

  // Reference Images
  const imagePaths = s.image_paths || [];
  if (imagePaths.length > 0) {
    const refsGrid = h("div", { class: "ms-ov-refs-grid" });
    for (let i = 0; i < imagePaths.length; i++) {
      refsGrid.appendChild(
        h("img", {
          class: "ms-ov-ref-img",
          src: api.styleRefImageUrl(s.uuid, i),
          alt: `Reference ${i + 1}`,
        })
      );
    }
    sections.push(
      h("div", {}, [
        h("div", { class: "ms-ov-section-label" }, ["Reference Images"]),
        refsGrid,
      ])
    );
  }

  // Generate Prompt for Topic
  const promptInput = h("input", {
    class: "input",
    type: "text",
    placeholder: "e.g., quantum computing explained",
  });
  const generateBtn = h("button", { class: "btn primary" }, ["Generate"]);
  const promptResult = h("pre", { class: "ms-ov-prompt-result" }, []);

  generateBtn.onclick = async () => {
    const topic = promptInput.value.trim();
    if (!topic) {
      toast("Enter a topic", { kind: "warning" });
      return;
    }

    generateBtn.disabled = true;
    generateBtn.textContent = "Generating…";

    try {
      const r = await api.styleGeneratePrompt(s.uuid, topic);
      promptResult.textContent = r.prompt;
      promptResult.classList.add("visible");
    } catch (err) {
      toast(`Error: ${err.message}`, { kind: "error" });
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "Generate";
    }
  };

  sections.push(
    h("div", {}, [
      h("div", { class: "ms-ov-section-label" }, ["Generate Prompt for Topic"]),
      h("div", { class: "ms-ov-prompt-form" }, [
        promptInput,
        generateBtn,
      ]),
      promptResult,
    ])
  );

  // Assemble panel
  panel.appendChild(header);
  sections.forEach((sec) => panel.appendChild(sec));

  backdrop.appendChild(panel);
  document.body.appendChild(backdrop);

  backdrop.onclick = (e) => {
    if (e.target === backdrop) backdrop.remove();
  };

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") backdrop.remove();
  }, { once: true });
}

function deleteStyle(uuid) {
  if (!confirm("Delete this style? This cannot be undone.")) return;

  (async () => {
    try {
      await api.styleDelete(uuid);
      toast("Style deleted", { kind: "success" });
      document.querySelector(".ch-ov-backdrop")?.remove();
      loadStyles();
    } catch (err) {
      toast(`Error: ${err.message}`, { kind: "error" });
    }
  })();
}

function openCreateModal() {
  const backdrop = h("div", { class: "ch-ov-backdrop" });
  const panel = h("div", { class: "ms-modal-panel" });

  const nameInput = h("input", {
    class: "input",
    type: "text",
    placeholder: "e.g., Dark Cinematic",
  });

  const descInput = h("textarea", {
    class: "input",
    placeholder: "Optional description of the style",
    rows: 3,
  });

  const uploadZone = h("div", { class: "ms-upload-zone" }, [
    "Click or drag images here (1-5 files, JPG/PNG)",
  ]);
  const fileInput = h("input", {
    type: "file",
    multiple: true,
    accept: "image/*",
    style: "display: none;",
  });
  const thumbsContainer = h("div", { class: "ms-upload-thumbs" });

  let selectedFiles = [];

  uploadZone.onclick = () => fileInput.click();
  uploadZone.ondragover = (e) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  };
  uploadZone.ondragleave = () => uploadZone.classList.remove("dragover");
  uploadZone.ondrop = (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    handleFiles(e.dataTransfer.files);
  };

  fileInput.onchange = () => handleFiles(fileInput.files);

  function handleFiles(files) {
    selectedFiles = Array.from(files).slice(0, 5);
    thumbsContainer.innerHTML = "";

    for (const f of selectedFiles) {
      const reader = new FileReader();
      reader.onload = (e) => {
        thumbsContainer.appendChild(
          h("img", {
            class: "ms-upload-thumb",
            src: e.target.result,
            alt: f.name,
          })
        );
      };
      reader.readAsDataURL(f);
    }
  }

  const cancelBtn = h("button", { class: "btn" }, ["Cancel"]);
  const createBtn = h("button", { class: "btn primary" }, ["Create Style"]);

  cancelBtn.onclick = () => backdrop.remove();
  createBtn.onclick = onSubmit;

  const fields = h("div", { class: "ms-modal-fields" }, [
    h("div", {}, [
      h("label", { class: "ms-modal-label" }, ["Name *"]),
      nameInput,
    ]),
    h("div", {}, [
      h("label", { class: "ms-modal-label" }, ["Description (optional)"]),
      descInput,
    ]),
    h("div", {}, [
      h("label", { class: "ms-modal-label" }, ["Reference Images (1–5) *"]),
      uploadZone,
      fileInput,
      thumbsContainer,
    ]),
  ]);

  panel.appendChild(h("div", { class: "ms-modal-title" }, ["New Style"]));
  panel.appendChild(fields);
  panel.appendChild(
    h("div", { class: "ms-modal-actions" }, [cancelBtn, createBtn])
  );

  backdrop.appendChild(panel);
  document.body.appendChild(backdrop);

  backdrop.onclick = (e) => {
    if (e.target === backdrop) backdrop.remove();
  };

  async function onSubmit() {
    const name = nameInput.value.trim();
    const description = descInput.value.trim();

    if (!name) {
      toast("Name is required", { kind: "warning" });
      return;
    }

    if (!selectedFiles.length || selectedFiles.length > 5) {
      toast("Upload 1–5 images", { kind: "warning" });
      return;
    }

    createBtn.disabled = true;
    createBtn.textContent = "Creating…";

    try {
      const fd = new FormData();
      fd.append("name", name);
      fd.append("description", description);
      selectedFiles.forEach((f) => fd.append("images", f));

      const createReq = await fetch("/api/styles", {
        method: "POST",
        body: fd,
      }).then((res) => res.json());

      toast("Style created! Generating preview…", { kind: "success" });
      backdrop.remove();

      // Fire-and-forget preview generation
      const uuid = createReq.id.split(":")[1];
      api.styleGeneratePreview(uuid).catch(() => {});

      // Reload grid after a short delay
      await new Promise((r) => setTimeout(r, 500));
      loadStyles();
    } catch (err) {
      toast(`Error: ${err.message}`, { kind: "error" });
    } finally {
      createBtn.disabled = false;
      createBtn.textContent = "Create Style";
    }
  }
}
