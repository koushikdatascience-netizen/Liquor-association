/* =========================================================
   WBFL Association — Wizard Step Navigation
   Handles Prev/Next/Save-Draft across membership/step1..5 + review
   ========================================================= */
(function(){
  "use strict";

  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const saveBtn = document.getElementById("saveBtn");
  const submitBtn = document.getElementById("submitBtn");

  if(!prevBtn && !nextBtn && !submitBtn) return; // not a wizard page

  const DRAFT_KEY = "wbfl_membership_draft";

  function collectFormData(){
    const data = {};
    document.querySelectorAll(".wizard-card input, .wizard-card select, .wizard-card textarea").forEach(function(el){
      if(el.type === "file") return;
      if(el.type === "checkbox"){ data[el.id] = el.checked; }
      else if(el.id){ data[el.id] = el.value; }
    });
    return data;
  }

  function persist(){
    try{
      const existing = JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}");
      const merged = Object.assign(existing, collectFormData());
      localStorage.setItem(DRAFT_KEY, JSON.stringify(merged));
    }catch(_){}
  }

  function restore(){
    try{
      const raw = localStorage.getItem(DRAFT_KEY);
      if(!raw) return;
      const data = JSON.parse(raw);
      Object.keys(data).forEach(function(k){
        const el = document.getElementById(k);
        if(!el) return;
        if(el.type === "checkbox") el.checked = !!data[k];
        else el.value = data[k];
      });
    }catch(_){}
  }

  function validateRequired(){
    const required = document.querySelectorAll(".wizard-card [required]");
    let ok = true;
    let firstInvalid = null;
    required.forEach(function(el){
      const empty = el.type === "checkbox" ? !el.checked : !el.value.trim();
      el.classList.toggle("is-error", empty);
      if(empty){
        ok = false;
        if(!firstInvalid) firstInvalid = el;
      }
    });
    if(firstInvalid) firstInvalid.focus();
    return ok;
  }

  document.addEventListener("input", function(e){
    if(e.target.classList && e.target.classList.contains("is-error") && e.target.value && e.target.value.trim()){
      e.target.classList.remove("is-error");
    }
  });

  prevBtn && prevBtn.addEventListener("click", function(){
    if(prevBtn.disabled) return;
    persist();
    if(window.WIZARD_PREV) window.location.href = window.WIZARD_PREV;
  });

  nextBtn && nextBtn.addEventListener("click", function(){
    if(!validateRequired()){
      window.toast && window.toast("Please complete the required fields", "warn");
      return;
    }
    persist();
    if(window.WIZARD_NEXT) window.location.href = window.WIZARD_NEXT;
  });

  saveBtn && saveBtn.addEventListener("click", function(){
    persist();
    window.toast && window.toast("Draft saved");
  });

  submitBtn && submitBtn.addEventListener("click", function(){
    persist();
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="bi bi-arrow-repeat" style="animation:spin 1s linear infinite"></i> Submitting...';
    setTimeout(function(){
      localStorage.removeItem(DRAFT_KEY);
      window.location.href = window.WIZARD_SUBMIT_REDIRECT || "submitted.html";
    }, 1000);
  });

  // ---------- Review page rendering ----------
  const reviewContent = document.getElementById("reviewContent");
  if(reviewContent){
    let draft = {};
    try{ draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}"); }catch(_){}

    const SECTIONS = [
      { title: "Personal details", editHref: "step1.html", fields: [
        ["Name","memberName"],["Nationality","nationality"],["Age","age"],["Gender","gender"],
        ["Address","address"],["PIN","pin"],["WhatsApp","whatsapp"],["Email","email"],["Phone","phone"]
      ]},
      { title: "Business details", editHref: "step2.html", fields: [
        ["Entity type","entityType"],["Licence category","licenceCat"],["Style name","styleName"],
        ["Licence ID","licenceId"],["Partners / MD","partners"],["Office phone","phoneOffice"],["Shop phone","phoneShop"]
      ]},
      { title: "Representative details", editHref: "step3.html", fields: [
        ["Primary delegate","pdName"],["Primary address","pdAddress"],
        ["Alternate delegate","adName"],["Alternate address","adAddress"]
      ]},
      { title: "Declaration", editHref: "step5.html", fields: [
        ["Signature","signature"]
      ]}
    ];

    function esc(s){
      return String(s || "").replace(/[&<>"']/g, function(c){
        return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
      });
    }

    const html = SECTIONS.map(function(section){
      const items = section.fields.map(function(pair){
        const label = pair[0], key = pair[1];
        const value = draft[key];
        const empty = !value;
        return '<div class="review-item"><span>' + esc(label) + '</span><b class="' + (empty ? "muted" : "") + '">' +
          (empty ? "Not provided" : esc(value)) + '</b></div>';
      }).join("");
      return '<div class="review-block"><div class="review-head"><h5>' + esc(section.title) + '</h5>' +
        '<button type="button" class="btn btn-ghost btn-sm" data-goto="' + section.editHref + '"><i class="bi bi-pencil" aria-hidden="true"></i> Edit</button></div>' +
        '<div class="review-grid">' + items + '</div></div>';
    }).join("");

    reviewContent.innerHTML = html;
    reviewContent.querySelectorAll("[data-goto]").forEach(function(btn){
      btn.addEventListener("click", function(){ window.location.href = btn.dataset.goto; });
    });
  }

  // ---------- Init ----------
  restore();
  setInterval(persist, 15000);

})();
