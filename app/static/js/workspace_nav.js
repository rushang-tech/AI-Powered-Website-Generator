const workspaceLayouts = Array.from(document.querySelectorAll("[data-workspace-nav-shell]"));

workspaceLayouts.forEach((layout) => {
    const NAV_COLLAPSE_KEY = "velosite:workspace-nav-collapsed";
    const mobileBreakpoint = window.matchMedia("(max-width: 1100px)");
    const conversationList = layout.querySelector("#workspace-conversation-list");
    const toggles = Array.from(layout.querySelectorAll("[data-nav-toggle]"));
    const closeButtons = Array.from(layout.querySelectorAll("[data-nav-close]"));
    const overlay = layout.querySelector("[data-nav-overlay]");

    function isMobileViewport() {
        return mobileBreakpoint.matches;
    }

    function isCollapsed() {
        return layout.classList.contains("is-nav-collapsed");
    }

    function setCollapsed(collapsed, persist = true) {
        layout.classList.toggle("is-nav-collapsed", Boolean(collapsed) && !isMobileViewport());
        toggles.forEach((button) => {
            button.setAttribute("aria-expanded", String(!layout.classList.contains("is-nav-collapsed")));
        });
        if (persist) {
            window.localStorage.setItem(NAV_COLLAPSE_KEY, collapsed ? "1" : "0");
        }
    }

    function setDrawerOpen(open) {
        layout.classList.toggle("is-nav-open", Boolean(open) && isMobileViewport());
        toggles.forEach((button) => {
            button.setAttribute("aria-expanded", String(layout.classList.contains("is-nav-open")));
        });
    }

    function applyResponsiveState() {
        if (isMobileViewport()) {
            layout.classList.remove("is-nav-collapsed");
            setDrawerOpen(false);
            return;
        }
        const collapsed = window.localStorage.getItem(NAV_COLLAPSE_KEY) === "1";
        setDrawerOpen(false);
        setCollapsed(collapsed, false);
    }

    function conversationMarkup(item) {
        const card = document.createElement("article");
        card.className = `workspace-nav-card ${item.is_active ? "is-active" : ""}`.trim();
        card.setAttribute("data-conversation-item", "");
        card.setAttribute("data-conversation-id", item.id);

        const link = document.createElement("a");
        link.className = "workspace-nav-entry";
        link.href = item.preview_url || "#";
        link.setAttribute("data-nav-close-on-select", "");
        if (item.is_active) {
            link.setAttribute("aria-current", "page");
        }

        const avatar = document.createElement("span");
        avatar.className = "workspace-nav-avatar";
        avatar.textContent = String(item.title || "U").trim().charAt(0).toUpperCase() || "U";
        link.appendChild(avatar);

        const copy = document.createElement("span");
        copy.className = "workspace-nav-copy";
        const title = document.createElement("strong");
        title.setAttribute("data-conversation-title", "");
        title.textContent = item.title || "Untitled conversation";
        copy.appendChild(title);
        const subtitle = document.createElement("span");
        subtitle.textContent = item.is_active ? "Current workspace" : "Open conversation";
        copy.appendChild(subtitle);
        link.appendChild(copy);

        card.appendChild(link);

        const actions = document.createElement("div");
        actions.className = "workspace-nav-actions";

        const renameButton = document.createElement("button");
        renameButton.className = "workspace-nav-action";
        renameButton.type = "button";
        renameButton.setAttribute("data-rename-conversation", item.id);
        renameButton.textContent = "Rename";
        actions.appendChild(renameButton);

        const deleteButton = document.createElement("button");
        deleteButton.className = "workspace-nav-action";
        deleteButton.type = "button";
        deleteButton.setAttribute("data-delete-conversation", item.id);
        deleteButton.textContent = "Delete";
        actions.appendChild(deleteButton);

        card.appendChild(actions);
        return card;
    }

    function renderConversationList(container, items) {
        if (!container) {
            return;
        }
        container.innerHTML = "";
        const list = Array.isArray(items) ? items : [];
        if (!list.length) {
            const empty = document.createElement("p");
            empty.className = "workspace-nav-empty";
            empty.textContent = "No saved conversations yet. Start a new chat to build one.";
            container.appendChild(empty);
            return;
        }
        list.forEach((item) => {
            container.appendChild(conversationMarkup(item));
        });
    }

    async function renameConversation(button) {
        const conversationId = button.getAttribute("data-rename-conversation");
        const card = button.closest("[data-conversation-item]");
        const titleEl = card ? card.querySelector("[data-conversation-title]") : null;
        const currentTitle = titleEl ? titleEl.textContent.trim() : "";
        const nextTitle = window.prompt("Rename conversation", currentTitle);
        if (!nextTitle || !nextTitle.trim()) {
            return;
        }

        const response = await fetch(`/conversations/${conversationId}/rename`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: nextTitle.trim() }),
        });
        const data = await response.json();
        if (!response.ok || !data.conversation) {
            window.alert(data.error || "Could not rename conversation.");
            return;
        }

        if (card) {
            const avatarEl = card.querySelector(".workspace-nav-avatar");
            if (titleEl) {
                titleEl.textContent = data.conversation.title;
            }
            if (avatarEl) {
                avatarEl.textContent = String(data.conversation.title || "U").trim().charAt(0).toUpperCase() || "U";
            }
        }
    }

    async function deleteConversation(button) {
        const conversationId = button.getAttribute("data-delete-conversation");
        const confirmed = window.confirm("Delete this conversation and its chat history?");
        if (!confirmed) {
            return;
        }

        const response = await fetch(`/conversations/${conversationId}`, { method: "DELETE" });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            window.alert(data.error || "Could not delete conversation.");
            return;
        }

        const card = button.closest("[data-conversation-item]");
        const deletingActiveConversation = Boolean(card && card.classList.contains("is-active"));
        if (deletingActiveConversation && data.redirect_url) {
            window.location.href = data.redirect_url;
            return;
        }

        if (card) {
            card.remove();
        }
        if (conversationList && !conversationList.querySelector("[data-conversation-item]")) {
            renderConversationList(conversationList, []);
        }
    }

    toggles.forEach((button) => {
        button.addEventListener("click", () => {
            if (isMobileViewport()) {
                setDrawerOpen(!layout.classList.contains("is-nav-open"));
                return;
            }
            setCollapsed(!isCollapsed());
        });
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", () => setDrawerOpen(false));
    });

    if (overlay) {
        overlay.addEventListener("click", () => setDrawerOpen(false));
    }

    layout.querySelectorAll("[data-nav-close-on-select]").forEach((item) => {
        item.addEventListener("click", () => {
            if (isMobileViewport()) {
                setDrawerOpen(false);
            }
        });
    });

    if (conversationList) {
        conversationList.addEventListener("click", async (event) => {
            const renameButton = event.target.closest("[data-rename-conversation]");
            if (renameButton) {
                event.preventDefault();
                await renameConversation(renameButton);
                return;
            }

            const deleteButton = event.target.closest("[data-delete-conversation]");
            if (deleteButton) {
                event.preventDefault();
                await deleteConversation(deleteButton);
                return;
            }

            if (event.target.closest("[data-nav-close-on-select]") && isMobileViewport()) {
                setDrawerOpen(false);
            }
        });
    }

    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setDrawerOpen(false);
        }
    });

    const handleBreakpointChange = () => applyResponsiveState();
    if (typeof mobileBreakpoint.addEventListener === "function") {
        mobileBreakpoint.addEventListener("change", handleBreakpointChange);
    } else if (typeof mobileBreakpoint.addListener === "function") {
        mobileBreakpoint.addListener(handleBreakpointChange);
    }

    window.renderWorkspaceConversationList = renderConversationList;
    applyResponsiveState();
});
