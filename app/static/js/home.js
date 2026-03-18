const form = document.getElementById("generate-form");

if (form) {
    const generateBtn = document.getElementById("generate-btn");
    const statusText = document.getElementById("status-text");

    const goalInput = document.getElementById("goal-input");
    const audienceInput = document.getElementById("audience-input");
    const toneInput = document.getElementById("tone-input");
    const densityInput = document.getElementById("density-input");
    const motionInput = document.getElementById("motion-input");
    const nameInput = document.getElementById("name-input");
    const notesInput = document.getElementById("notes-input");

    function setBusy(isBusy, message) {
        generateBtn.disabled = isBusy;
        generateBtn.classList.toggle("btn-disabled", isBusy);
        generateBtn.textContent = isBusy ? "Building Studio..." : "Generate Studio";
        statusText.textContent = message || "";
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

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const brief = {
            goal: goalInput.value.trim(),
            audience: audienceInput.value.trim(),
            brand_tone: toneInput.value.trim(),
            content_density: densityInput.value,
            motion_level: motionInput.value,
            name: nameInput.value.trim(),
            notes: notesInput.value.trim(),
        };
        if (!brief.goal || !brief.audience || !brief.brand_tone) {
            setBusy(false, "Goal, audience, and brand tone are required.");
            return;
        }

        setBusy(true, "Generating variants, layouts, and copy...");
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
            window.location.href = data.preview_url;
        } catch (error) {
            setBusy(false, error.message || "Something went wrong.");
        }
    });
}
