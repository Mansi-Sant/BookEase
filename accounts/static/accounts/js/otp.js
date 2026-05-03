document.addEventListener("DOMContentLoaded", () => {
    const otpForm = document.getElementById("otp-form");
    const boxes = Array.from(document.querySelectorAll(".otp-box"));
    const hiddenOtpInput = document.getElementById("id_otp_code");
    const clientError = document.getElementById("otpClientError");
    const countdownEl = document.getElementById("otpCountdown");
    const verifyBtn = document.getElementById("verifyOtpBtn");
    const resendBtn = document.getElementById("resendOtpBtn");
    const resendForm = document.getElementById("resendForm");
    const inlineMessage = document.getElementById("otpInlineMessage");

    const csrfTokenInput = resendForm
        ? resendForm.querySelector('input[name="csrfmiddlewaretoken"]')
        : null;
    const csrfToken = csrfTokenInput ? csrfTokenInput.value : "";

    const flashMessages = document.querySelectorAll(".flash-message");
    flashMessages.forEach((message) => {
        setTimeout(() => {
            message.classList.add("fade-out");
        }, 4000);
    });

    const showInlineMessage = (text, type) => {
        if (!inlineMessage) {
            return;
        }
        const klass = type === "success" ? "otp-inline-success" : "otp-inline-error";
        inlineMessage.innerHTML = `<div class="${klass}">${text}</div>`;
        setTimeout(() => {
            inlineMessage.innerHTML = "";
        }, 4000);
    };

    if (boxes.length > 0) {
        boxes[0].focus();
    }

    boxes.forEach((box, index) => {
        box.addEventListener("input", () => {
            box.value = (box.value || "").replace(/\D/g, "").slice(0, 1);
            if (box.value) {
                box.classList.add("filled");
                if (index < boxes.length - 1) {
                    boxes[index + 1].focus();
                }
            } else {
                box.classList.remove("filled");
            }
        });

        box.addEventListener("keydown", (event) => {
            if (event.key === "Backspace" && !box.value && index > 0) {
                boxes[index - 1].focus();
            }
        });
    });

    if (boxes[0]) {
        boxes[0].addEventListener("paste", (event) => {
            event.preventDefault();
            const pasted = (event.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, 6);
            if (!pasted) {
                return;
            }
            boxes.forEach((b) => {
                b.value = "";
                b.classList.remove("filled");
            });
            pasted.split("").forEach((char, i) => {
                if (boxes[i]) {
                    boxes[i].value = char;
                    boxes[i].classList.add("filled");
                }
            });
            const lastFilled = Math.min(pasted.length - 1, boxes.length - 1);
            if (lastFilled >= 0) {
                boxes[lastFilled].focus();
            }
        });
    }

    if (otpForm) {
        otpForm.addEventListener("submit", (event) => {
            const code = boxes.map((b) => b.value).join("");
            if (hiddenOtpInput) {
                hiddenOtpInput.value = code;
            }
            if (code.length !== 6) {
                event.preventDefault();
                if (clientError) {
                    clientError.textContent = "Please enter all 6 digits";
                }
                return;
            }
            if (clientError) {
                clientError.textContent = "";
            }
        });
    }

    let seconds = 600;
    const formatTime = (total) => {
        const mm = String(Math.floor(total / 60)).padStart(2, "0");
        const ss = String(total % 60).padStart(2, "0");
        return `${mm}:${ss}`;
    };

    if (countdownEl) {
        countdownEl.textContent = formatTime(seconds);
        const timer = setInterval(() => {
            seconds -= 1;
            if (seconds <= 0) {
                clearInterval(timer);
                countdownEl.textContent = "00:00";
                if (verifyBtn) {
                    verifyBtn.disabled = true;
                }
                showInlineMessage("OTP expired.", "error");
                return;
            }
            countdownEl.textContent = formatTime(seconds);
        }, 1000);
    }

    let resendCooldown = 30;
    const setResendState = () => {
        if (!resendBtn) {
            return;
        }
        if (resendCooldown > 0) {
            resendBtn.disabled = true;
            resendBtn.textContent = `Resend in ${resendCooldown}s`;
        } else {
            resendBtn.disabled = false;
            resendBtn.textContent = "Resend OTP";
        }
    };

    setResendState();
    const resendCooldownTimer = setInterval(() => {
        resendCooldown -= 1;
        setResendState();
        if (resendCooldown <= 0) {
            clearInterval(resendCooldownTimer);
        }
    }, 1000);

    if (resendForm) {
        resendForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!resendBtn || resendBtn.disabled) {
                return;
            }
            try {
                const response = await fetch("/accounts/otp/resend/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });
                const data = await response.json();
                if (!response.ok || !data.ok) {
                    showInlineMessage(data.message || "Failed to resend OTP.", "error");
                    return;
                }
                showInlineMessage("OTP resent successfully", "success");
                resendCooldown = 30;
                setResendState();
                const cooldown = setInterval(() => {
                    resendCooldown -= 1;
                    setResendState();
                    if (resendCooldown <= 0) {
                        clearInterval(cooldown);
                    }
                }, 1000);
            } catch (error) {
                showInlineMessage("Failed to resend OTP.", "error");
            }
        });
    }
});
