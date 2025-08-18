// popup.js
// Popup logic: scheme selection, mock processing, and Autofill via backend + content script messaging.

// ====== Config ======
const BACKEND_URL = 'http://127.0.0.1:5000'; // change to your deployed backend if needed

// ====== DOM refs ======
const schemeSelect = document.getElementById('schemeSelect');
const ruleContent = document.getElementById('ruleContent');

const documentUpload = document.getElementById('documentUpload');
const statusMessage = document.getElementById('statusMessage');
const progressWrap = document.getElementById('progressWrap');
const progressFill = document.getElementById('progressFill');

const userIdInput = document.getElementById('userIdInput');
const autofillPageBtn = document.getElementById('autofillPageBtn');
const autofillStatus = document.getElementById('autofillStatus');

const formSection = document.getElementById('form-section');
const farmerName = document.getElementById('farmerName');
const mobileNumber = document.getElementById('mobileNumber');
const cropType = document.getElementById('cropType');
const affectedArea = document.getElementById('affectedArea');
const actualYield = document.getElementById('actualYield');
const thresholdYield = document.getElementById('thresholdYield');
const damagePhoto = document.getElementById('damagePhoto');
const eligibilityResult = document.getElementById('eligibilityResult');
const approveBtn = document.getElementById('approveBtn');
const rejectBtn = document.getElementById('rejectBtn');

// ====== Mock data used for demo fallback (keeps original demo behavior) ======
const mockApiResponses = {
  'pm-kisan': {
    'sample-pm.pdf': {
      name: 'Ravi Kumar',
      mobile: '9876543210',
      crop: 'Wheat',
      affected_area: '2.5',
      actual_yield: '800',
      threshold_yield: '1200',
      damage_photo_b64: null,
      verification: 'Verified'
    }
  },
  'kcc': {},
  'ridf': {}
};

const schemeRules = {
  'pm-kisan': 'PM-Kisan rule: farmer must have Aadhaar & land records. Claim is based on yield loss.',
  'kcc': 'KCC rule: credit eligibility with PAN and bank details.',
  'ridf': 'RIDF rule: project-related documentation needed.'
};

// ====== Helpers ======
function setStatus(msg) {
  statusMessage.textContent = msg;
}
function showProgress() {
  progressWrap.style.display = 'block';
  progressFill.style.width = '0%';
}
function hideProgress() {
  progressWrap.style.display = 'none';
  progressFill.style.width = '0%';
}
function updateProgress(pct) {
  progressFill.style.width = pct + '%';
}

function resetFormUI() {
  formSection.style.display = 'none';
  farmerName.value = mobileNumber.value = cropType.value = affectedArea.value =
    actualYield.value = thresholdYield.value = '';
  damagePhoto.style.display = 'none';
  eligibilityResult.textContent = '';
}

function populateForm(data) {
  formSection.style.display = 'block';
  farmerName.value = data.name || '';
  mobileNumber.value = data.mobile || '';
  cropType.value = data.crop || '';
  affectedArea.value = data.affected_area || '';
  actualYield.value = data.actual_yield || '';
  thresholdYield.value = data.threshold_yield || '';
  if (data.damage_photo_b64) {
    damagePhoto.src = data.damage_photo_b64;
    damagePhoto.style.display = 'block';
  } else {
    damagePhoto.style.display = 'none';
  }
  // small eligibility note
  eligibilityResult.textContent = data.verification ? `Verification: ${data.verification}` : '';
}

function simulateProcessing(fileName, scheme) {
  // use mock if exists, else fabricate fallback
  return new Promise((resolve) => {
    showProgress();
    setStatus('Scanning document…');
    let pct = 0;
    const t = setInterval(() => {
      pct += Math.floor(Math.random() * 12) + 6;
      if (pct > 95) pct = 95;
      updateProgress(pct);
    }, 350);

    setTimeout(() => {
      clearInterval(t);
      updateProgress(100);
      hideProgress();
      // lookup mock
      const mock = (mockApiResponses[scheme] && mockApiResponses[scheme][fileName]) || null;
      if (mock) {
        setStatus('Document processed (mock).');
        resolve(mock);
      } else {
        // fabricate simple fallback data
        const fallback = {
          name: 'Test Farmer',
          mobile: '7000000000',
          crop: 'Rice',
          affected_area: '1.2',
          actual_yield: '450',
          threshold_yield: '900',
          damage_photo_b64: null,
          verification: 'Unverified'
        };
        setStatus('Document processed (fallback).');
        resolve(fallback);
      }
    }, 2200 + Math.floor(Math.random() * 1200));
  });
}

