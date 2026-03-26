const onboardingForm = document.querySelector("[data-onboarding-form]");

if (onboardingForm) {
    const step = Number(onboardingForm.dataset.step || "0");
    const nextArrow = onboardingForm.querySelector("[data-next-arrow]");

    if ((step === 1 || step === 2) && nextArrow) {
        const radioInputs = Array.from(onboardingForm.querySelectorAll(".onboarding-choice-input"));

        const syncNextArrow = () => {
            const hasSelection = radioInputs.some((input) => input.checked);
            nextArrow.disabled = !hasSelection;
        };

        radioInputs.forEach((input) => {
            input.addEventListener("change", syncNextArrow);
        });

        syncNextArrow();
    }
}
