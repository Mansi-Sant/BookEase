document.addEventListener("DOMContentLoaded", () => {
    const byId = (id) => document.getElementById(id);

    document.querySelectorAll(".type-card").forEach((card) => {
        card.addEventListener("click", () => {
            document.querySelectorAll(".type-card").forEach((c) => c.classList.remove("selected"));
            card.classList.add("selected");
            const value = card.dataset.value;
            const input = document.querySelector(`input[name="appointment_type"][value="${value}"]`);
            if (input) input.checked = true;
        });
    });

    const addResourceBtn = byId("addResourceRow");
    if (addResourceBtn) {
        addResourceBtn.addEventListener("click", () => addResourceRow());
    }
    window.removeResourceRow = (btn) => {
        const container = byId("resourceRows");
        if (!container) return;
        const rows = container.querySelectorAll(".dynamic-row");
        if (rows.length <= 1 && container.dataset.requireOne === "true") return;
        btn.closest(".dynamic-row")?.remove();
    };
    window.addResourceRow = () => {
        const tpl = byId("resourceRowTemplate");
        const container = byId("resourceRows");
        if (!tpl || !container) return;
        const clone = tpl.content.cloneNode(true);
        container.appendChild(clone);
    };

    document.querySelectorAll(".day-enable").forEach((checkbox) => {
        const row = checkbox.closest(".hours-row");
        const inputs = row ? row.querySelectorAll(".time-input") : [];
        const sync = () => {
            const enabled = checkbox.checked;
            if (row) row.classList.toggle("disabled", !enabled);
            inputs.forEach((i) => {
                i.disabled = !enabled;
            });
        };
        checkbox.addEventListener("change", sync);
        sync();
    });

    const applyAll = byId("applyAllDays");
    if (applyAll) {
        applyAll.addEventListener("change", () => {
            if (!applyAll.checked) return;
            const firstEnabled = document.querySelector(".hours-row .day-enable:checked");
            if (!firstEnabled) return;
            const row = firstEnabled.closest(".hours-row");
            if (!row) return;
            const start = row.querySelector('input[name^="start_time_"]')?.value || "";
            const end = row.querySelector('input[name^="end_time_"]')?.value || "";
            document.querySelectorAll(".hours-row .day-enable:checked").forEach((cb) => {
                const r = cb.closest(".hours-row");
                if (!r) return;
                const s = r.querySelector('input[name^="start_time_"]');
                const e = r.querySelector('input[name^="end_time_"]');
                if (s) s.value = start;
                if (e) e.value = end;
            });
        });
    }

    const weeklyTab = byId("weeklyTab");
    const flexibleTab = byId("flexibleTab");
    const weeklyWrap = byId("weeklyWrap");
    const flexibleWrap = byId("flexibleWrap");
    const scheduleMode = byId("scheduleMode");
    const syncTabs = (mode) => {
        if (scheduleMode) scheduleMode.value = mode;
        if (weeklyTab) weeklyTab.classList.toggle("active", mode === "weekly");
        if (flexibleTab) flexibleTab.classList.toggle("active", mode === "flexible");
        if (weeklyWrap) weeklyWrap.classList.toggle("hidden", mode !== "weekly");
        if (flexibleWrap) flexibleWrap.classList.toggle("hidden", mode !== "flexible");
    };
    if (weeklyTab) weeklyTab.addEventListener("click", () => syncTabs("weekly"));
    if (flexibleTab) flexibleTab.addEventListener("click", () => syncTabs("flexible"));
    if (scheduleMode) syncTabs(scheduleMode.value || "weekly");

    window.addSlotRow = (type) => {
        const tpl = byId(type === "weekly" ? "weeklySlotRowTemplate" : "flexSlotRowTemplate");
        const container = byId(type === "weekly" ? "weeklyRows" : "flexRows");
        if (!tpl || !container) return;
        container.appendChild(tpl.content.cloneNode(true));
    };
    window.removeSlotRow = (btn) => btn.closest(".dynamic-row")?.remove();

    window.addQuestionRow = () => {
        const tpl = byId("questionRowTemplate");
        const container = byId("questionRows");
        if (!tpl || !container) return;
        container.appendChild(tpl.content.cloneNode(true));
    };
    window.removeQuestionRow = (btn) => btn.closest(".dynamic-row")?.remove();

    const durationSelect = byId("durationSelect");
    const customDurationWrap = byId("customDurationWrap");
    const customDurationInput = byId("customDurationInput");
    const syncDuration = () => {
        if (!durationSelect || !customDurationWrap) return;
        const isCustom = durationSelect.value === "custom";
        customDurationWrap.classList.toggle("hidden", !isCustom);
        if (customDurationInput) customDurationInput.required = isCustom;
    };
    if (durationSelect) {
        durationSelect.addEventListener("change", syncDuration);
        syncDuration();
    }

    const form = document.querySelector(".wizard-form");
    if (form) {
        form.addEventListener("submit", (e) => {
            document.querySelectorAll("#questionRows .dynamic-row").forEach((row, index) => {
                const checkbox = row.querySelector("input[type='checkbox']");
                if (checkbox) checkbox.name = `question_required_${index}`;
            });

            const required = form.querySelectorAll("[data-required='true']");
            let ok = true;
            required.forEach((el) => {
                const error = el.parentElement?.querySelector(".field-error-inline");
                if (!String(el.value || "").trim()) {
                    ok = false;
                    el.classList.add("input-error");
                    if (error) error.textContent = "This field is required.";
                } else {
                    el.classList.remove("input-error");
                    if (error) error.textContent = "";
                }
            });

            const typeCards = document.querySelectorAll(".type-card");
            if (typeCards.length) {
                const checked = form.querySelector('input[name="appointment_type"]:checked');
                const typeError = byId("typeSelectionError");
                if (!checked) {
                    ok = false;
                    if (typeError) typeError.textContent = "Please select an appointment type.";
                } else if (typeError) {
                    typeError.textContent = "";
                }
            }

            if (!ok) e.preventDefault();
        });
    }
});
