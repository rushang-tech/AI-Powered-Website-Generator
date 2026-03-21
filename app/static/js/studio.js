const shell = document.querySelector("[data-preview-id]");

if (shell) {
    const MAX_BRAND_ASSETS = 4;
    const MAX_BRAND_ASSET_BYTES = 1024 * 1024;
    const ALLOWED_BRAND_ASSET_TYPES = new Set([
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "image/svg+xml",
    ]);

    const configEl = document.getElementById("studio-config");
    const config = configEl ? JSON.parse(configEl.textContent) : {};

    const previewId = shell.getAttribute("data-preview-id");
    const conversationId = config.conversationId || shell.getAttribute("data-conversation-id");
    let selectedVariantId = config.selectedVariantId || shell.getAttribute("data-selected-variant");
    let selectedVariant = config.selectedVariant || {};
    let currentBrief = config.brief || {};
    let currentBrandAssets = Array.isArray(currentBrief.brand_assets) ? currentBrief.brand_assets : [];
    let conversationMessages = Array.isArray(config.conversationMessages) ? config.conversationMessages : [];
    let recentConversations = Array.isArray(config.recentConversations) ? config.recentConversations : [];

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
    const layerList = document.getElementById("layer-list");
    const frameBaseUrl = shell.getAttribute("data-frame-url") || `/preview/${previewId}/frame`;
    const layoutLibrary = config.layoutLibrary || {};
    const artDirectionKeys = Array.isArray(config.artDirectionKeys) ? config.artDirectionKeys : [];

    const navPublishBtn = document.getElementById("nav-publish-btn");
    const navExportBtn = document.getElementById("nav-export-btn");
    const regenAllBtn = document.getElementById("regen-all-btn");
    const regenCopyBtn = document.getElementById("regen-copy-btn");
    const fullscreenBtn = document.getElementById("fullscreen-btn");
    const canvasVariantTitle = document.getElementById("canvas-variant-title");
    const canvasVariantSummary = document.getElementById("canvas-variant-summary");
    const generationWarning = document.getElementById("generation-warning");
    const generationWarningCopy = document.getElementById("generation-warning-copy");
    const generationWarningList = document.getElementById("generation-warning-list");
    const brandAssetsInput = document.getElementById("brand-assets-input");
    const brandAssetsPreview = document.getElementById("brand-assets-preview");
    const iconStyleInput = document.getElementById("icon-style-input");
    const applyBrandingBtn = document.getElementById("apply-branding-btn");
    const recentConversationList = document.getElementById("workspace-conversation-list");
    const conversationMessagesEl = document.getElementById("conversation-messages");
    const conversationForm = document.getElementById("conversation-form");
    const conversationInput = document.getElementById("conversation-input");
    const sendMessageBtn = document.getElementById("send-message-btn");

    let busy = false;

    function setStatus(message) {
        statusEl.textContent = message || "";
    }

    function setBusy(isBusy, label) {
        busy = isBusy;
        [applyStyleBtn, styleRemixBtn, regenAllBtn, regenCopyBtn, navPublishBtn, navExportBtn, applyBrandingBtn, sendMessageBtn].forEach((button) => {
            if (button) {
                button.disabled = isBusy;
                button.classList.toggle("btn-disabled", isBusy);
            }
        });
        if (conversationInput) {
            conversationInput.disabled = isBusy;
        }
        if (applyStyleBtn) {
            applyStyleBtn.textContent = isBusy && label ? label : "Apply Studio Changes";
        }
        if (applyBrandingBtn) {
            applyBrandingBtn.textContent = isBusy && label ? label : "Apply Branding";
        }
        if (sendMessageBtn) {
            sendMessageBtn.textContent = isBusy && label ? label : "Send Prompt";
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
            brandAssetsPreview.innerHTML = '<p class="asset-preview-empty">No brand images applied yet.</p>';
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
            return currentBrandAssets;
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

    function renderValidationState(variant) {
        if (!generationWarning || !generationWarningCopy || !generationWarningList) {
            return;
        }
        const validation = variant && variant.validation ? variant.validation : {};
        const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];
        const fallbackUsed = Boolean(validation.fallback_used);

        generationWarning.classList.toggle("is-hidden", !fallbackUsed);
        generationWarningCopy.textContent = fallbackUsed
            ? "Some copy blocks did not come back cleanly from the model, so Studio filled them with backup text."
            : "";
        generationWarningList.innerHTML = "";
        warnings.forEach((warning) => {
            const item = document.createElement("li");
            item.textContent = warning;
            generationWarningList.appendChild(item);
        });
    }

    function renderConversationMessages(messages) {
        if (!conversationMessagesEl) {
            return;
        }
        conversationMessagesEl.innerHTML = "";
        const items = Array.isArray(messages) ? messages : [];
        if (!items.length) {
            const empty = document.createElement("p");
            empty.className = "muted-copy";
            empty.textContent = "No visible chat messages yet.";
            conversationMessagesEl.appendChild(empty);
            return;
        }
        items.forEach((message) => {
            const card = document.createElement("article");
            card.className = `message-card message-${message.role || "assistant"}`;

            const role = document.createElement("span");
            role.className = "message-role";
            role.textContent = String(message.role || "assistant").replace(/\b\w/g, (char) => char.toUpperCase());
            card.appendChild(role);

            const body = document.createElement("p");
            body.textContent = message.body || "";
            card.appendChild(body);

            conversationMessagesEl.appendChild(card);
        });
    }

    function renderRecentConversations(items) {
        if (!recentConversationList) {
            return;
        }
        if (typeof window.renderWorkspaceConversationList === "function") {
            window.renderWorkspaceConversationList(recentConversationList, items);
            return;
        }

        recentConversationList.innerHTML = "";
    }

    function buildFrameUrl(extraParams = {}, studioMode = false) {
        const url = new URL(frameBaseUrl, window.location.origin);
        Object.entries(extraParams).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                url.searchParams.set(key, value);
            }
        });
        if (studioMode) {
            url.searchParams.set("studio", "1");
            url.searchParams.set("_", Date.now().toString());
        }
        return `${url.pathname}${url.search}`;
    }

    function refreshStudioFrame() {
        previewFrame.src = buildFrameUrl({}, true);
    }

    function refreshLayoutOptions() {
        const templateKey = templateSelect.value;
        const layouts = layoutLibrary[templateKey] || [];
        const currentValue = layoutModeSelect.value;
        layoutModeSelect.innerHTML = "";
        layouts.forEach((layoutKey) => {
            const option = document.createElement("option");
            option.value = layoutKey;
            option.textContent = formatLabel(layoutKey);
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
        return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
    }

    function remixFrameUrl(candidate) {
        const params = {
            variant_id: selectedVariantId,
            template_key: candidate.template_key,
            art_direction: candidate.art_direction,
            layout_mode: candidate.layout_mode,
            density: candidate.density,
            motion_level: candidate.motion_level,
            remix_label: candidate.label,
        };
        return buildFrameUrl(params, false);
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

    function updateCanvasMeta(variant) {
        selectedVariant = variant || selectedVariant;
        if (!selectedVariant) {
            return;
        }
        renderValidationState(selectedVariant);
        if (canvasVariantTitle) {
            canvasVariantTitle.textContent = selectedVariant.label || "Variant";
        }
        if (canvasVariantSummary) {
            canvasVariantSummary.textContent = selectedVariant.summary || "";
        }
    }

    function syncControlsFromVariant(variant) {
        const plan = variant && variant.render_plan ? variant.render_plan : null;
        if (!plan) {
            return;
        }
        if (templateSelect) {
            templateSelect.value = plan.template_key || templateSelect.value;
            refreshLayoutOptions();
        }
        if (artDirectionSelect) {
            artDirectionSelect.value = plan.art_direction || artDirectionSelect.value;
        }
        if (layoutModeSelect) {
            layoutModeSelect.value = plan.layout_mode || layoutModeSelect.value;
        }
        if (densitySelect) {
            densitySelect.value = plan.density || densitySelect.value;
        }
        if (motionSelect) {
            motionSelect.value = plan.motion_level || motionSelect.value;
        }
    }

    function syncVariantSelection() {
        document.querySelectorAll("[data-variant-id]").forEach((button) => {
            button.classList.toggle("is-selected", button.getAttribute("data-variant-id") === selectedVariantId);
        });
    }

    function bindLayerControls() {
        document.querySelectorAll("[data-layer-section]").forEach((checkbox) => {
            checkbox.addEventListener("change", async () => {
                try {
                    await runCanvasCommand({
                        action: "toggle_section",
                        section_name: checkbox.getAttribute("data-layer-section"),
                        value: checkbox.checked,
                    }, `Toggling ${checkbox.getAttribute("data-layer-section")}...`);
                } catch (error) {
                    checkbox.checked = !checkbox.checked;
                    setStatus(error.message || "Failed to update section visibility.");
                }
            });
        });

        document.querySelectorAll("[data-regenerate-section]").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                const sectionName = button.getAttribute("data-regenerate-section");
                regenerate("section", sectionName);
            });
        });
    }

    function renderLayerList(variant) {
        if (!layerList || !variant || !variant.render_plan) {
            return;
        }
        const order = variant.render_plan.section_order || [];
        const visibility = variant.render_plan.section_visibility || {};
        layerList.innerHTML = "";
        order.forEach((sectionName, index) => {
            const row = document.createElement("div");
            row.className = "layer-row";
            row.innerHTML = `
                <span class="layer-order">${String(index + 1).padStart(2, "0")}</span>
                <span class="layer-name">${formatLabel(sectionName)}</span>
                <span class="layer-actions">
                    <button class="layer-regen" type="button" data-regenerate-section="${sectionName}">Regenerate</button>
                    <input type="checkbox" data-layer-section="${sectionName}" ${visibility[sectionName] ? "checked" : ""}>
                </span>
            `;
            layerList.appendChild(row);
        });
        bindLayerControls();
    }

    function applyStudioResponse(data, successMessage) {
        selectedVariantId = data.selected_variant_id || selectedVariantId;
        updateCanvasMeta(data.selected_variant);
        syncControlsFromVariant(data.selected_variant);
        renderLayerList(data.selected_variant);
        syncVariantSelection();
        refreshStudioFrame();
        setStatus(successMessage);
        setBusy(false);
    }

    function applyConversationData(data) {
        if (Array.isArray(data.messages)) {
            conversationMessages = data.messages;
            renderConversationMessages(conversationMessages);
        }
        if (Array.isArray(data.recent_conversations)) {
            recentConversations = data.recent_conversations;
            renderRecentConversations(recentConversations);
        }
    }

    async function applyBranding() {
        if (busy) {
            return;
        }
        setBusy(true, "Saving branding...");
        setStatus("Applying brand assets...");
        try {
            const brandAssets = await serializeBrandAssets(brandAssetsInput ? brandAssetsInput.files : []);
            const data = await postJson(`/preview/${previewId}/branding`, {
                brief: {
                    brand_assets: brandAssets,
                    icon_style: iconStyleInput ? iconStyleInput.value.trim() : "",
                },
            });
            currentBrief = data.brief || currentBrief;
            currentBrandAssets = Array.isArray(currentBrief.brand_assets) ? currentBrief.brand_assets : brandAssets;
            renderAssetPreview(currentBrandAssets);
            refreshStudioFrame();
            setStatus("Branding updated in the preview.");
            if (brandAssetsInput) {
                brandAssetsInput.value = "";
            }
        } catch (error) {
            setStatus(error.message || "Failed to update branding.");
        } finally {
            setBusy(false);
        }
    }

    async function sendConversationMessage(event) {
        event.preventDefault();
        if (busy || !conversationInput) {
            return;
        }
        const message = conversationInput.value.trim();
        if (!message) {
            setStatus("Write a follow-up prompt first.");
            return;
        }

        setBusy(true, "Sending...");
        setStatus("Continuing this workspace...");
        try {
            const data = await postJson(`/conversations/${conversationId}/messages`, {
                message,
                variant_id: selectedVariantId,
            });
            conversationInput.value = "";
            applyConversationData(data);
            applyStudioResponse(data, "Conversation update applied.");
        } catch (error) {
            setStatus(error.message || "Could not continue the conversation.");
            setBusy(false);
        }
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
        const match = disposition.match(/filename=\"?([^\"]+)\"?/);
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

    async function postPublish() {
        const data = await postJson(`/preview/${previewId}/publish`, {
            variant_id: selectedVariantId,
        });
        const publicUrl = data.public_url || "";
        if (publicUrl && navigator.clipboard && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(publicUrl);
            } catch (ignored) {
                // Keep going even if clipboard access fails.
            }
        }
        return data;
    }

    async function runCanvasCommand(payload, busyLabel = "Applying canvas edit...") {
        if (busy) {
            return null;
        }
        setBusy(true, busyLabel);
        setStatus(busyLabel);
        try {
            const data = await postJson(`/preview/${previewId}/command`, {
                variant_id: selectedVariantId,
                ...payload,
            });
            selectedVariantId = data.selected_variant_id || selectedVariantId;
            updateCanvasMeta(data.selected_variant);
            syncControlsFromVariant(data.selected_variant);
            renderLayerList(data.selected_variant);
            syncVariantSelection();
            refreshStudioFrame();
            setStatus("Canvas updated.");
            return data;
        } finally {
            setBusy(false);
        }
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
            applyStudioResponse(data, `${candidate.label} applied.`);
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
            applyStudioResponse(data, "Design changes applied.");
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
            applyStudioResponse(data, "Preview regenerated.");
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
    if (brandAssetsInput) {
        brandAssetsInput.addEventListener("change", async () => {
            try {
                const assets = await serializeBrandAssets(brandAssetsInput.files);
                renderAssetPreview(assets);
                setStatus(assets.length ? "Brand images ready to apply." : "");
            } catch (error) {
                brandAssetsInput.value = "";
                renderAssetPreview(currentBrandAssets);
                setStatus(error.message || "Could not load brand images.");
            }
        });
    }
    if (applyBrandingBtn) {
        applyBrandingBtn.addEventListener("click", applyBranding);
    }
    if (conversationForm) {
        conversationForm.addEventListener("submit", sendConversationMessage);
    }
    if (navPublishBtn) {
        navPublishBtn.addEventListener("click", async () => {
            if (busy) {
                return;
            }
            setStatus("Publishing live link...");
            try {
                const data = await postPublish();
                const link = data.public_url || data.public_path || "";
                if (link) {
                    window.open(link, "_blank", "noopener,noreferrer");
                }
                setStatus(link ? `Published: ${link}` : "Published.");
            } catch (error) {
                setStatus(error.message || "Publish failed.");
            }
        });
    }
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
                applyStudioResponse(data, "Variant switched.");
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

    window.addEventListener("message", async (event) => {
        const data = event.data || {};
        if (data.type !== "velosite:command") {
            return;
        }
        if (event.origin !== window.location.origin) {
            return;
        }
        const isFrameSource = event.source === previewFrame.contentWindow;
        const isTrustedBridge = data.source === "velosite-frame-editor";
        if (!isFrameSource && !isTrustedBridge) {
            return;
        }
        const payload = data.payload || {};
        try {
            if (payload.action === "regenerate_section") {
                await regenerate("section", payload.section_name || "");
                return;
            }
            await runCanvasCommand(payload, payload.status_label || "Applying canvas edit...");
        } catch (error) {
            setStatus(error.message || "Canvas action failed.");
        }
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

    previewFrame.addEventListener("load", () => {
        setStatus(statusEl.textContent || "Hover the canvas to reveal direct edit actions.");
    });

    refreshLayoutOptions();
    renderLayerList(selectedVariant);
    updateCanvasMeta(selectedVariant);
    syncControlsFromVariant(selectedVariant);
    syncVariantSelection();
    renderAssetPreview(currentBrandAssets);
    renderConversationMessages(conversationMessages);
    renderRecentConversations(recentConversations);
}
