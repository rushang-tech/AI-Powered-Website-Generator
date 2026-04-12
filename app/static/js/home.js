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
    const goalValidation = document.getElementById("goal-validation");
    const goalWordCount = document.getElementById("goal-word-count");
    const audienceInput = document.getElementById("audience-input");
    const toneInput = document.getElementById("tone-input");
    const densityInput = document.getElementById("density-input");
    const motionInput = document.getElementById("motion-input");
    const paletteMoodInput = document.getElementById("palette-mood-input");
    const typographyVibeInput = document.getElementById("typography-vibe-input");
    const nameInput = document.getElementById("name-input");
    const notesInput = document.getElementById("notes-input");
    const brandAssetsInput = document.getElementById("brand-assets-input");
    const brandAssetsPreview = document.getElementById("brand-assets-preview");
    const tasteKeywordsInput = document.getElementById("taste-keywords-input");
    const iconStyleInput = document.getElementById("icon-style-input");
    const demoBrief = config.demoBrief || {};
    const GOAL_MIN_WORDS = Number(goalInput?.dataset.minWords || 3);
    const GOAL_MAX_WORDS = Number(goalInput?.dataset.maxWords || 80);

    /* ── Details toggle (progressive disclosure) ── */
    const detailsToggle = document.getElementById("details-toggle");
    const detailsPanel = document.getElementById("details-panel");
    let detailsRevealed = !detailsPanel;
    let busy = false;

    function countWords(value) {
        return String(value || "").trim().match(/[a-z0-9][a-z0-9'’-]*/gi)?.length || 0;
    }

    function getGoalValidation(value) {
        const wordCount = countWords(value);
        if (!wordCount) {
            return {
                wordCount,
                isValid: false,
                message: `Write ${GOAL_MIN_WORDS} to ${GOAL_MAX_WORDS} words so Studio can route the right layout, tone, and structure.`,
            };
        }
        if (wordCount < GOAL_MIN_WORDS) {
            const remaining = GOAL_MIN_WORDS - wordCount;
            return {
                wordCount,
                isValid: false,
                message: `${wordCount} word${wordCount === 1 ? "" : "s"} so far. Add ${remaining} more to make the prompt clear enough.`,
            };
        }
        if (wordCount > GOAL_MAX_WORDS) {
            const overflow = wordCount - GOAL_MAX_WORDS;
            return {
                wordCount,
                isValid: false,
                message: `${wordCount} words is too long. Trim ${overflow} word${overflow === 1 ? "" : "s"} to stay under ${GOAL_MAX_WORDS}.`,
            };
        }
        return {
            wordCount,
            isValid: true,
            message: `${wordCount} words. Good range for generation.`,
        };
    }

    function syncGenerateAvailability() {
        if (!generateBtn) {
            return;
        }
        const validation = getGoalValidation(goalInput ? goalInput.value : "");
        generateBtn.disabled = busy || !validation.isValid;
        generateBtn.style.opacity = generateBtn.disabled ? "0.5" : "";
    }

    function renderGoalValidation() {
        const validation = getGoalValidation(goalInput ? goalInput.value : "");
        const shouldShowInlineMessage = !validation.isValid && validation.wordCount > 0;
        if (goalValidation) {
            goalValidation.textContent = shouldShowInlineMessage ? validation.message : "";
            goalValidation.classList.remove("is-valid");
            goalValidation.classList.toggle("is-invalid", shouldShowInlineMessage);
        }
        if (goalWordCount) {
            goalWordCount.textContent = `${validation.wordCount} / ${GOAL_MAX_WORDS} words`;
            goalWordCount.classList.toggle("is-invalid", validation.wordCount > GOAL_MAX_WORDS);
        }
        syncGenerateAvailability();
        return validation;
    }

    function fillDefaults() {
        if (audienceInput && !audienceInput.value.trim()) {
            audienceInput.value = "General audience";
        }
        if (toneInput && !toneInput.value.trim()) {
            toneInput.value = "Clear and modern";
        }
    }

    function setDetailsOpen(isOpen) {
        if (!detailsPanel) {
            return;
        }
        detailsPanel.classList.toggle("is-open", isOpen);
        if (detailsToggle) {
            detailsToggle.classList.toggle("is-open", isOpen);
            detailsToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }
    }

    function revealDetailsStep({ focusField = false } = {}) {
        if (!detailsPanel) {
            return;
        }
        setDetailsOpen(true);
        detailsRevealed = true;
        detailsPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        if (focusField && audienceInput) {
            audienceInput.focus();
        }
    }

    if (detailsToggle && detailsPanel) {
        setDetailsOpen(detailsPanel.classList.contains("is-open"));
        detailsToggle.addEventListener("click", () => {
            const isOpen = !detailsPanel.classList.contains("is-open");
            setDetailsOpen(isOpen);
            if (isOpen) {
                detailsRevealed = true;
            }
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
        busy = isBusy;
        syncGenerateAvailability();
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

    function parseTasteKeywords(value) {
        const rawItems = String(value || "").split(/[,|\n]+/);
        const output = [];
        const seen = new Set();
        rawItems.forEach((item) => {
            const normalized = item
                .trim()
                .toLowerCase()
                .replace(/[^a-z0-9\s-]+/g, " ")
                .replace(/[\s_]+/g, "-")
                .replace(/-+/g, "-")
                .replace(/^-|-$/g, "");
            if (!normalized || seen.has(normalized)) {
                return;
            }
            seen.add(normalized);
            output.push(normalized);
        });
        return output.slice(0, 8);
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
            fillDefaults();
            renderGoalValidation();
            revealDetailsStep();
            goalInput.focus();
        });
    });

    /* ── Demo brief chip ── */
    if (demoBriefBtn) {
        demoBriefBtn.addEventListener("click", () => {
            goalInput.value = demoBrief.goal || goalInput.value;
            revealDetailsStep();
            fillDefaults();
            if (audienceInput) audienceInput.value = demoBrief.audience || audienceInput.value;
            if (toneInput) toneInput.value = demoBrief.brand_tone || toneInput.value;
            const densitySelect = densityInput ? densityInput.closest("[data-brief-select]") : null;
            const motionSelect = motionInput ? motionInput.closest("[data-brief-select]") : null;
            if (densitySelect) setSelectValue(densitySelect, demoBrief.content_density || "balanced");
            if (motionSelect) setSelectValue(motionSelect, demoBrief.motion_level || "moderate");
            if (paletteMoodInput) paletteMoodInput.value = demoBrief.palette_mood || paletteMoodInput.value;
            if (typographyVibeInput) typographyVibeInput.value = demoBrief.typography_vibe || typographyVibeInput.value;
            if (nameInput) nameInput.value = demoBrief.name || nameInput.value;
            if (tasteKeywordsInput) tasteKeywordsInput.value = demoBrief.taste_keywords || tasteKeywordsInput.value;
            if (notesInput) notesInput.value = demoBrief.notes || notesInput.value;
            renderGoalValidation();
            setBusy(false, "Demo prompt loaded. Hit Run to generate.");
            goalInput.focus();
        });
    }

    if (goalInput) {
        goalInput.addEventListener("input", () => {
            renderGoalValidation();
        });
        goalInput.addEventListener("keydown", (event) => {
            if (event.isComposing || event.key !== "Enter" || event.shiftKey) {
                return;
            }
            if (event.metaKey || event.ctrlKey || event.altKey) {
                return;
            }
            event.preventDefault();
            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
                return;
            }
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
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
        const goal = goalInput.value.trim();
        const validation = renderGoalValidation();

        if (!goal) {
            setBusy(false, "Describe what you want to build.");
            goalInput.focus();
            return;
        }

        if (!validation.isValid) {
            setBusy(false, validation.message);
            goalInput.focus();
            return;
        }

        if (!detailsRevealed) {
            fillDefaults();
            revealDetailsStep({ focusField: true });
            setBusy(false, "Review details below, then hit Run again to generate.");
            return;
        }

        fillDefaults();

        let brandAssets = [];
        try {
            brandAssets = await serializeBrandAssets(brandAssetsInput ? brandAssetsInput.files : []);
        } catch (error) {
            setBusy(false, error.message || "Could not load brand images.");
            return;
        }
        const brief = {
            goal,
            audience: audienceInput ? audienceInput.value.trim() : "",
            brand_tone: toneInput ? toneInput.value.trim() : "",
            content_density: densityInput ? densityInput.value : "balanced",
            motion_level: motionInput ? motionInput.value : "moderate",
            palette_mood: paletteMoodInput ? paletteMoodInput.value : "",
            typography_vibe: typographyVibeInput ? typographyVibeInput.value : "",
            taste_keywords: parseTasteKeywords(tasteKeywordsInput ? tasteKeywordsInput.value : ""),
            name: nameInput ? nameInput.value.trim() : "",
            notes: notesInput ? notesInput.value.trim() : "",
            brand_assets: brandAssets,
            icon_style: iconStyleInput ? iconStyleInput.value.trim() : "",
        };

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

    renderGoalValidation();
    renderAssetPreview([]);
}
