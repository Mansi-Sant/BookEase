document.addEventListener("DOMContentLoaded", () => {
    let currentStep = 1;
    const stepSections = Array.from(document.querySelectorAll(".step-section"));
    const indicators = Array.from(document.querySelectorAll("[data-step-indicator]"));

    const showStep = (n) => {
        currentStep = n;
        stepSections.forEach((sec) => sec.classList.toggle("hidden", Number(sec.dataset.step) !== n));
        indicators.forEach((item) => {
            const idx = Number(item.dataset.stepIndicator);
            item.classList.toggle("active", idx === n);
            item.classList.toggle("completed", idx < n);
        });
    };

    if (stepSections.length) showStep(1);

    const slotInput = document.getElementById("selected_slot");
    const slotSummary = document.getElementById("selectedSlotSummary");
    const slotError = document.getElementById("slotError");
    document.querySelectorAll(".slot-card[data-slot-id]").forEach((card) => {
        card.addEventListener("click", () => {
            document.querySelectorAll(".slot-card[data-slot-id]").forEach((c) => c.classList.remove("selected"));
            card.classList.add("selected");
            if (slotInput) slotInput.value = card.dataset.slotId;
            if (slotSummary) slotSummary.textContent = card.dataset.slotLabel || "-";
            if (slotError) slotError.textContent = "";
        });
    });

    const next1 = document.getElementById("nextStep1");
    const next2 = document.getElementById("nextStep2");
    const back2 = document.getElementById("backStep2");
    const back3 = document.getElementById("backStep3");
    const step2 = document.querySelector('.step-section[data-step="2"]');

    if (next1) {
        next1.addEventListener("click", () => {
            if (slotInput && !slotInput.value) {
                if (slotError) slotError.textContent = "Please select a slot.";
                return;
            }
            const hasQuestions = step2?.dataset.hasQuestions === "1";
            showStep(hasQuestions ? 2 : 3);
        });
    }
    if (next2) next2.addEventListener("click", () => showStep(3));
    if (back2) back2.addEventListener("click", () => showStep(1));
    if (back3) back3.addEventListener("click", () => showStep(2));

    const picInput = document.querySelector('input[type="file"][name="profile_picture"]');
    const avatarPreview = document.getElementById("avatarPreview");
    if (picInput && avatarPreview) {
        picInput.addEventListener("change", () => {
            const file = picInput.files?.[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => {
                if (avatarPreview.tagName === "IMG") {
                    avatarPreview.src = reader.result;
                }
            };
            reader.readAsDataURL(file);
        });
    }

    document.querySelectorAll(".tab-btn[data-tab-target]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tabTarget;
            const container = btn.closest("section, article, .card, .section") || document;
            container.querySelectorAll(".tab-btn[data-tab-target]").forEach((b) => b.classList.remove("active"));
            container.querySelectorAll(".tab-section").forEach((sec) => sec.classList.add("hidden"));
            btn.classList.add("active");
            const targetEl = document.getElementById(target);
            if (targetEl) targetEl.classList.remove("hidden");
        });
    });

    document.querySelectorAll(".cancel-toggle-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const box = btn.closest(".booking-card, .booking-sidebar, .card")?.querySelector(".inline-confirm");
            if (box) box.classList.toggle("visible");
        });
    });
    document.querySelectorAll(".keep-booking-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const box = btn.closest(".inline-confirm");
            if (box) box.classList.remove("visible");
        });
    });

    const avatarBtn = document.getElementById("avatarBtn");
    const avatarDropdown = document.getElementById("avatarDropdown");
    if (avatarBtn && avatarDropdown) {
        avatarBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            avatarDropdown.classList.toggle("open");
        });
        document.addEventListener("click", (e) => {
            if (!avatarDropdown.contains(e.target) && e.target !== avatarBtn) {
                avatarDropdown.classList.remove("open");
            }
        });
    }

    const navHamburger = document.getElementById("navHamburger");
    const navLinks = document.getElementById("navLinks");
    if (navHamburger && navLinks) {
        navHamburger.addEventListener("click", () => navLinks.classList.toggle("open"));
    }

    document.querySelectorAll(".flash").forEach((msg) => {
        setTimeout(() => {
            msg.classList.add("fade-out");
            setTimeout(() => msg.remove(), 350);
        }, 4000);
    });

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (e) => {
            let valid = true;
            form.querySelectorAll("[required]").forEach((input) => {
                const hasValue = (input.value || "").trim().length > 0;
                if (!hasValue) {
                    valid = false;
                    input.classList.add("input-error");
                    const err = input.parentElement?.querySelector(".field-error");
                    if (err) err.textContent = "This field is required.";
                }
                input.addEventListener("focus", () => {
                    input.classList.remove("input-error");
                    const err = input.parentElement?.querySelector(".field-error");
                    if (err) err.textContent = "";
                });
            });
            if (!valid) e.preventDefault();
        });
    });
});
