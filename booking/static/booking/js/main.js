/**
 * Vanilla JS for BookEase — no external libraries.
 * Booking slot refresh uses a plain Django POST (see #refresh-slots-form).
 */
(function () {
  "use strict";

  document.documentElement.classList.add("js-ready");

  /* Mobile nav */
  var toggle = document.querySelector("[data-nav-toggle]");
  var navLinks = document.querySelector("[data-nav-links]");
  var sidebar = document.querySelector("[data-sidebar]");
  var sidebarOpen = document.querySelector("[data-sidebar-open]");

  function closeMenus() {
    if (navLinks) navLinks.classList.remove("is-open");
    if (sidebar) sidebar.classList.remove("is-open");
  }

  if (toggle && navLinks) {
    toggle.addEventListener("click", function () {
      navLinks.classList.toggle("is-open");
    });
  }
  if (sidebarOpen && sidebar) {
    sidebarOpen.addEventListener("click", function () {
      sidebar.classList.toggle("is-open");
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeMenus();
  });

  /* Auto-dismiss Django messages (~3s) */
  var flashRoot = document.getElementById("flash-messages");
  if (flashRoot) {
    setTimeout(function () {
      flashRoot.style.opacity = "0";
      flashRoot.style.transform = "translateX(12px)";
      flashRoot.style.transition = "opacity 0.35s, transform 0.35s";
      setTimeout(function () {
        flashRoot.remove();
      }, 400);
    }, 3000);
  }

  /* Cancel appointment confirm */
  document.querySelectorAll("[data-confirm-cancel]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm("Cancel this appointment? The time slot will be released.")) {
        e.preventDefault();
      }
    });
  });

  /* Booking wizard */
  var bookRoot = document.getElementById("booking-wizard");
  if (!bookRoot) return;

  var step1 = document.getElementById("booking-step-1");
  var step2 = document.getElementById("booking-step-2");
  var refreshForm = document.getElementById("refresh-slots-form");
  var refreshServiceInput = document.getElementById("refresh-service-id");
  var mainForm = document.getElementById("booking-main-form");
  var hiddenService = document.getElementById("id_service");
  var hiddenTimeslot = document.getElementById("id_timeslot");
  var notesEl = bookRoot.querySelector("[data-notes]");
  var btnProceed = document.getElementById("btn-proceed-booking");
  var btnBack = document.getElementById("btn-back-booking");

  var summaryEls = {
    service: document.getElementById("summary-service"),
    date: document.getElementById("summary-date"),
    time: document.getElementById("summary-time"),
    duration: document.getElementById("summary-duration"),
    price: document.getElementById("summary-price"),
    user: document.getElementById("summary-user"),
    notes: document.getElementById("summary-notes"),
  };

  function hideStep(el) {
    if (!el) return;
    el.classList.add("is-hidden");
  }
  function showStep(el) {
    if (!el) return;
    el.classList.remove("is-hidden");
  }

  function selectServiceCard(card) {
    document.querySelectorAll(".service-card").forEach(function (c) {
      c.classList.remove("is-selected");
    });
    card.classList.add("is-selected");
    var sid = card.getAttribute("data-service-id");
    if (hiddenService) hiddenService.value = sid;
  }

  document.querySelectorAll(".service-card").forEach(function (card) {
    card.addEventListener("click", function () {
      selectServiceCard(card);
      if (refreshForm && refreshServiceInput) {
        refreshServiceInput.value = card.getAttribute("data-service-id");
        refreshForm.submit();
      }
    });
  });

  document.querySelectorAll(".slot-pill:not(:disabled)").forEach(function (pill) {
    pill.addEventListener("click", function () {
      document.querySelectorAll(".slot-pill").forEach(function (p) {
        p.classList.remove("is-selected");
      });
      pill.classList.add("is-selected");
      if (hiddenTimeslot) {
        hiddenTimeslot.value = pill.getAttribute("data-slot-id");
      }
    });
  });

  /* Calendar day → highlight matching timeslots (click again to clear) */
  var calFilterIso = null;
  document.querySelectorAll(".cal-day[data-date-iso]").forEach(function (cell) {
    cell.addEventListener("click", function () {
      if (cell.classList.contains("cal-day--past")) return;
      var iso = cell.getAttribute("data-date-iso");
      if (!iso) return;
      if (calFilterIso === iso) {
        calFilterIso = null;
        document.querySelectorAll(".cal-day").forEach(function (c) {
          c.classList.remove("is-selected");
        });
        document.querySelectorAll(".slot-pill").forEach(function (p) {
          p.classList.remove("slot-pill--dim");
        });
        return;
      }
      calFilterIso = iso;
      document.querySelectorAll(".cal-day").forEach(function (c) {
        c.classList.remove("is-selected");
      });
      cell.classList.add("is-selected");
      document.querySelectorAll(".slot-pill").forEach(function (p) {
        var d = p.getAttribute("data-date-iso");
        p.classList.toggle("slot-pill--dim", d !== iso);
      });
    });
  });

  if (btnProceed) {
    btnProceed.addEventListener("click", function () {
      var sVal = hiddenService && hiddenService.value;
      var tVal = hiddenTimeslot && hiddenTimeslot.value;
      if (!sVal) {
        window.alert("Please choose a service.");
        return;
      }
      if (!tVal) {
        window.alert("Please choose an available time slot.");
        return;
      }
      var selectedCard = document.querySelector(".service-card.is-selected");
      if (selectedCard && summaryEls.service) {
        summaryEls.service.textContent = selectedCard.getAttribute("data-service-name") || "—";
        var dur = selectedCard.getAttribute("data-duration");
        if (summaryEls.duration) summaryEls.duration.textContent = dur ? dur + " min" : "—";
        var price = selectedCard.getAttribute("data-price");
        if (summaryEls.price) {
          summaryEls.price.textContent = price ? "₹" + price : "—";
        }
      }
      var pill = document.querySelector(".slot-pill.is-selected");
      if (pill) {
        if (summaryEls.date) summaryEls.date.textContent = pill.getAttribute("data-date") || "—";
        if (summaryEls.time) summaryEls.time.textContent = pill.getAttribute("data-time") || "—";
      }
      if (summaryEls.notes && notesEl) {
        summaryEls.notes.textContent = notesEl.value.trim() || "—";
      }
      hideStep(step1);
      showStep(step2);
    });
  }

  if (btnBack) {
    btnBack.addEventListener("click", function (e) {
      e.preventDefault();
      hideStep(step2);
      showStep(step1);
    });
  }
})();
