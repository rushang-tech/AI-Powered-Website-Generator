const shell = document.querySelector("[data-preview-id]");

if (shell) {
    const configEl = document.getElementById("studio-config");
    const config = configEl ? JSON.parse(configEl.textContent) : {};

    const previewId = shell.getAttribute("data-preview-id");
    let selectedVariantId = config.selectedVariantId || shell.getAttribute("data-selected-variant");

    const templateSelect = document.getElementById("template-select");
    const artDirectionSelect = document.getElementById("art-direction-select");
    const layoutModeSelect = document.getElementById("layout-mode-select");
    const densitySelect = document.getElementById("density-select");
    const motionSelect = document.getElementById("motion-select");
    const applyStyleBtn = document.getElementById("apply-style-btn");
    const styleRemixBtn = document.getElementById("style-remix-btn");
    const statusEl = document.getElementById("override-status");
    const canvasShell = document.getElementById("canvas-shell");
    const previewFrame = document.getElementById("preview-frame");
    const remixGrid = document.getElementById("remix-grid");
    const frameBaseUrl = shell.getAttribute("data-frame-url") || `/preview/${previewId}/frame`;
    const layoutLibrary = config.layoutLibrary || {};
    const artDirectionKeys = Array.isArray(config.artDirectionKeys) ? config.artDirectionKeys : [];

    const navExportBtn = document.getElementById("nav-export-btn");
    const regenAllBtn = document.getElementById("regen-all-btn");
    const regenCopyBtn = document.getElementById("regen-copy-btn");
    const fullscreenBtn = document.getElementById("fullscreen-btn");

    let busy = false;

    function setStatus(message) {
        statusEl.textContent = message || "";
    }

    function setBusy(isBusy, label) {
        busy = isBusy;
        [applyStyleBtn, styleRemixBtn, regenAllBtn, regenCopyBtn, navExportBtn].forEach((button) => {
            if (button) {
                button.disabled = isBusy;
                button.classList.toggle("btn-disabled", isBusy);
            }
        });
        applyStyleBtn.textContent = isBusy && label ? label : "Apply Studio Changes";
    }

    function frameDocument() {
        try {
            return previewFrame.contentDocument || previewFrame.contentWindow.document;
        } catch (error) {
            return null;
        }
    }

    function syncLayerVisibility() {
        const doc = frameDocument();
        if (!doc) {
            return;
        }
        document.querySelectorAll("[data-layer-section]").forEach((checkbox) => {
            const sectionName = checkbox.getAttribute("data-layer-section");
            doc.querySelectorAll(`[data-section="${sectionName}"]`).forEach((section) => {
                section.style.display = checkbox.checked ? "" : "none";
            });
        });
    }

    function refreshLayoutOptions() {
        const templateKey = templateSelect.value;
        const layouts = layoutLibrary[templateKey] || [];
        const currentValue = layoutModeSelect.value;
        layoutModeSelect.innerHTML = "";
        layouts.forEach((layoutKey) => {
            const option = document.createElement("option");
            option.value = layoutKey;
            option.textContent = layoutKey.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
            option.selected = layoutKey === currentValue;
            layoutModeSelect.appendChild(option);
        });
        if (!layouts.includes(currentValue) && layouts.length) {
            layoutModeSelect.value = layouts[0];
        }
    }

    function collectSectionVisibility() {
        const sectionVisibility = {};
        document.querySelectorAll("[data-layer-section]").forEach((checkbox) => {
            sectionVisibility[checkbox.getAttribute("data-layer-section")] = checkbox.checked;
        });
        return sectionVisibility;
    }

    function formatLabel(value) {
        return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
    }

    function remixFrameUrl(candidate) {
        const params = new URLSearchParams({
            variant_id: selectedVariantId,
            template_key: candidate.template_key,
            art_direction: candidate.art_direction,
            layout_mode: candidate.layout_mode,
            density: candidate.density,
            motion_level: candidate.motion_level,
            remix_label: candidate.label,
        });
        return `${frameBaseUrl}?${params.toString()}`;
    }

    function buildRemixCandidates() {
        const templateKey = templateSelect.value;
        const layouts = layoutLibrary[templateKey] || [layoutModeSelect.value];
        const currentLayout = layoutModeSelect.value;
        const currentLayoutIndex = Math.max(0, layouts.indexOf(currentLayout));
        const currentArt = artDirectionSelect.value;
        const artPool = artDirectionKeys.filter((key) => key !== currentArt);
        const densityScale = ["airy", "balanced", "dense"];
        const motionScale = ["calm", "moderate", "energetic"];
        const densityPool = [densitySelect.value, ...densityScale.filter((value) => value !== densitySelect.value)];
        const motionPool = [motionSelect.value, ...motionScale.filter((value) => value !== motionSelect.value)];
        const candidates = [];

        for (let index = 0; index < 3; index += 1) {
            const layout = layouts[(currentLayoutIndex + index + 1) % layouts.length] || currentLayout;
            const artDirection = artPool.length ? artPool[index % artPool.length] : currentArt;
            candidates.push({
                label: `Remix ${index + 1}`,
                template_key: templateKey,
                art_direction: artDirection,
                layout_mode: layout,
                density: densityPool[(index + 1) % densityPool.length] || densitySelect.value,
                motion_level: motionPool[(index + 1) % motionPool.length] || motionSelect.value,
            });
        }
        return candidates;
    }

    async function applyRemix(candidate) {
        if (busy) {
            return;
        }
        setBusy(true, "Applying remix...");
        setStatus(`Applying ${candidate.label}...`);
        try {
            const data = await postJson(`/preview/${previewId}/override`, {
                variant_id: selectedVariantId,
                template_key: candidate.template_key,
                art_direction: candidate.art_direction,
                layout_mode: candidate.layout_mode,
                density: candidate.density,
                motion_level: candidate.motion_level,
                section_visibility: collectSectionVisibility(),
            });
            window.location.href = data.preview_url;
        } catch (error) {
            setStatus(error.message || "Failed to apply remix.");
            setBusy(false);
        }
    }

    function renderRemixGrid(candidates) {
        if (!remixGrid) {
            return;
        }
        remixGrid.innerHTML = "";
        candidates.forEach((candidate) => {
            const card = document.createElement("article");
            card.className = "remix-card";

            const heading = document.createElement("h3");
            heading.textContent = candidate.label;
            card.appendChild(heading);

            const meta = document.createElement("p");
            meta.className = "remix-meta";
            meta.textContent = `${formatLabel(candidate.art_direction)} / ${formatLabel(candidate.layout_mode)}`;
            card.appendChild(meta);

            const frame = document.createElement("iframe");
            frame.className = "remix-frame";
            frame.src = remixFrameUrl(candidate);
            frame.title = `${candidate.label} preview`;
            frame.loading = "lazy";
            frame.sandbox = "allow-same-origin allow-scripts";
            card.appendChild(frame);

            const applyBtn = document.createElement("button");
            applyBtn.type = "button";
            applyBtn.className = "btn";
            applyBtn.textContent = `Apply ${candidate.label}`;
            applyBtn.addEventListener("click", () => {
                applyRemix(candidate);
            });
            card.appendChild(applyBtn);

            remixGrid.appendChild(card);
        });
    }

    async function postJson(url, body) {
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body || {}),
        });
        const data = await response.json();
        if (!response.ok || data.ok === false) {
            throw new Error(data.error || "Request failed.");
        }
        return data;
    }

    async function postExport() {
        const response = await fetch(`/preview/${previewId}/export`, { method: "POST" });
        if (!response.ok) {
            let error = "Export failed.";
            try {
                const data = await response.json();
                error = data.error || error;
            } catch (ignored) {
                // Keep the generic message if JSON decoding fails.
            }
            throw new Error(error);
        }
        const blob = await response.blob();
        const disposition = response.headers.get("Content-Disposition") || "";
        const match = disposition.match(/filename=\"?([^"]+)\"?/);
        const filename = match ? match[1] : `velosite-${previewId}.zip`;
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    async function applyOverride() {
        if (busy) {
            return;
        }
        setBusy(true, "Applying...");
        setStatus("Applying design changes...");

        try {
            const data = await postJson(`/preview/${previewId}/override`, {
                variant_id: selectedVariantId,
                template_key: templateSelect.value,
                art_direction: artDirectionSelect.value,
                layout_mode: layoutModeSelect.value,
                density: densitySelect.value,
                motion_level: motionSelect.value,
                section_visibility: collectSectionVisibility(),
            });
            window.location.href = data.preview_url;
        } catch (error) {
            setStatus(error.message || "Failed to apply override.");
            setBusy(false);
        }
    }

    async function regenerate(scope, sectionName = "") {
        if (busy) {
            return;
        }
        setBusy(true, "Regenerating...");
        setStatus("Regenerating preview...");
        try {
            const data = await postJson(`/preview/${previewId}/regenerate`, {
                scope,
                variant_id: selectedVariantId,
                section_name: sectionName,
            });
            window.location.href = data.preview_url;
        } catch (error) {
            setStatus(error.message || "Failed to regenerate preview.");
            setBusy(false);
        }
    }

    templateSelect.addEventListener("change", refreshLayoutOptions);
    applyStyleBtn.addEventListener("click", applyOverride);
    if (styleRemixBtn) {
        styleRemixBtn.addEventListener("click", () => {
            if (busy) {
                return;
            }
            const candidates = buildRemixCandidates();
            renderRemixGrid(candidates);
            setStatus("Remix previews are ready. Apply one to update the studio.");
        });
    }
    regenAllBtn.addEventListener("click", () => regenerate("all"));
    regenCopyBtn.addEventListener("click", () => regenerate("copy"));
    navExportBtn.addEventListener("click", async () => {
        if (busy) {
            return;
        }
        setStatus("Preparing ZIP export...");
        try {
            await postExport();
            setStatus("Export complete.");
        } catch (error) {
            setStatus(error.message || "Export failed.");
        }
    });

    document.querySelectorAll("[data-variant-id]").forEach((button) => {
        button.addEventListener("click", async () => {
            if (busy) {
                return;
            }
            selectedVariantId = button.getAttribute("data-variant-id");
            setStatus("Switching variant...");
            try {
                const data = await postJson(`/preview/${previewId}/override`, { variant_id: selectedVariantId });
                window.location.href = data.preview_url;
            } catch (error) {
                setStatus(error.message || "Failed to switch variant.");
            }
        });
    });

    document.querySelectorAll(".device-btn").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".device-btn").forEach((item) => item.classList.remove("is-active"));
            button.classList.add("is-active");
            canvasShell.classList.remove("device-desktop", "device-tablet", "device-mobile");
            canvasShell.classList.add(`device-${button.getAttribute("data-device")}`);
        });
    });

    document.querySelectorAll("[data-layer-section]").forEach((checkbox) => {
        checkbox.addEventListener("change", syncLayerVisibility);
    });

    document.querySelectorAll("[data-regenerate-section]").forEach((button) => {
        button.addEventListener("click", () => {
            const sectionName = button.getAttribute("data-regenerate-section");
            regenerate("section", sectionName);
        });
    });

    if (fullscreenBtn) {
        fullscreenBtn.addEventListener("click", async () => {
            if (document.fullscreenElement) {
                await document.exitFullscreen();
                return;
            }
            if (canvasShell.requestFullscreen) {
                await canvasShell.requestFullscreen();
            }
        });
    }

    previewFrame.addEventListener("load", syncLayerVisibility);
    refreshLayoutOptions();
}
