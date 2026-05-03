document.addEventListener("DOMContentLoaded", () => {
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    }

    const getCsrfToken = () => {
        const row = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="));
        return row ? row.split("=")[1] : "";
    };

    document.querySelectorAll(".publish-toggle-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const url = btn.dataset.toggleUrl;
            if (!url) return;
            try {
                const res = await fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });
                const data = await res.json();
                if (!res.ok || !data.ok) throw new Error("toggle failed");
                btn.textContent = data.button_label;
                const badge = btn.closest(".card")?.querySelector("[data-status-badge]");
                if (badge) {
                    badge.textContent = data.status_label;
                    badge.classList.toggle("badge-published", data.is_published);
                    badge.classList.toggle("badge-draft", !data.is_published);
                }
            } catch (err) {
                alert("Unable to toggle publish status.");
            }
        });
    });

    document.querySelectorAll(".copy-share-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const url = btn.dataset.shareUrl;
            if (!url) return;
            try {
                const res = await fetch(url);
                const data = await res.json();
                if (!data.share_link) {
                    alert(data.message || "Share link unavailable for published service.");
                    return;
                }
                await navigator.clipboard.writeText(data.share_link);
                btn.textContent = "Copied!";
                setTimeout(() => (btn.textContent = "Share Link"), 1500);
            } catch (err) {
                alert("Failed to copy link.");
            }
        });
    });

    document.querySelectorAll(".day-enabled").forEach((checkbox) => {
        const row = checkbox.closest("tr");
        if (!row) return;
        const timeInputs = row.querySelectorAll(".day-time-input");
        const syncState = () => {
            timeInputs.forEach((input) => {
                input.disabled = !checkbox.checked;
            });
        };
        checkbox.addEventListener("change", syncState);
        syncState();
    });

    document.querySelectorAll(".table-clickable tbody tr[data-href]").forEach((row) => {
        row.addEventListener("click", () => {
            window.location.href = row.dataset.href;
        });
    });

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const required = form.querySelectorAll("[required]");
            let ok = true;
            required.forEach((input) => {
                if (!input.value.trim()) {
                    input.classList.add("input-error");
                    ok = false;
                } else {
                    input.classList.remove("input-error");
                }
            });
            if (!ok) {
                event.preventDefault();
                alert("Please complete required fields.");
            }
        });
    });
});
