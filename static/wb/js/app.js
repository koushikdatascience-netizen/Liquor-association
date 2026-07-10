/* =========================================================
   WBFL Association — Global App Behaviour
   (toast, mobile sidebar/nav toggle, FAQ accordion)
   ========================================================= */
(function(){
  "use strict";

  // ---------- Client-side validators (used by the application wizard) ----------
  window.WBFLValidators = {
    isValidEmail: function(v){
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v).trim());
    },
    isValidPhone: function(v){
      const s = String(v).trim();
      const digits = s.replace(/[^\d]/g, "");
      return /^[+\d][\d\s-]{6,}$/.test(s) && digits.length >= 10 && digits.length <= 15;
    },
    isValidPin: function(v){
      return /^\d{6}$/.test(String(v).trim());
    }
  };

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
    const submitLabel = nextBtn ? nextBtn.dataset.submitLabel : "Submit Application";
    const documentRequired = applicationWizard.dataset.documentRequired !== "false";
    const documentFields = [
      "excise_license",
      "primary_delegate_photo",
      "alternate_delegate_photo",
      "passport_photo",
      "pan_card",
      "aadhaar_card",
      "partnership_deed",
      "gst_certificate",
      "address_proof"
    ];
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

    const DRAFT_KEY = "wbfl_application_draft";
    function collectDraft(){
      const data = {};
      applicationWizard.querySelectorAll("input, select, textarea").forEach(function(el){
        if(el.type === "file") return;
        if(el.type === "checkbox"){ data[el.name || el.id] = el.checked; }
        else if(el.name || el.id){ data[el.name || el.id] = el.value; }
      });
      return data;
    }
    let persistTimer = null;
    function persistDraft(){
      try{
        const existing = JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}");
        const merged = Object.assign(existing, collectDraft());
        localStorage.setItem(DRAFT_KEY, JSON.stringify(merged));
      }catch(_){}
    }
    function schedulePersist(){
      if(persistTimer) clearTimeout(persistTimer);
      persistTimer = setTimeout(persistDraft, 600);
    }
    function restoreDraft(){
      try{
        const raw = localStorage.getItem(DRAFT_KEY);
        if(!raw) return;
        const data = JSON.parse(raw);
        applicationWizard.querySelectorAll("input, select, textarea").forEach(function(el){
          if(el.type === "file") return;
          const key = el.name || el.id;
          if(!(key in data)) return;
          if(el.type === "checkbox"){ el.checked = !!data[key]; }
          else { el.value = data[key]; }
        });
      }catch(_){}
    }

    function fieldLabel(field){
      const name = field.name;
      if(fieldLabels[name]) return fieldLabels[name];
      const label = applicationWizard.querySelector("label[for='" + field.id + "']");
      return label ? label.textContent.replace("*", "").trim() : "This field";
    }

    function fieldShell(field){
      return field.closest(".field") || field.closest(".upload") || field.closest(".checkbox") || field.parentElement;
    }

    function clearFieldError(field){
      const shell = fieldShell(field);
      field.classList && field.classList.remove("is-error");
      field.removeAttribute("aria-invalid");
      if(shell) shell.classList.remove("has-error");
      const id = field.id ? field.id + "-client-error" : "";
      const existing = id ? document.getElementById(id) : shell?.querySelector("[data-client-error]");
      if(existing) existing.remove();
      field.removeAttribute("aria-describedby");
    }

    function setFieldError(field, message){
      const shell = fieldShell(field);
      if(!shell) return;
      clearFieldError(field);
      field.classList && field.classList.add("is-error");
      field.setAttribute("aria-invalid", "true");
      shell.classList.add("has-error");
      const error = document.createElement("div");
      error.className = "field-error";
      error.dataset.clientError = "true";
      if(field.id) error.id = field.id + "-client-error";
      error.textContent = message;
      if(field.type === "checkbox"){
        shell.insertAdjacentElement("afterend", error);
      }else if(field.closest(".upload")){
        shell.appendChild(error);
      }else{
        shell.appendChild(error);
      }
      if(error.id) field.setAttribute("aria-describedby", error.id);
    }

    function isEmptyField(field){
      if(field.type === "checkbox") return !field.checked;
      if(field.type === "file") return !field.files || !field.files.length;
      return !String(field.value || "").trim();
    }

    function validateField(field){
      if(field.disabled || field.type === "hidden" || field.type === "button" || field.type === "submit") return true;
      clearFieldError(field);
      if(field.required && isEmptyField(field)){
        const message = field.type === "checkbox" ? "Please confirm this declaration." : fieldLabel(field) + " is required.";
        setFieldError(field, message);
        return false;
      }
      if(field.type === "file" && field.files && field.files[0]){
        const file = field.files[0];
        const accept = field.getAttribute("accept") || "";
        const acceptedTypes = accept.split(",").map(function(type){ return type.trim(); }).filter(Boolean);
        const isAccepted = !acceptedTypes.length || acceptedTypes.some(function(type){
          return type.endsWith("/*") ? file.type.indexOf(type.slice(0, -1)) === 0 : file.type === type;
        });
        if(!isAccepted){
          setFieldError(field, accept.indexOf("application/pdf") >= 0 ? "Upload a PDF, JPG, PNG or WebP file." : "Upload a JPG, PNG or WebP image.");
          return false;
        }
      }
      if(field.value){
        if(field.type === "email" && window.WBFLValidators && !window.WBFLValidators.isValidEmail(field.value)){
          setFieldError(field, "Enter a valid email address.");
          return false;
        }
        if(field.name === "pin_code" && window.WBFLValidators && !window.WBFLValidators.isValidPin(field.value)){
          setFieldError(field, "PIN code must be 6 digits.");
          return false;
        }
        if((field.name === "whatsapp_number" || field.name === "residence_phone" || field.name === "office_phone" || field.name === "shop_phone") && window.WBFLValidators && !window.WBFLValidators.isValidPhone(field.value)){
          setFieldError(field, "Enter a valid phone number.");
          return false;
        }
      }
      return true;
    }

    function validateDocuments(panel){
      if(Number(panel.dataset.stepPanel) !== 4 || !documentRequired) return true;
      const hasDocument = documentFields.some(function(name){
        const field = applicationWizard.querySelector("[name='" + name + "']");
        return field && field.files && field.files.length;
      });
      if(hasDocument) return true;
      const firstUpload = panel.querySelector("[name='excise_license']") || panel.querySelector("input[type='file']");
      if(firstUpload) setFieldError(firstUpload, "Upload at least one application document.");
      return false;
    }

    function validateStep(step){
      const panel = panels.find(function(item){ return Number(item.dataset.stepPanel) === step; });
      if(!panel) return true;
      const fields = Array.from(panel.querySelectorAll("input, select, textarea"));
      let valid = true;
      fields.forEach(function(field){
        if(!validateField(field)) valid = false;
      });
      if(!validateDocuments(panel)) valid = false;
      if(!valid){
        if(!panel.hidden){
          const firstInvalid = panel.querySelector(".is-error, .has-error input, .has-error select, .has-error textarea");
          firstInvalid && firstInvalid.focus({preventScroll:true});
          panel.scrollIntoView({behavior:"smooth", block:"start"});
        }
      }
      return valid;
    }

    function validateAllSteps(){
      for(let step = 1; step <= totalSteps; step += 1){
        if(!validateStep(step)){
          showStep(step);
          window.setTimeout(function(){
            const panel = panels.find(function(item){ return Number(item.dataset.stepPanel) === step; });
            const firstInvalid = panel?.querySelector(".is-error, .has-error input, .has-error select, .has-error textarea");
            firstInvalid && firstInvalid.focus({preventScroll:true});
          }, 0);
          return false;
        }
      }
      return true;
    }

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
      if(nextBtn){
        nextBtn.innerHTML = currentStep === totalSteps
          ? submitLabel + ' <i class="bi bi-check2-circle" aria-hidden="true"></i>'
          : 'Next <i class="bi bi-arrow-right" aria-hidden="true"></i>';
      }
      if(currentStep === totalSteps) refreshReview();
      applicationWizard.scrollIntoView({behavior:"smooth", block:"start"});
    }

    nextBtn && nextBtn.addEventListener("click", function(){
      if(currentStep === totalSteps){
        applicationWizard.requestSubmit();
        return;
      }
      if(validateStep(currentStep)) showStep(currentStep + 1);
    });
    prevBtn && prevBtn.addEventListener("click", function(){ showStep(currentStep - 1); });
    const saveDraftBtn = applicationWizard.querySelector("[data-save-draft]");
    saveDraftBtn && saveDraftBtn.addEventListener("click", function(){
      persistDraft();
      const fd = new FormData(applicationWizard);
      fd.set("save_draft", "1");
      saveDraftBtn.disabled = true;
      saveDraftBtn.innerHTML = '<i class="bi bi-arrow-repeat" style="animation:spin 1s linear infinite" aria-hidden="true"></i> Saving...';
      fetch(window.location.pathname, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: fd })
        .then(function(){ window.toast("Draft saved"); })
        .catch(function(){ window.toast("Draft saved on this device", "warn"); })
        .finally(function(){
          saveDraftBtn.disabled = false;
          saveDraftBtn.innerHTML = "Save draft";
        });
    });
    applicationWizard.querySelectorAll("[data-go-step]").forEach(function(btn){
      btn.addEventListener("click", function(){ showStep(Number(btn.dataset.goStep)); });
    });
    applicationWizard.querySelectorAll("input[type='file']").forEach(function(input){
      input.addEventListener("change", function(){
        const label = input.closest(".upload-drop")?.querySelector("[data-file-label]");
        if(label) label.textContent = input.files && input.files[0] ? input.files[0].name : "Drag & drop or click to upload";
        clearFieldError(input);
      });
    });
    applicationWizard.querySelectorAll("input, select, textarea").forEach(function(field){
      field.addEventListener("input", function(){ clearFieldError(field); schedulePersist(); });
      field.addEventListener("change", function(){ clearFieldError(field); schedulePersist(); });
    });
    applicationWizard.addEventListener("submit", function(e){
      if(!validateAllSteps()){
        e.preventDefault();
        return;
      }
      try{ localStorage.removeItem(DRAFT_KEY); }catch(_){}
      if(nextBtn){
        nextBtn.disabled = true;
        nextBtn.innerHTML = '<i class="bi bi-arrow-repeat" style="animation:spin 1s linear infinite" aria-hidden="true"></i> Submitting...';
      }
    });
    restoreDraft();
    const errorPanel = panels.find(function(panel){ return panel.querySelector(".errorlist"); });
    showStep(errorPanel ? Number(errorPanel.dataset.stepPanel) : 1);
  }

  // ---------- Upload widgets (drag/drop + preview) ----------
  document.querySelectorAll(".upload").forEach(function(root){
    const input = root.querySelector('input[type="file"]');
    if(!input) return;
    const dropEl = root.querySelector(".upload-drop");
    let fileEl = root.querySelector(".upload-file");
    if(!fileEl){
      fileEl = document.createElement("div");
      fileEl.className = "upload-file upload-preview";
      fileEl.style.display = "none";
      fileEl.innerHTML = '<div class="upload-thumb"><i class="bi bi-file-earmark"></i></div><div class="upload-meta"><span class="name"></span><span class="size"></span></div><button class="rm" type="button" aria-label="Remove file"><i class="bi bi-x-lg" aria-hidden="true"></i></button>';
      root.appendChild(fileEl);
    }
    const nameEl = fileEl ? fileEl.querySelector(".name") : null;
    const sizeEl = fileEl ? fileEl.querySelector(".size") : null;
    const thumbEl = fileEl ? fileEl.querySelector(".upload-thumb") : null;
    const rmBtn = fileEl ? fileEl.querySelector(".rm") : null;
    let previewUrl = "";

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
      if(previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = "";
      if(fileEl) fileEl.style.display = "none";
      if(dropEl) dropEl.style.display = "flex";
    });
    function showFile(f){
      if(f.size > 10 * 1024 * 1024){
        window.toast("Max file size is 10 MB", "warn");
        input.value = "";
        return;
      }
      root.classList.add("is-loading");
      if(nameEl) nameEl.textContent = f.name;
      if(sizeEl) sizeEl.textContent = (f.size/1024).toFixed(0) + " KB";
      if(thumbEl) thumbEl.innerHTML = '<i class="bi bi-arrow-repeat" style="animation:spin 1s linear infinite" aria-hidden="true"></i>';
      if(fileEl) fileEl.style.display = "flex";
      if(dropEl) dropEl.style.display = "none";
      window.setTimeout(function(){
        root.classList.remove("is-loading");
        if(!thumbEl) return;
        if(previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = "";
        if(f.type && f.type.indexOf("image/") === 0){
          previewUrl = URL.createObjectURL(f);
          thumbEl.innerHTML = "";
          const img = document.createElement("img");
          img.src = previewUrl;
          img.alt = "";
          thumbEl.appendChild(img);
        }else if(f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")){
          thumbEl.innerHTML = '<i class="bi bi-file-earmark-pdf" aria-hidden="true"></i>';
        }else{
          thumbEl.innerHTML = '<i class="bi bi-file-earmark" aria-hidden="true"></i>';
        }
      }, 260);
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
