document.addEventListener("DOMContentLoaded", () => {
    const roleTabsContainers = document.querySelectorAll("[data-role-tabs]");
    roleTabsContainers.forEach((container) => {
        const tabs = container.querySelectorAll(".role-tab");
        const roleInput = document.getElementById("id_role");
        tabs.forEach((tab) => {
            tab.addEventListener("click", () => {
                tabs.forEach((item) => item.classList.remove("active"));
                tab.classList.add("active");
                if (roleInput) {
                    roleInput.value = tab.dataset.roleValue || "customer";
                }
            });
        });
    });

    const toggles = document.querySelectorAll(".toggle-password");
    toggles.forEach((toggle) => {
        toggle.addEventListener("click", () => {
            const targetId = toggle.getAttribute("data-target");
            const input = targetId ? document.getElementById(targetId) : null;
            if (!input) {
                return;
            }
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            toggle.textContent = show ? "🙈" : "👁";
        });
    });

    const passwordInput = document.getElementById("id_password1");
    const strengthBar = document.getElementById("passwordStrength");
    const strengthText = document.getElementById("passwordStrengthText");
    if (passwordInput && strengthBar && strengthText) {
        const setStrength = (level, label) => {
            strengthBar.classList.remove("strength-weak", "strength-medium", "strength-strong");
            strengthBar.classList.add(level);
            strengthText.textContent = label;
        };

        passwordInput.addEventListener("keyup", () => {
            const value = passwordInput.value || "";
            const hasLetters = /[A-Za-z]/.test(value);
            const hasNumbers = /\d/.test(value);
            const hasSpecial = /[^A-Za-z0-9]/.test(value);

            if (value.length < 8) {
                setStrength("strength-weak", "Weak");
                return;
            }

            if (hasLetters && hasNumbers && hasSpecial) {
                setStrength("strength-strong", "Strong");
                return;
            }

            setStrength("strength-medium", "Medium");
        });
    }

    const flashMessages = document.querySelectorAll(".flash-message");
    flashMessages.forEach((message) => {
        setTimeout(() => {
            message.classList.add("fade-out");
        }, 4000);
    });

});
