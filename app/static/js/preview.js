const previewShell = document.querySelector('[data-preview-mode="review"]');

if (previewShell) {
    const configEl = document.getElementById("preview-config");
    const config = configEl ? JSON.parse(configEl.textContent) : {};

    const previewId = config.previewId || previewShell.getAttribute("data-preview-id");
    const conversationId = config.conversationId || previewShell.getAttribute("data-conversation-id");
    let selectedVariantId = config.selectedVariantId || previewShell.getAttribute("data-selected-variant");
    let selectedVariant = config.selectedVariant || {};
    let recentConversations = Array.isArray(config.recentConversations) ? config.recentConversations : [];

    const frameBaseUrl = config.frameUrl || previewShell.getAttribute("data-frame-url") || ("/preview/" + previewId + "/frame");
    const navPublishBtn = document.getElementById("nav-publish-btn");
    const navExportBtn = document.getElementById("nav-export-btn");
    const previewFrame = document.getElementById("preview-frame");
    const canvasShell = document.getElementById("canvas-shell");
    const previewConversationTitle = document.getElementById("preview-conversation-title");
    const previewStatus = document.getElementById("preview-status");
    const recentConversationList = document.getElementById("workspace-conversation-list");
    const conversationForm = document.getElementById("conversation-form");
    const conversationInput = document.getElementById("conversation-input");
    const sendMessageBtn = document.getElementById("send-message-btn");

    let busy = false;

    function setStatus(message) {
        if (previewStatus) {
            previewStatus.textContent = message || "";
        }
    }

    function setBusy(isBusy, label) {
        busy = isBusy;
        [navPublishBtn, navExportBtn, sendMessageBtn].forEach((button) => {
            if (button) {
                button.disabled = isBusy;
            }
        });
        document.querySelectorAll("[data-variant-id], [data-prompt-suggestion]").forEach((button) => {
            button.disabled = isBusy;
        });
        if (conversationInput) {
            conversationInput.disabled = isBusy;
        }
        if (sendMessageBtn) {
            sendMessageBtn.setAttribute("aria-label", isBusy && label ? label : "Send prompt");
        }
    }

    function syncComposerHeight() {
        if (!conversationInput) {
            return;
        }
        conversationInput.style.height = "auto";
        conversationInput.style.height = Math.min(conversationInput.scrollHeight, 160) + "px";
    }

    function primePrompt(message) {
        if (!conversationInput) {
            return;
        }
        conversationInput.value = String(message || "").trim();
        syncComposerHeight();
        conversationInput.focus();
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

    function updateConversationMeta(conversation) {
        if (!conversation || !previewConversationTitle) {
            return;
        }
        previewConversationTitle.textContent = conversation.title || previewConversationTitle.textContent;
    }

    function updateVariantMeta(variant) {
        selectedVariant = variant || selectedVariant;
    }

    function syncVariantSelection() {
        document.querySelectorAll("[data-variant-id]").forEach((button) => {
            const isSelected = button.getAttribute("data-variant-id") === selectedVariantId;
            button.classList.toggle("is-selected", isSelected);
            button.setAttribute("aria-pressed", isSelected ? "true" : "false");
        });
    }

    function buildFrameUrl(extraParams) {
        const url = new URL(frameBaseUrl, window.location.origin);
        const params = extraParams || {};
        url.searchParams.set("embed", "1");
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                url.searchParams.set(key, value);
            }
        });
        url.searchParams.set("_", Date.now().toString());
        return url.pathname + url.search;
    }

    function refreshPreviewFrame() {
        if (previewFrame) {
            previewFrame.src = buildFrameUrl();
        }
    }

    function applyResponseData(data, statusMessage) {
        if (data.selected_variant_id) {
            selectedVariantId = data.selected_variant_id;
        }
        if (data.selected_variant) {
            updateVariantMeta(data.selected_variant);
        }
        if (data.conversation) {
            updateConversationMeta(data.conversation);
        }
        if (Array.isArray(data.recent_conversations)) {
            recentConversations = data.recent_conversations;
            renderRecentConversations(recentConversations);
        }
        syncVariantSelection();
        refreshPreviewFrame();
        setStatus(statusMessage);
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
        const response = await fetch("/preview/" + previewId + "/export", { method: "POST" });
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
        const filename = match ? match[1] : "velosite-" + previewId + ".zip";
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
        const data = await postJson("/preview/" + previewId + "/publish", {
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

    async function submitPrompt(message) {
        if (busy) {
            return;
        }
        const nextMessage = String(message || "").trim();
        if (!nextMessage) {
            setStatus("Write a follow-up prompt first.");
            return;
        }

        setBusy(true, "Sending...");
        setStatus("Updating this preview…");
        try {
            const data = await postJson("/conversations/" + conversationId + "/messages", {
                message: nextMessage,
                variant_id: selectedVariantId,
            });
            if (conversationInput) {
                conversationInput.value = "";
                syncComposerHeight();
            }
            applyResponseData(data, "Preview updated.");
        } catch (error) {
            setStatus(error.message || "Could not update the preview.");
        } finally {
            setBusy(false);
        }
    }

    if (conversationForm) {
        conversationForm.addEventListener("submit", (event) => {
            event.preventDefault();
            submitPrompt(conversationInput ? conversationInput.value : "");
        });
    }

    if (conversationInput) {
        conversationInput.addEventListener("input", syncComposerHeight);
        conversationInput.addEventListener("keydown", (event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                event.preventDefault();
                submitPrompt(conversationInput.value);
            }
        });
        syncComposerHeight();
    }

    document.querySelectorAll("[data-prompt-suggestion]").forEach((button) => {
        button.addEventListener("click", () => {
            const suggestion = button.getAttribute("data-prompt-suggestion") || "";
            if (!conversationInput) {
                submitPrompt(suggestion);
                return;
            }
            primePrompt(suggestion);
            setStatus("Suggestion loaded — edit or send.");
        });
    });

    document.querySelectorAll("[data-variant-id]").forEach((button) => {
        button.addEventListener("click", async () => {
            if (busy) {
                return;
            }
            selectedVariantId = button.getAttribute("data-variant-id");
            syncVariantSelection();
            setBusy(true, "Switching...");
            setStatus("Switching direction…");
            try {
                const data = await postJson("/preview/" + previewId + "/override", { variant_id: selectedVariantId });
                applyResponseData(data, "Direction switched.");
            } catch (error) {
                setStatus(error.message || "Could not switch direction.");
            } finally {
                setBusy(false);
            }
        });
    });

    document.querySelectorAll(".device-btn").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".device-btn").forEach((item) => item.classList.remove("is-active"));
            button.classList.add("is-active");
            if (!canvasShell) {
                return;
            }
            canvasShell.classList.remove("device-desktop", "device-tablet", "device-mobile");
            canvasShell.classList.add("device-" + button.getAttribute("data-device"));
        });
    });

    if (navPublishBtn) {
        navPublishBtn.addEventListener("click", async () => {
            if (busy) {
                return;
            }
            setStatus("Publishing live link…");
            try {
                const data = await postPublish();
                const link = data.public_url || data.public_path || "";
                if (link) {
                    window.open(link, "_blank", "noopener,noreferrer");
                }
                setStatus(link ? "Published — " + link : "Published.");
            } catch (error) {
                setStatus(error.message || "Publish failed.");
            }
        });
    }

    if (navExportBtn) {
        navExportBtn.addEventListener("click", async () => {
            if (busy) {
                return;
            }
            setStatus("Preparing ZIP export…");
            try {
                await postExport();
                setStatus("Export complete.");
            } catch (error) {
                setStatus(error.message || "Export failed.");
            }
        });
    }

    if (previewFrame) {
        previewFrame.addEventListener("load", () => {
            if (!previewStatus || !previewStatus.textContent) {
                setStatus("");
            }
        });
    }

    updateVariantMeta(selectedVariant);
    renderRecentConversations(recentConversations);
    syncVariantSelection();
}