// ====== Scheme selection handling ======
schemeSelect.addEventListener('change', () => {
  const s = schemeSelect.value;
  if (!s) {
    ruleContent.textContent = 'Select a scheme to view rules.';
  } else {
    ruleContent.textContent = schemeRules[s] || 'No rules available for this scheme.';
  }
  resetFormUI();
});

// ====== File upload handling (keeps original demo behaviour) ======
documentUpload.addEventListener('change', async (ev) => {
  resetFormUI();
  const f = ev.target.files && ev.target.files[0];
  if (!f) {
    setStatus('No file selected.');
    return;
  }
  const scheme = schemeSelect.value || 'pm-kisan';
  // simple validations
  if (!f.type || f.type.indexOf('pdf') === -1) {
    setStatus('Please upload a PDF document.');
    return;
  }
  if (f.size > 12 * 1024 * 1024) {
    setStatus('File too large (max 12MB).');
    return;
  }
  setStatus('File selected: ' + f.name);
  // simulate processing & populate UI
  const data = await simulateProcessing(f.name, scheme);
  populateForm(data);
});

// ====== Approve/Reject buttons (demo) ======
approveBtn.addEventListener('click', () => {
  alert('Approved (demo). In a real flow you would send approval to backend.');
});
rejectBtn.addEventListener('click', () => {
  alert('Rejected (demo). In a real flow you would send rejection to backend.');
});

// ====== --- Autofill flow: collect fields from active page, call backend, apply result --- ======

// Collect named fields from the active tab (content script must handle 'collect_fields')
function collectFieldsFromActiveTab() {
  return new Promise((resolve, reject) => {
    try {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs || !tabs[0]) return reject(new Error('No active tab found'));
        chrome.tabs.sendMessage(tabs[0].id, { action: 'collect_fields' }, (resp) => {
          if (chrome.runtime.lastError) {
            // content script not injected or other error
            return reject(new Error(chrome.runtime.lastError.message));
          }
          resolve((resp && resp.fields) || []);
        });
      });
    } catch (err) {
      reject(err);
    }
  });
}

// Ask active tab to apply mapped fields (content script must handle 'apply_fields')
function applyFieldsToActiveTab(mapped_fields) {
  return new Promise((resolve, reject) => {
    try {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs || !tabs[0]) return reject(new Error('No active tab'));
        chrome.tabs.sendMessage(tabs[0].id, { action: 'apply_fields', mapped_fields: mapped_fields }, (resp) => {
          if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
          resolve(resp);
        });
      });
    } catch (err) {
      reject(err);
    }
  });
}

async function requestAutofillFromServer(userId, fields) {
  // body: user_id, output_type=json, fields[]
  const body = { user_id: userId, output_type: 'json', fields: fields || [] };
  const res = await fetch(`${BACKEND_URL}/auto_fill_user`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Server ${res.status}: ${txt}`);
  }
  const j = await res.json();
  return j;
}

autofillPageBtn.addEventListener('click', async (e) => {
  e.preventDefault();
  autofillStatus.textContent = '';
  const uid = (userIdInput.value || '').trim();
  if (!uid) {
    autofillStatus.textContent = 'Please paste a valid user_id before autofill.';
    return;
  }

  try {
    autofillStatus.textContent = 'Collecting fields from active page…';
    let fields = [];
    try {
      fields = await collectFieldsFromActiveTab();
    } catch (err) {
      // continue with empty fields; server can try template-based mapping
      console.warn('Could not collect fields from page:', err.message || err);
      autofillStatus.textContent = 'Warning: could not collect fields from page; proceeding with template mapping.';
      fields = [];
    }

    autofillStatus.textContent = `Requesting autofill for user ${uid}…`;
    const serverResp = await requestAutofillFromServer(uid, fields);

    if (!serverResp || !serverResp.success) {
      throw new Error(serverResp && (serverResp.error || serverResp.message) ? (serverResp.error || serverResp.message) : 'Server returned failure');
    }

    const mapped = serverResp.mapped_fields || serverResp.fields || serverResp.mappedFields || {};
    if (!mapped || Object.keys(mapped).length === 0) {
      autofillStatus.textContent = 'Server returned no mapped values.';
      return;
    }

    autofillStatus.textContent = 'Applying values to the active page…';
    await applyFieldsToActiveTab(mapped);

    autofillStatus.textContent = 'Autofill applied — please verify the page fields.';
  } catch (err) {
    console.error('Autofill error', err);
    autofillStatus.textContent = 'Autofill failed: ' + (err.message || err);
  }
});
