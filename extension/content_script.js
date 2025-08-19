// content_script.js
// Collects named form fields on the page and applies mapped values when asked.

function collectFormFieldsFromPage() {
  const elems = Array.from(document.querySelectorAll('input, select, textarea'));
  const fields = [];

  elems.forEach(el => {
    // skip invisible/disabled elements
    if (el.disabled) return;
    // skip inputs without name/id
    const idOrName = el.name || el.id;
    if (!idOrName) return;

    // skip hidden inputs
    const style = window.getComputedStyle(el);
    if (style && (style.display === 'none' || style.visibility === 'hidden' || el.type === 'hidden')) return;

    // find label if available
    let label = '';
    try {
      const lab = document.querySelector(`label[for="${el.id}"]`) || el.closest('label');
      if (lab) label = lab.innerText.trim();
    } catch (e) {}

    if (!label) label = el.placeholder || idOrName;

    // infer basic field type
    let field_type = 'text';
    const t = (el.getAttribute('type') || '').toLowerCase();
    if (t === 'date') field_type = 'date';
    if (t === 'tel') field_type = 'tel';
    if (t === 'email') field_type = 'email';
    if (/aadhaar|aadhar/i.test(label) || /aadhaar|aadhar/i.test(idOrName)) field_type = 'aadhaar';
    if (/pan/i.test(label) || /pan/i.test(idOrName)) field_type = 'pan';
    if (/voter|epic/i.test(label) || /voter|epic/i.test(idOrName)) field_type = 'voter_id';

    fields.push({
      field_id: idOrName,
      label: label,
      field_type: field_type
    });
  });

  return fields;
}

function applyMappedFieldsToPage(mapped_fields) {
  // mapped_fields expected format:
  // { field_id: { value: "...", confidence: 90, source: "...", note: "..." }, ... }
  Object.entries(mapped_fields || {}).forEach(([fid, obj]) => {
    try {
      const selector = `[name="${fid}"], #${fid}`;
      const el = document.querySelector(selector);
      if (!el) {
        // try looser selector: data-field attribute
        const el2 = document.querySelector(`[data-field="${fid}"]`);
        if (el2) {
          el2.textContent = (typeof obj === 'object' && obj.value !== undefined) ? obj.value : obj;
        }
        return;
      }

      const rawVal = (typeof obj === 'object' && obj.value !== undefined) ? obj.value : obj;
      const val = rawVal == null ? '' : String(rawVal);

      if (el.tagName.toLowerCase() === 'select') {
        // try to set option if exists, otherwise set value
        const opt = Array.from(el.options).find(o => o.value === val || o.text === val);
        if (opt) {
          el.value = opt.value;
        } else {
          el.value = val;
        }
      } else if (el.tagName.toLowerCase() === 'input' || el.tagName.toLowerCase() === 'textarea') {
        if (el.type === 'checkbox' || el.type === 'radio') {
          // set checked if truthy matches
          el.checked = !!val;
        } else {
          el.value = val;
        }
      } else {
        el.textContent = val;
      }

      // dispatch events so frameworks detect the change
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));

      // visual hint based on confidence
      let conf = null;
      if (obj && typeof obj.confidence !== 'undefined') {
        conf = Number(obj.confidence) || 0;
      }
      if (conf !== null && !Number.isNaN(conf)) {
        if (conf >= 80) {
          el.style.boxShadow = '0 0 0 3px rgba(16,185,129,0.12)';
        } else if (conf >= 50) {
          el.style.boxShadow = '0 0 0 3px rgba(255,165,0,0.12)';
        } else {
          el.style.boxShadow = '0 0 0 3px rgba(220,38,38,0.12)';
        }
      } else {
        // subtle highlight for injected values
        el.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.06)';
      }
    } catch (e) {
      console.error('applyMappedFieldsToPage error for', fid, e);
    }
  });
}

// respond to popup messages
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.action) {
    sendResponse({ error: 'no action' });
    return true;
  }

  if (msg.action === 'collect_fields') {
    try {
      const fields = collectFormFieldsFromPage();
      sendResponse({ fields });
    } catch (e) {
      console.error('collect_fields error', e);
      sendResponse({ fields: [] });
    }
    return true; // keep channel open
  }

  if (msg.action === 'apply_fields') {
    try {
      applyMappedFieldsToPage(msg.mapped_fields || {});
      sendResponse({ applied: true });
    } catch (e) {
      console.error('apply_fields error', e);
      sendResponse({ applied: false, error: String(e) });
    }
    return true;
  }

  // unknown action
  sendResponse({ error: 'unknown action' });
  return true;
});
