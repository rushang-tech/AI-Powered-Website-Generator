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

    let pipelineTicker = null;
    let pipelineIndex = 0;

    function setStageState(stageEl, state) {
        stageEl.classList.remove("pipeline-pending", "pipeline-active", "pipeline-complete", "pipeline-error");
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
                setStageState(stageEl, "complete");
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
            pipelineSteps.forEach((stageEl) => setStageState(stageEl, "complete"));
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
            const mappedState = stage?.state === "complete" || stage?.state === "active" || stage?.state === "error"
                ? stage.state
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
        generateBtn.disabled = isBusy;
        generateBtn.classList.toggle("btn-disabled", isBusy);
        generateBtn.textContent = isBusy ? "Building Studio..." : "Generate Studio";
        statusText.textContent = message || "";
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
            brandAssetsPreview.innerHTML = '<p class="asset-preview-empty">No brand images selected yet.</p>';
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

    document.querySelectorAll("[data-sample]").forEach((chip) => {
        chip.addEventListener("click", () => {
            goalInput.value = chip.getAttribute("data-sample");
            if (!audienceInput.value) {
                audienceInput.value = "People ready to buy quickly";
            }
            if (!toneInput.value) {
                toneInput.value = "Bold, polished, intentional";
            }
            notesInput.focus();
        });
    });

    if (demoBriefBtn) {
        demoBriefBtn.addEventListener("click", () => {
            goalInput.value = demoBrief.goal || goalInput.value;
            audienceInput.value = demoBrief.audience || audienceInput.value;
            toneInput.value = demoBrief.brand_tone || toneInput.value;
            densityInput.value = demoBrief.content_density || densityInput.value;
            motionInput.value = demoBrief.motion_level || motionInput.value;
            nameInput.value = demoBrief.name || nameInput.value;
            notesInput.value = demoBrief.notes || notesInput.value;
            setBusy(false, "Demo prompt loaded. Click Generate Studio.");
            notesInput.focus();
        });
    }

    if (brandAssetsInput) {
        brandAssetsInput.addEventListener("change", async () => {
            try {
                const assets = await serializeBrandAssets(brandAssetsInput.files);
                renderAssetPreview(assets);
                if (brandAssetsInput.files.length > MAX_BRAND_ASSETS) {
                    setBusy(false, `Using the first ${MAX_BRAND_ASSETS} brand images.`);
                } else {
                    setBusy(false, assets.length ? "Brand images ready for generation." : "");
                }
            } catch (error) {
                brandAssetsInput.value = "";
                renderAssetPreview([]);
                setBusy(false, error.message || "Could not load brand images.");
            }
        });
    }

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
            audience: audienceInput.value.trim(),
            brand_tone: toneInput.value.trim(),
            content_density: densityInput.value,
            motion_level: motionInput.value,
            name: nameInput.value.trim(),
            notes: notesInput.value.trim(),
            brand_assets: brandAssets,
            icon_style: iconStyleInput ? iconStyleInput.value.trim() : "",
        };
        if (!brief.goal || !brief.audience || !brief.brand_tone) {
            setBusy(false, "Goal, audience, and brand tone are required.");
            return;
        }

        setBusy(true, "Starting generation pipeline...");
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
            setBusy(true, "Generation complete. Opening Studio...");
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
