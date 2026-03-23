const form = document.getElementById("generate-form");

if (form) {
    const MAX_BRAND_ASSETS = 4;
    const MAX_BRAND_ASSET_BYTES = 1024 * 1024;
    const ALLOWED_BRAND_ASSET_TYPES = new Set([
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "image/svg+xml",
    ]);

    const configEl = document.getElementById("home-config");
    const config = configEl ? JSON.parse(configEl.textContent) : {};

    const generateBtn = document.getElementById("generate-btn");
    const statusText = document.getElementById("status-text");
    const demoBriefBtn = document.getElementById("demo-brief-btn");
    const pipelineProgress = document.getElementById("pipeline-progress");
    const pipelineSteps = Array.from(document.querySelectorAll("[data-stage-key]"));
    const statusBlueprint = Array.isArray(config.statusBlueprint) ? config.statusBlueprint : [];

    const goalInput = document.getElementById("goal-input");
    const audienceInput = document.getElementById("audience-input");
    const toneInput = document.getElementById("tone-input");
    const densityInput = document.getElementById("density-input");
    const motionInput = document.getElementById("motion-input");
    const nameInput = document.getElementById("name-input");
    const notesInput = document.getElementById("notes-input");
    const brandAssetsInput = document.getElementById("brand-assets-input");
    const brandAssetsPreview = document.getElementById("brand-assets-preview");
    const iconStyleInput = document.getElementById("icon-style-input");
    const demoBrief = config.demoBrief || {};

    /* ── Details toggle (progressive disclosure) ── */
    const detailsToggle = document.getElementById("details-toggle");
    const detailsPanel = document.getElementById("details-panel");

    if (detailsToggle && detailsPanel) {
        detailsToggle.addEventListener("click", () => {
            const isOpen = detailsPanel.classList.toggle("is-open");
            detailsToggle.classList.toggle("is-open", isOpen);
        });
    }

    let pipelineTicker = null;
    let pipelineIndex = 0;

    function setStageState(stageEl, state) {
        stageEl.classList.remove("pipeline-pending", "pipeline-active", "pipeline-complete", "pipeline-done", "pipeline-error");
        stageEl.classList.add(`pipeline-${state}`);
    }

    function resetPipeline() {
        pipelineSteps.forEach((stageEl, index) => {
            setStageState(stageEl, "pending");
            const detail = statusBlueprint[index]?.detail;
            const detailEl = stageEl.querySelector("span");
            if (detail && detailEl) {
                detailEl.textContent = detail;
            }
        });
    }

    function stopPipelineTicker() {
        if (!pipelineTicker) {
            return;
        }
        window.clearInterval(pipelineTicker);
        pipelineTicker = null;
    }

    function renderPipelineProgress(activeIndex) {
        pipelineSteps.forEach((stageEl, index) => {
            if (index < activeIndex) {
                setStageState(stageEl, "done");
                return;
            }
            if (index === activeIndex) {
                setStageState(stageEl, "active");
                return;
            }
            setStageState(stageEl, "pending");
        });
    }

    function startPipelineTicker() {
        resetPipeline();
        if (pipelineProgress) {
            pipelineProgress.style.display = "";
        }
        if (!pipelineSteps.length) {
            return;
        }
        pipelineIndex = 0;
        renderPipelineProgress(pipelineIndex);
        pipelineTicker = window.setInterval(() => {
            pipelineIndex = Math.min(pipelineIndex + 1, pipelineSteps.length - 1);
            renderPipelineProgress(pipelineIndex);
        }, 950);
    }

    function markPipelineError() {
        if (!pipelineSteps.length) {
            return;
        }
        const index = Math.max(0, Math.min(pipelineIndex, pipelineSteps.length - 1));
        setStageState(pipelineSteps[index], "error");
    }

    function applyServerStatuses(statuses) {
        if (!Array.isArray(statuses) || !statuses.length) {
            pipelineSteps.forEach((stageEl) => setStageState(stageEl, "done"));
            return;
        }
        const statesByKey = new Map();
        statuses.forEach((item) => {
            if (item && item.key) {
                statesByKey.set(item.key, item);
            }
        });
        pipelineSteps.forEach((stageEl) => {
            const key = stageEl.getAttribute("data-stage-key");
            const stage = statesByKey.get(key);
            const mappedState = stage?.state === "complete" || stage?.state === "done" || stage?.state === "active" || stage?.state === "error"
                ? (stage.state === "complete" ? "done" : stage.state)
                : "pending";
            setStageState(stageEl, mappedState);
            if (stage?.detail) {
                const detailEl = stageEl.querySelector("span");
                if (detailEl) {
                    detailEl.textContent = stage.detail;
                }
            }
        });
    }

    function setBusy(isBusy, message) {
        if (generateBtn) {
            generateBtn.disabled = isBusy;
            generateBtn.style.opacity = isBusy ? "0.5" : "";
        }
        if (statusText) {
            statusText.textContent = message || "";
        }
    }

    function fileToDataUrl(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ""));
            reader.onerror = () => reject(new Error(`Could not read ${file.name}.`));
            reader.readAsDataURL(file);
        });
    }

    function inferredMimeType(file) {
        if (file.type) {
            return file.type;
        }
        const lowerName = String(file.name || "").toLowerCase();
        if (lowerName.endsWith(".svg")) {
            return "image/svg+xml";
        }
        if (lowerName.endsWith(".png")) {
            return "image/png";
        }
        if (lowerName.endsWith(".webp")) {
            return "image/webp";
        }
        if (lowerName.endsWith(".gif")) {
            return "image/gif";
        }
        if (lowerName.endsWith(".jpg") || lowerName.endsWith(".jpeg")) {
            return "image/jpeg";
        }
        return "";
    }

    function renderAssetPreview(assets) {
        if (!brandAssetsPreview) {
            return;
        }
        brandAssetsPreview.innerHTML = "";
        const items = Array.isArray(assets) ? assets : [];
        if (!items.length) {
            return;
        }
        items.forEach((asset, index) => {
            const card = document.createElement("figure");
            card.className = "asset-preview-card";
            const image = document.createElement("img");
            image.src = asset.data_url;
            image.alt = asset.alt || asset.name || `Brand asset ${index + 1}`;
            const caption = document.createElement("figcaption");
            caption.textContent = `${asset.name || `Brand asset ${index + 1}`}${index === 0 ? " • Primary mark" : ""}`;
            card.appendChild(image);
            card.appendChild(caption);
            brandAssetsPreview.appendChild(card);
        });
    }

    async function serializeBrandAssets(fileList) {
        const files = Array.from(fileList || []).slice(0, MAX_BRAND_ASSETS);
        if (!files.length) {
            return [];
        }

        const invalidType = files.find((file) => !ALLOWED_BRAND_ASSET_TYPES.has(inferredMimeType(file)));
        if (invalidType) {
            throw new Error(`${invalidType.name} is not a supported image type.`);
        }

        const oversized = files.find((file) => file.size > MAX_BRAND_ASSET_BYTES);
        if (oversized) {
            throw new Error(`${oversized.name} is too large. Keep each image under 1 MB.`);
        }

        return Promise.all(
            files.map(async (file, index) => ({
                id: `brand-asset-${index + 1}`,
                name: file.name,
                alt: file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " "),
                mime_type: inferredMimeType(file),
                data_url: await fileToDataUrl(file),
            }))
        );
    }

    /* ── Quick-start chips ── */
    document.querySelectorAll("[data-sample]").forEach((chip) => {
        chip.addEventListener("click", () => {
            goalInput.value = chip.getAttribute("data-sample");
            // Open details panel when using a quick-start
            if (detailsPanel && !detailsPanel.classList.contains("is-open")) {
                detailsPanel.classList.add("is-open");
                if (detailsToggle) detailsToggle.classList.add("is-open");
            }
            if (audienceInput && !audienceInput.value) {
                audienceInput.value = "People ready to buy quickly";
            }
            if (toneInput && !toneInput.value) {
                toneInput.value = "Bold, polished, intentional";
            }
            goalInput.focus();
        });
    });

    /* ── Demo brief chip ── */
    if (demoBriefBtn) {
        demoBriefBtn.addEventListener("click", () => {
            goalInput.value = demoBrief.goal || goalInput.value;
            // Open details panel and fill all fields
            if (detailsPanel && !detailsPanel.classList.contains("is-open")) {
                detailsPanel.classList.add("is-open");
                if (detailsToggle) detailsToggle.classList.add("is-open");
            }
            if (audienceInput) audienceInput.value = demoBrief.audience || audienceInput.value;
            if (toneInput) toneInput.value = demoBrief.brand_tone || toneInput.value;
            if (densityInput) densityInput.value = demoBrief.content_density || densityInput.value;
            if (motionInput) motionInput.value = demoBrief.motion_level || motionInput.value;
            if (nameInput) nameInput.value = demoBrief.name || nameInput.value;
            if (notesInput) notesInput.value = demoBrief.notes || notesInput.value;
            setBusy(false, "Demo prompt loaded. Hit → to generate.");
            goalInput.focus();
        });
    }

    /* ── Brand asset input ── */
    if (brandAssetsInput) {
        brandAssetsInput.addEventListener("change", async () => {
            try {
                const assets = await serializeBrandAssets(brandAssetsInput.files);
                renderAssetPreview(assets);
                if (brandAssetsInput.files.length > MAX_BRAND_ASSETS) {
                    setBusy(false, `Using the first ${MAX_BRAND_ASSETS} brand images.`);
                } else {
                    setBusy(false, assets.length ? "Brand images ready." : "");
                }
            } catch (error) {
                brandAssetsInput.value = "";
                renderAssetPreview([]);
                setBusy(false, error.message || "Could not load brand images.");
            }
        });
    }

    /* ── Form submit ── */
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        let brandAssets = [];
        try {
            brandAssets = await serializeBrandAssets(brandAssetsInput ? brandAssetsInput.files : []);
        } catch (error) {
            setBusy(false, error.message || "Could not load brand images.");
            return;
        }
        const brief = {
            goal: goalInput.value.trim(),
            audience: audienceInput ? audienceInput.value.trim() : "",
            brand_tone: toneInput ? toneInput.value.trim() : "",
            content_density: densityInput ? densityInput.value : "balanced",
            motion_level: motionInput ? motionInput.value : "moderate",
            name: nameInput ? nameInput.value.trim() : "",
            notes: notesInput ? notesInput.value.trim() : "",
            brand_assets: brandAssets,
            icon_style: iconStyleInput ? iconStyleInput.value.trim() : "",
        };

        if (!brief.goal) {
            setBusy(false, "Describe what you want to build.");
            goalInput.focus();
            return;
        }

        // Auto-fill audience and tone if empty
        if (!brief.audience) brief.audience = "General audience";
        if (!brief.brand_tone) brief.brand_tone = "Clear and modern";

        setBusy(true, "Starting generation...");
        startPipelineTicker();
        try {
            const response = await fetch("/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: brief.goal, brief }),
            });
            const data = await response.json();
            if (!response.ok || !data.preview_url) {
                throw new Error(data.error || "Generation failed.");
            }
            stopPipelineTicker();
            applyServerStatuses(data.statuses);
            setBusy(true, "Opening Studio...");
            window.location.href = data.preview_url;
        } catch (error) {
            stopPipelineTicker();
            markPipelineError();
            setBusy(false, error.message || "Something went wrong.");
        }
    });

    resetPipeline();
    renderAssetPreview([]);
}
