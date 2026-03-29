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

    /* ── Generation overlay ── */
    const genOverlay = document.getElementById("gen-overlay");
    const genTitle = document.getElementById("gen-title");
    const genStepText = document.getElementById("gen-step-text");
    const genRingFill = document.getElementById("gen-ring-fill");
    const genStepDots = Array.from(document.querySelectorAll("[data-gen-step]"));
    const RING_CIRCUMFERENCE = 276.46;

    let genTicker = null;
    let genIndex = 0;

    function showOverlay() {
        if (genOverlay) {
            genOverlay.classList.add("is-active");
            genOverlay.setAttribute("aria-hidden", "false");
        }
    }

    function hideOverlay() {
        if (genOverlay) {
            genOverlay.classList.remove("is-active");
            genOverlay.setAttribute("aria-hidden", "true");
        }
    }

    function setRingProgress(fraction) {
        if (!genRingFill) return;
        const offset = RING_CIRCUMFERENCE * (1 - Math.min(1, Math.max(0, fraction)));
        genRingFill.style.strokeDashoffset = offset;
    }

    function setStepText(text) {
        if (!genStepText) return;
        genStepText.classList.add("is-fading");
        setTimeout(() => {
            genStepText.textContent = text;
            genStepText.classList.remove("is-fading");
        }, 300);
    }

    function updateStepDots(activeIndex) {
        genStepDots.forEach((dot, index) => {
            dot.classList.remove("is-active", "is-done", "is-pending");
            if (index < activeIndex) {
                dot.classList.add("is-done");
            } else if (index === activeIndex) {
                dot.classList.add("is-active");
            } else {
                dot.classList.add("is-pending");
            }
        });
    }

    function resetOverlay() {
        genIndex = 0;
        setRingProgress(0);
        updateStepDots(0);
        if (genTitle) genTitle.textContent = "Building your site…";
        if (genStepText) genStepText.textContent = "Preparing your brief";
    }

    function startGenTicker() {
        resetOverlay();
        showOverlay();
        if (!statusBlueprint.length) return;

        genIndex = 0;
        updateStepDots(0);
        setStepText(statusBlueprint[0]?.label || "Processing…");
        setRingProgress(0);

        genTicker = window.setInterval(() => {
            genIndex = Math.min(genIndex + 1, statusBlueprint.length - 1);
            updateStepDots(genIndex);
            setStepText(statusBlueprint[genIndex]?.label || "Processing…");
            setRingProgress((genIndex + 1) / statusBlueprint.length);
        }, 950);
    }

    function stopGenTicker() {
        if (genTicker) {
            window.clearInterval(genTicker);
            genTicker = null;
        }
    }

    function markGenComplete() {
        stopGenTicker();
        setRingProgress(1);
        genStepDots.forEach((dot) => {
            dot.classList.remove("is-active", "is-pending");
            dot.classList.add("is-done");
        });
        if (genTitle) genTitle.textContent = "Almost there…";
        setStepText("Opening Preview");
    }

    function markGenError(message) {
        stopGenTicker();
        hideOverlay();
        setBusy(false, message || "Something went wrong.");
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

    /* ── Custom select dropdowns ── */
    document.querySelectorAll("[data-brief-select]").forEach((select) => {
        const trigger = select.querySelector("[data-select-trigger]");
        const dropdown = select.querySelector("[data-select-dropdown]");
        const hiddenInput = select.querySelector("input[type=hidden]");
        const labelEl = select.querySelector("[data-select-label]");
        const options = Array.from(select.querySelectorAll("[data-select-value]"));

        if (!trigger || !dropdown) return;

        trigger.addEventListener("click", (e) => {
            e.stopPropagation();
            document.querySelectorAll("[data-brief-select].is-open").forEach((other) => {
                if (other !== select) other.classList.remove("is-open");
            });
            select.classList.toggle("is-open");
        });

        options.forEach((option) => {
            option.addEventListener("click", () => {
                const value = option.getAttribute("data-select-value");
                if (hiddenInput) hiddenInput.value = value;
                if (labelEl) labelEl.textContent = option.textContent.trim();
                options.forEach((o) => o.classList.remove("is-selected"));
                option.classList.add("is-selected");
                select.classList.remove("is-open");
            });
        });
    });

    document.addEventListener("click", () => {
        document.querySelectorAll("[data-brief-select].is-open").forEach((s) => {
            s.classList.remove("is-open");
        });
    });

    function setSelectValue(selectContainer, value) {
        if (!selectContainer) return;
        const hiddenInput = selectContainer.querySelector("input[type=hidden]");
        const labelEl = selectContainer.querySelector("[data-select-label]");
        const options = selectContainer.querySelectorAll("[data-select-value]");
        if (hiddenInput) hiddenInput.value = value;
        options.forEach((opt) => {
            const isMatch = opt.getAttribute("data-select-value") === value;
            opt.classList.toggle("is-selected", isMatch);
            if (isMatch && labelEl) labelEl.textContent = opt.textContent.trim();
        });
    }

    /* ── Quick-start chips ── */
    document.querySelectorAll("[data-sample]").forEach((chip) => {
        chip.addEventListener("click", () => {
            goalInput.value = chip.getAttribute("data-sample");
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
            if (detailsPanel && !detailsPanel.classList.contains("is-open")) {
                detailsPanel.classList.add("is-open");
                if (detailsToggle) detailsToggle.classList.add("is-open");
            }
            if (audienceInput) audienceInput.value = demoBrief.audience || audienceInput.value;
            if (toneInput) toneInput.value = demoBrief.brand_tone || toneInput.value;
            const densitySelect = densityInput ? densityInput.closest("[data-brief-select]") : null;
            const motionSelect = motionInput ? motionInput.closest("[data-brief-select]") : null;
            if (densitySelect) setSelectValue(densitySelect, demoBrief.content_density || "balanced");
            if (motionSelect) setSelectValue(motionSelect, demoBrief.motion_level || "moderate");
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

        if (!brief.audience) brief.audience = "General audience";
        if (!brief.brand_tone) brief.brand_tone = "Clear and modern";

        setBusy(true, "");
        startGenTicker();
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
            markGenComplete();
            setTimeout(() => {
                window.location.href = data.preview_url;
            }, 600);
        } catch (error) {
            markGenError(error.message || "Something went wrong.");
        }
    });

    renderAssetPreview([]);
}
