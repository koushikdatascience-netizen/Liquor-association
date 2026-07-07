/* =========================================================
   WBFL Association — Shared Field Validators
   (email, PIN, phone format helpers used across forms)
   ========================================================= */
(function(){
  "use strict";

  function isValidEmail(v){ return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }
  function isValidPin(v){ return /^\d{6}$/.test(v); }
  function isValidPhone(v){ return /^[+]?[\d\s-]{7,15}$/.test(v); }

  window.WBFLValidators = { isValidEmail, isValidPin, isValidPhone };

  document.addEventListener("blur", function(e){
    const el = e.target;
    if(!el.classList) return;
    if(el.type === "email" && el.value && !isValidEmail(el.value)){
      el.classList.add("is-error");
      window.toast && window.toast("Please enter a valid email address", "warn");
    }
    if(el.id === "pin" && el.value && !isValidPin(el.value)){
      el.classList.add("is-error");
      window.toast && window.toast("PIN code must be 6 digits", "warn");
    }
  }, true);

})();
