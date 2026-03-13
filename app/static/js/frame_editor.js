document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector('[data-preview-root="true"]');
    if (!root || window.parent === window) {
        return;
    }

    document.body.classList.add("frame-editor-ready");

    const hoverCapable = window.matchMedia("(hover: hover)").matches;
    const toolbar = document.createElement("div");
    toolbar.className = "frame-hover-toolbar";
    toolbar.hidden = true;

    const editor = document.createElement("form");
    editor.className = "frame-inline-editor";
    editor.hidden = true;

    const moveMenu = document.createElement("div");
    moveMenu.className = "frame-move-menu";
    moveMenu.hidden = true;

    document.body.append(toolbar, editor, moveMenu);

    let selectedNode = null;

    function resolveParentOrigin() {
        try {
            if (document.referrer) {
                return new URL(document.referrer).origin;
            }
        } catch (error) {
            // Fallback to wildcard when referrer parsing fails.
        }
        return "*";
    }

    function postCommand(payload) {
        window.parent.postMessage(
            { type: "velosite:command", source: "velosite-frame-editor", payload },
            resolveParentOrigin()
        );
    }

    function eventElement(target) {
        if (target instanceof Element) {
            return target;
        }
        if (target instanceof Node) {
            return target.parentElement;
        }
        return null;
    }

    function closestEditable(target) {
        const element = eventElement(target);
        if (!element) {
            return null;
        }
        return element.closest("[data-node-id]");
    }

    function insideFloatingUi(target) {
        const element = eventElement(target);
        return Boolean(element && element.closest(".frame-hover-toolbar, .frame-inline-editor, .frame-move-menu"));
    }

    function sectionForNode(node) {
        if (!node) {
            return null;
        }
        return node.matches('.preview-section[data-node-id]') ? node : node.closest('.preview-section[data-node-id]');
    }

    function clearFocusState() {
        document.querySelectorAll(".is-node-selected").forEach((item) => item.classList.remove("is-node-selected"));
        document.querySelectorAll(".preview-section").forEach((section) => {
            section.classList.remove("is-hovered", "is-dimmed");
        });
        document.body.classList.remove("is-focus-mode");
    }

    function placeFloatingElement(element, node, offsetY = 12) {
        const rect = node.getBoundingClientRect();
        const left = Math.min(window.innerWidth - element.offsetWidth - 12, Math.max(12, rect.left));
        const top = Math.max(12, rect.top - element.offsetHeight - offsetY);
        element.style.left = `${left}px`;
        element.style.top = `${top}px`;
    }

    function setSelectedNode(node) {
        selectedNode = node;
        clearFocusState();
        if (!node) {
            toolbar.hidden = true;
            return;
        }

        node.classList.add("is-node-selected");
        const activeSection = sectionForNode(node);
        if (activeSection) {
            document.body.classList.add("is-focus-mode");
            activeSection.classList.add("is-hovered");
            document.querySelectorAll(".preview-section").forEach((section) => {
                if (section !== activeSection) {
                    section.classList.add("is-dimmed");
                }
            });
        }
        renderToolbar(node);
    }

    function hideEditor() {
        editor.hidden = true;
        editor.innerHTML = "";
    }

    function hideMoveMenu() {
        moveMenu.hidden = true;
        moveMenu.innerHTML = "";
    }

    function renderButton(label, onClick, className = "") {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        if (className) {
            button.className = className;
        }
        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            onClick();
        });
        return button;
    }

    function openSingleFieldEditor(node) {
        const label = node.dataset.nodeType === "button" ? "Button label" : "Edit copy";
        const currentValue = (node.textContent || "").replace(/^"|"$/g, "").trim();
        const editPath = node.dataset.editPath;
        editor.innerHTML = `
            <strong>${label}</strong>
            <label>
                Copy
                <textarea rows="4" name="value">${currentValue}</textarea>
            </label>
            <div class="editor-actions">
                <button type="button" class="editor-save">Save</button>
                <button type="button" class="editor-cancel">Cancel</button>
            </div>
        `;
        editor.hidden = false;
        placeFloatingElement(editor, node, 18);
        const input = editor.querySelector("textarea");
        input.focus();
        const save = () => {
            postCommand({
                action: "set_text",
                node_id: node.dataset.nodeId,
                edit_path: editPath,
                value: input.value,
                status_label: "Saving text...",
            });
            hideEditor();
        };
        editor.querySelector(".editor-save").addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            save();
        });
        editor.querySelector(".editor-cancel").addEventListener("click", hideEditor);
        editor.onsubmit = (event) => {
            event.preventDefault();
            save();
        };
    }

    function openListItemEditor(node) {
        const fields = (node.dataset.editFields || "").split(",").map((field) => field.trim()).filter(Boolean);
        const values = {};
        fields.forEach((field) => {
            const fieldNode = node.querySelector(`[data-item-field="${field}"]`);
            values[field] = fieldNode ? fieldNode.textContent.trim() : "";
        });
        editor.innerHTML = `<strong>Edit card</strong>`;
        fields.forEach((field) => {
            const wrapper = document.createElement("label");
            wrapper.innerHTML = `${field.replace(/\b\w/g, (char) => char.toUpperCase())}<input name="${field}" value="${values[field] || ""}">`;
            editor.appendChild(wrapper);
        });
        const actions = document.createElement("div");
        actions.className = "editor-actions";
        actions.append(
            renderButton("Save", () => {
                const nextValue = {};
                fields.forEach((field) => {
                    nextValue[field] = editor.querySelector(`[name="${field}"]`).value;
                });
                postCommand({
                    action: "set_text",
                    node_id: node.dataset.nodeId,
                    edit_path: node.dataset.editPath,
                    value: nextValue,
                    status_label: "Saving card...",
                });
                hideEditor();
            }, "editor-save"),
            renderButton("Cancel", hideEditor, "editor-cancel")
        );
        editor.appendChild(actions);
        editor.hidden = false;
        placeFloatingElement(editor, node, 18);
        const firstInput = editor.querySelector("input");
        if (firstInput) {
            firstInput.focus();
        }
    }

    function openMoveOptions(node) {
        const isSection = node.dataset.nodeType === "section";
        moveMenu.innerHTML = "";
        const heading = document.createElement("strong");
        heading.textContent = isSection ? "Move section" : "Move card";
        moveMenu.appendChild(heading);
        const actions = document.createElement("div");
        actions.className = "move-actions";
        actions.append(
            renderButton("Move Up", () => {
                postCommand({
                    action: isSection ? "move_section" : "move_item",
                    node_id: node.dataset.nodeId,
                    section_name: node.dataset.sectionName || node.dataset.section,
                    edit_path: node.dataset.editPath,
                    direction: "up",
                    status_label: isSection ? "Moving section up..." : "Moving card up...",
                });
                hideMoveMenu();
            }),
            renderButton("Move Down", () => {
                postCommand({
                    action: isSection ? "move_section" : "move_item",
                    node_id: node.dataset.nodeId,
                    section_name: node.dataset.sectionName || node.dataset.section,
                    edit_path: node.dataset.editPath,
                    direction: "down",
                    status_label: isSection ? "Moving section down..." : "Moving card down...",
                });
                hideMoveMenu();
            }),
            renderButton("Close", hideMoveMenu, "toolbar-ghost")
        );
        moveMenu.appendChild(actions);
        moveMenu.hidden = false;
        placeFloatingElement(moveMenu, node, 18);
    }

    function renderToolbar(node) {
        const nodeType = node.dataset.nodeType;
        const editPath = node.dataset.editPath;
        const sectionName = node.dataset.sectionName || node.dataset.section;
        toolbar.innerHTML = "";

        if (nodeType === "section") {
            toolbar.append(
                renderButton("Improve", () => postCommand({ action: "improve_section", node_id: node.dataset.nodeId, section_name: sectionName, status_label: "Improving section..." })),
                renderButton("Move", () => openMoveOptions(node), "toolbar-ghost"),
                renderButton("Hide", () => postCommand({ action: "toggle_section", node_id: node.dataset.nodeId, section_name: sectionName, value: false, status_label: "Hiding section..." }), "toolbar-ghost"),
                renderButton("Regenerate", () => postCommand({ action: "regenerate_section", section_name: sectionName, status_label: "Regenerating section..." }), "toolbar-ghost")
            );
        } else if (nodeType === "list-item") {
            toolbar.append(
                renderButton("Edit", () => openListItemEditor(node)),
                renderButton("Rewrite", () => postCommand({ action: "rewrite_text", node_id: node.dataset.nodeId, edit_path: editPath, instruction: "Rewrite this card with sharper copy.", status_label: "Rewriting card..." })),
                renderButton("Move", () => openMoveOptions(node), "toolbar-ghost"),
                renderButton("Delete", () => postCommand({ action: "delete_item", node_id: node.dataset.nodeId, edit_path: editPath, status_label: "Deleting card..." }), "toolbar-ghost")
            );
        } else if (nodeType === "button") {
            toolbar.append(
                renderButton("Edit Label", () => openSingleFieldEditor(node)),
                renderButton("Rewrite CTA", () => postCommand({ action: "rewrite_cta", node_id: node.dataset.nodeId, edit_path: editPath, instruction: "Make this CTA more compelling.", status_label: "Rewriting CTA..." })),
                renderButton("Close", () => setSelectedNode(null), "toolbar-ghost")
            );
        } else {
            toolbar.append(
                renderButton("Edit", () => openSingleFieldEditor(node)),
                renderButton("Rewrite", () => postCommand({ action: "rewrite_text", node_id: node.dataset.nodeId, edit_path: editPath, instruction: "Rewrite this website copy.", status_label: "Rewriting text..." })),
                renderButton("Shorter", () => postCommand({ action: "rewrite_text", node_id: node.dataset.nodeId, edit_path: editPath, instruction: "Make this shorter.", status_label: "Shortening text..." }), "toolbar-ghost"),
                renderButton("Punchier", () => postCommand({ action: "rewrite_text", node_id: node.dataset.nodeId, edit_path: editPath, instruction: "Make this more punchy.", status_label: "Sharpening text..." }), "toolbar-ghost")
            );
        }

        toolbar.hidden = false;
        requestAnimationFrame(() => {
            placeFloatingElement(toolbar, node);
        });
    }

    document.addEventListener("mouseover", (event) => {
        if (!hoverCapable || !editor.hidden || !moveMenu.hidden || !toolbar.hidden) {
            return;
        }
        if (insideFloatingUi(event.target)) {
            return;
        }
        const node = closestEditable(event.target);
        if (!node || node === selectedNode) {
            return;
        }
        // Keep the more-specific selection while the pointer moves inside the same card/section.
        if (selectedNode && node.contains(selectedNode)) {
            return;
        }
        setSelectedNode(node);
    });

    document.addEventListener("click", (event) => {
        const editable = closestEditable(event.target);
        const clickedInsideFloating = insideFloatingUi(event.target);
        if (clickedInsideFloating) {
            return;
        }
        if (editable) {
            setSelectedNode(editable);
            return;
        }
        hideEditor();
        hideMoveMenu();
        setSelectedNode(null);
    });

    window.addEventListener("scroll", () => {
        if (selectedNode && !toolbar.hidden) {
            placeFloatingElement(toolbar, selectedNode);
        }
        if (selectedNode && !editor.hidden) {
            placeFloatingElement(editor, selectedNode, 18);
        }
        if (selectedNode && !moveMenu.hidden) {
            placeFloatingElement(moveMenu, selectedNode, 18);
        }
    }, { passive: true });

    window.addEventListener("resize", () => {
        if (selectedNode) {
            setSelectedNode(selectedNode);
        }
    });
});
