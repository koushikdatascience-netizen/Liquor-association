/* =========================================================
   WBFL Association — Global App Behaviour
   (toast, mobile sidebar/nav toggle, FAQ accordion)
   ========================================================= */
(function(){
  "use strict";

  // ---------- Toast ----------
  function ensureToastHost(){
    let host = document.getElementById("toastHost");
    if(!host){
      host = document.createElement("div");
      host.id = "toastHost";
      host.className = "toast-host";
      host.setAttribute("aria-live","polite");
      host.setAttribute("aria-atomic","true");
      document.body.appendChild(host);
    }
    return host;
  }
  window.toast = function(msg, kind){
    const host = ensureToastHost();
    const el = document.createElement("div");
    el.className = "toast";
    const icon = kind === "warn" ? "exclamation-triangle" : "check-circle";
    el.innerHTML = '<i class="bi bi-' + icon + '" aria-hidden="true"></i> ' + msg;
    host.appendChild(el);
    setTimeout(function(){
      el.style.opacity = "0";
      el.style.transform = "translateY(-6px)";
      el.style.transition = "all 200ms ease";
      setTimeout(function(){ el.remove(); }, 220);
    }, 2400);
  };

  document.querySelectorAll(".django-messages .toast").forEach(function(el, index){
    const delay = 3200 + (index * 180);
    setTimeout(function(){
      el.style.opacity = "0";
      el.style.transform = "translateY(-6px)";
      el.style.transition = "opacity 200ms ease, transform 200ms ease";
      setTimeout(function(){
        el.remove();
        document.querySelectorAll(".django-messages").forEach(function(host){
          if(!host.querySelector(".toast")) host.remove();
        });
      }, 220);
    }, delay);
  });

  // ---------- Public nav mobile toggle ----------
  const navToggle = document.querySelector("[data-nav-toggle]");
  const mobileSheet = document.querySelector(".mobile-sheet");
  if(navToggle && mobileSheet){
    navToggle.addEventListener("click", function(){
      const open = mobileSheet.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }

  // ---------- Portal sidebar toggle (mobile) ----------
  const sidebar = document.querySelector(".sidebar");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const openBtn = document.querySelector("[data-sidebar-toggle]");
  const closeBtn = document.querySelector("[data-sidebar-close]");
  function openSidebar(){
    sidebar && sidebar.classList.add("open");
    backdrop && backdrop.classList.add("open");
  }
  function closeSidebar(){
    sidebar && sidebar.classList.remove("open");
    backdrop && backdrop.classList.remove("open");
  }
  openBtn && openBtn.addEventListener("click", openSidebar);
  closeBtn && closeBtn.addEventListener("click", closeSidebar);
  backdrop && backdrop.addEventListener("click", closeSidebar);

  function updateMobileToggle(){
    if(!openBtn) return;
    openBtn.style.display = window.innerWidth <= 960 ? "flex" : "none";
  }
  updateMobileToggle();
  window.addEventListener("resize", updateMobileToggle);

  // ---------- FAQ accordion ----------
  document.querySelectorAll("[data-faq] .faq-q").forEach(function(btn){
    btn.addEventListener("click", function(){
      const item = btn.closest(".faq-item");
      const isOpen = item.classList.contains("open");
      item.parentElement.querySelectorAll(".faq-item").forEach(function(i){ i.classList.remove("open"); });
      if(!isOpen) item.classList.add("open");
      item.querySelectorAll(".faq-q").forEach(function(q){ q.setAttribute("aria-expanded", String(!isOpen)); });
    });
  });

  // ---------- Optional demo-only form helpers ----------
  document.querySelectorAll("form").forEach(function(form){
    if(form.id === "contactForm"){
      form.addEventListener("submit", function(e){
        e.preventDefault();
        window.toast("Message sent — we will get back to you.");
        form.reset();
      });
    } else if(form.id === "loginForm"){
      form.addEventListener("submit", function(e){
        e.preventDefault();
        window.toast && window.toast("Please submit using the Django login form.");
      });
    } else if(form.id === "registerForm"){
      form.addEventListener("submit", function(e){
        e.preventDefault();
        const pwd = document.getElementById("regPassword");
        const confirm = document.getElementById("regConfirm");
        if(pwd && confirm && pwd.value !== confirm.value){
          window.toast("Passwords do not match", "warn");
          return;
        }
        window.toast && window.toast("Please submit using the Django registration form.");
      });
    } else if(form.id === "forgotForm"){
      form.addEventListener("submit", function(e){
        e.preventDefault();
        window.toast("Reset link sent to your email.");
      });
    }
  });

  // ---------- Copy link (membership card) ----------
  const copyBtn = document.getElementById("copyLink");
  if(copyBtn){
    copyBtn.addEventListener("click", async function(){
      const input = document.getElementById("verifyUrl");
      try{
        await navigator.clipboard.writeText(input.value);
        window.toast("Link copied");
      }catch(_){
        input.select();
        document.execCommand("copy");
        window.toast("Link copied");
      }
    });
  }

  // ---------- Fake download buttons (membership card) ----------
  const dlPng = document.getElementById("downloadPng");
  const dlPdf = document.getElementById("downloadPdf");
  dlPng && dlPng.addEventListener("click", function(){ window.toast("PNG downloaded"); });
  dlPdf && dlPdf.addEventListener("click", function(){ window.toast("PDF downloaded"); });

  // ---------- Profile tabs ----------
  document.querySelectorAll(".tab").forEach(function(tab){
    tab.addEventListener("click", function(){
      const target = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach(function(t){
        t.classList.toggle("active", t === tab);
        t.setAttribute("aria-selected", String(t === tab));
      });
      document.querySelectorAll(".tab-panel").forEach(function(p){
        p.hidden = p.dataset.panel !== target;
      });
    });
  });

  // ---------- Django membership application wizard ----------
  const applicationWizard = document.querySelector("[data-application-wizard]");
  if(applicationWizard){
    let currentStep = 1;
    const totalSteps = 6;
    const panels = Array.from(applicationWizard.querySelectorAll("[data-step-panel]"));
    const indicators = Array.from(document.querySelectorAll("[data-step-indicator]"));
    const prevBtn = applicationWizard.querySelector("[data-prev-step]");
    const nextBtn = applicationWizard.querySelector("[data-next-step]");
    const submitBtn = applicationWizard.querySelector("[data-submit-application]");
    const fieldLabels = {
      full_name: "Full name",
      nationality: "Nationality",
      age: "Age",
      gender: "Sex",
      whatsapp_number: "WhatsApp",
      email: "Email",
      residence_phone: "Telephone (residence)",
      residential_address: "Complete mailing address",
      pin_code: "PIN",
      entity_type: "Entity type",
      licence_category: "Category of licence",
      style_name: "Specific style name",
      excise_license_number: "Licence ID",
      office_phone: "Telephone (office)",
      shop_phone: "Telephone (shop / bar)",
      primary_delegate_name: "Primary representative",
      primary_delegate_designation: "Designation",
      alternate_delegate_name: "Alternate representative",
      alternate_delegate_role: "Relationship / Role"
    };

    function fieldValue(name){
      const field = applicationWizard.querySelector("[name='" + name + "']");
      if(!field) return "-";
      if(field.type === "file") return field.files && field.files[0] ? field.files[0].name : "Not selected";
      if(field.tagName === "SELECT") return field.options[field.selectedIndex]?.text || field.value || "-";
      return field.value || "-";
    }

    function refreshReview(){
      applicationWizard.querySelectorAll("[data-review-fields]").forEach(function(container){
        const fields = container.dataset.reviewFields.split(",");
        container.replaceChildren();
        fields.forEach(function(name){
          const item = document.createElement("div");
          const label = document.createElement("span");
          const value = document.createElement("b");
          label.textContent = fieldLabels[name] || name;
          value.textContent = fieldValue(name);
          item.append(label, value);
          container.appendChild(item);
        });
      });
    }

    function showStep(step){
      currentStep = Math.max(1, Math.min(totalSteps, step));
      panels.forEach(function(panel){
        const active = Number(panel.dataset.stepPanel) === currentStep;
        panel.hidden = !active;
        panel.classList.toggle("active", active);
      });
      indicators.forEach(function(indicator){
        const num = Number(indicator.dataset.stepIndicator);
        indicator.classList.toggle("active", num === currentStep);
        indicator.classList.toggle("done", num < currentStep);
        const stepNum = indicator.querySelector(".st-num");
        if(stepNum) stepNum.innerHTML = num < currentStep ? '<i class="bi bi-check" aria-hidden="true"></i>' : String(num);
      });
      if(prevBtn) prevBtn.disabled = currentStep === 1;
      if(nextBtn) nextBtn.hidden = currentStep === totalSteps;
      if(submitBtn) submitBtn.hidden = currentStep !== totalSteps;
      if(currentStep === totalSteps) refreshReview();
      applicationWizard.scrollIntoView({behavior:"smooth", block:"start"});
    }

    nextBtn && nextBtn.addEventListener("click", function(){ showStep(currentStep + 1); });
    prevBtn && prevBtn.addEventListener("click", function(){ showStep(currentStep - 1); });
    applicationWizard.querySelectorAll("[data-go-step]").forEach(function(btn){
      btn.addEventListener("click", function(){ showStep(Number(btn.dataset.goStep)); });
    });
    applicationWizard.querySelectorAll("input[type='file']").forEach(function(input){
      input.addEventListener("change", function(){
        const label = input.closest(".upload-drop")?.querySelector("[data-file-label]");
        if(label) label.textContent = input.files && input.files[0] ? input.files[0].name : "Drag & drop or click to upload";
      });
    });
    const errorPanel = panels.find(function(panel){ return panel.querySelector(".errorlist"); });
    showStep(errorPanel ? Number(errorPanel.dataset.stepPanel) : 1);
  }

  // ---------- Upload widgets (drag/drop + preview) ----------
  document.querySelectorAll(".upload").forEach(function(root){
    const input = root.querySelector('input[type="file"]');
    if(!input) return;
    const dropEl = root.querySelector(".upload-drop");
    const fileEl = root.querySelector(".upload-file");
    const nameEl = fileEl ? fileEl.querySelector(".name") : null;
    const sizeEl = fileEl ? fileEl.querySelector(".size") : null;
    const rmBtn = fileEl ? fileEl.querySelector(".rm") : null;

    root.addEventListener("click", function(e){
      if(rmBtn && (e.target === rmBtn || rmBtn.contains(e.target))) return;
      if(e.target === input) return;
      if(root.classList.contains("django-upload") && e.target.closest(".upload-drop")) return;
      input.click();
    });
    root.addEventListener("dragover", function(e){ e.preventDefault(); root.classList.add("is-drag"); });
    root.addEventListener("dragleave", function(){ root.classList.remove("is-drag"); });
    root.addEventListener("drop", function(e){
      e.preventDefault();
      root.classList.remove("is-drag");
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if(f){ input.files = e.dataTransfer.files; showFile(f); }
    });
    input.addEventListener("change", function(){
      const f = input.files && input.files[0];
      if(f) showFile(f);
    });
    rmBtn && rmBtn.addEventListener("click", function(e){
      e.stopPropagation();
      input.value = "";
      if(fileEl) fileEl.style.display = "none";
      if(dropEl) dropEl.style.display = "flex";
    });
    function showFile(f){
      if(f.size > 10 * 1024 * 1024){
        window.toast("Max file size is 10 MB", "warn");
        return;
      }
      if(nameEl) nameEl.textContent = f.name;
      if(sizeEl) sizeEl.textContent = (f.size/1024).toFixed(0) + " KB";
      if(fileEl) fileEl.style.display = "flex";
      if(dropEl) dropEl.style.display = "none";
    }
  });

  // ---------- Payment page: show "proceed to payment" demo toggle ----------
  const proceedPayment = document.getElementById("proceedPayment");
  if(proceedPayment){ /* controlled by backend in production */ }

})();



/* ---------- Admin Login Modal ---------- */
(function(){
  "use strict";
  const backdrop = document.getElementById("adminModalBackdrop");
  const openBtn = document.getElementById("adminLoginBtn");
  const openBtnMobile = document.getElementById("adminLoginBtnMobile");
  const closeBtn = document.getElementById("adminModalClose");
  const form = document.getElementById("adminLoginForm");

  if(!backdrop) return;

  function openModal(e){
    if(e) e.preventDefault();
    backdrop.classList.add("open");
    document.body.style.overflow = "hidden";
    const firstInput = backdrop.querySelector("input");
    firstInput && firstInput.focus();
  }
  function closeModal(){
    backdrop.classList.remove("open");
    document.body.style.overflow = "";
  }

  openBtn && openBtn.addEventListener("click", openModal);
  openBtnMobile && openBtnMobile.addEventListener("click", openModal);
  closeBtn && closeBtn.addEventListener("click", closeModal);
  backdrop.addEventListener("click", function(e){
    if(e.target === backdrop) closeModal();
  });
  document.addEventListener("keydown", function(e){
    if(e.key === "Escape" && backdrop.classList.contains("open")) closeModal();
  });

  form && form.addEventListener("submit", function(e){
    e.preventDefault();
    window.location.href = "/admin/";
  });
})();
