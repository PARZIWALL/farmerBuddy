document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const schemeSelect = document.getElementById('schemeSelect');
    const rulesSection = document.getElementById('rules-section');
    const ruleContentDiv = document.getElementById('ruleContent');
    const uploadSection = document.getElementById('upload-section');
    const documentUploadInput = document.getElementById('documentUpload');
    const fileNameDiv = document.getElementById('fileName');
    const statusMessageDiv = document.getElementById('statusMessage');
    const loader = document.getElementById('loader');
    const formSection = document.getElementById('form-section');
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    const uploadArea = document.querySelector('.upload-area');

    // Form inputs - updated to match new fields
    const farmerNameInput = document.getElementById('farmerName');
    const mobileNumberInput = document.getElementById('mobileNumber');
    const cropTypeInput = document.getElementById('cropType');
    const affectedAreaInput = document.getElementById('affectedArea');
    const actualYieldInput = document.getElementById('actualYield');
    const thresholdYieldInput = document.getElementById('thresholdYield');
    const sumInsuredInput = document.getElementById('sumInsured');
    const calamityTypeInput = document.getElementById('calamityType');
    const eligibilityResultDiv = document.getElementById('eligibilityResult');
    const approveBtn = document.getElementById('approveBtn');
    const rejectBtn = document.getElementById('rejectBtn');
    const damagePhoto = document.getElementById('damagePhoto');
    const photoStatusDiv = document.getElementById('photoStatus');

    // State variables
    let isProcessing = false;
    let selectedScheme = '';

    // Realistic mock data with photo data
    const mockApiResponses = {
        'yield_loss': {
            'application1.pdf': { 
                farmerName: 'Ramesh Kumar Singh', mobileNumber: '9876543210', cropType: 'Paddy (Rice)', affectedArea: 2.5, 
                actualYield: 18, thresholdYield: 45, sumInsured: 45000, calamityType: 'Drought and Pest Attack',
                photoVerificationStatus: 'Verified',
                damagePhoto: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
            },
            'application2.pdf': { 
                farmerName: 'Sushila Devi', mobileNumber: '9123456789', cropType: 'Wheat', affectedArea: 4.2, 
                actualYield: 22, thresholdYield: 35, sumInsured: 63000, calamityType: 'Unseasonal Rainfall', 
                photoVerificationStatus: 'Unverified',
                damagePhoto: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
            },
            'farmer_doc.pdf': { 
                farmerName: 'Anil Verma', mobileNumber: '8765432109', cropType: 'Cotton', affectedArea: 3.8, 
                actualYield: 8, thresholdYield: 20, sumInsured: 76000, calamityType: 'Pink Bollworm Attack', 
                photoVerificationStatus: 'Verified',
                damagePhoto: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
            }
        },
        'prevented_sowing': {
            'claim_form.pdf': { 
                farmerName: 'Mukesh Patel', mobileNumber: '9988776655', cropType: 'Groundnut', affectedArea: 2.1, 
                actualYield: 0, thresholdYield: 15, sumInsured: 42000, calamityType: 'Deficient Rainfall - No Sowing Possible',
                preventedSowing: true, photoVerificationStatus: 'Verified',
                damagePhoto: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
            },
            'application.pdf': { 
                farmerName: 'Geeta Sharma', mobileNumber: '9517538520', cropType: 'Maize', affectedArea: 1.8, 
                actualYield: 0, thresholdYield: 25, sumInsured: 36000, calamityType: 'Excess Rainfall - Waterlogged Fields',
                preventedSowing: true, photoVerificationStatus: 'Unverified',
                damagePhoto: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
            }
        },
        'post_harvest': {
            'document.pdf': { 
                farmerName: 'Suresh Yadav', mobileNumber: '9876501234', cropType: 'Mustard', affectedArea: 1.5, 
                actualYield: 12, thresholdYield: 15, sumInsured: 30000, calamityType: 'Hailstorm (Post-Harvest)',
                postHarvest: true, photoVerificationStatus: 'Verified',
                damagePhoto: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
            }
        }
    };

    const schemeRules = {
        'yield_loss': `
            <div class="rule-item">
                <strong><i class="fas fa-calculator"></i> Yield Loss Assessment:</strong>
                <p>Claims calculated as: <strong>[(Threshold Yield - Actual Yield) / Threshold Yield] × Sum Insured</strong></p>
            </div>
            <div class="rule-item">
                <strong><i class="fas fa-percentage"></i> Mid-Season Adversity:</strong>
                <p>On-account payment when <strong>expected yield is less than 50%</strong> of threshold yield</p>
            </div>`,
        'prevented_sowing': `
            <div class="rule-item">
                <strong><i class="fas fa-seedling"></i> Prevented Sowing/Planting:</strong>
                <p>Covers inability to sow due to adverse weather conditions</p>
            </div>
            <div class="rule-item">
                <strong><i class="fas fa-percentage"></i> Compensation:</strong>
                <p><strong>25% of Sum Insured</strong> - Insurance cover terminates after payment</p>
            </div>`,
        'post_harvest': `
            <div class="rule-item">
                <strong><i class="fas fa-warehouse"></i> Post-Harvest Losses:</strong>
                <p>Covers harvested crop left in "cut & spread" condition in field</p>
            </div>
            <div class="rule-item">
                <strong><i class="fas fa-clock"></i> Coverage Period:</strong>
                <p>Maximum <strong>14 days</strong> from harvesting for specific perils</p>
            </div>`
    };

    function updateStatus(text, type = 'ready') {
        statusText.textContent = text;
        statusIndicator.className = `status-indicator ${type}`;
    }

    schemeSelect.addEventListener('change', function() {
        selectedScheme = schemeSelect.value;
        if (selectedScheme) {
            rulesSection.classList.remove('hidden');
            ruleContentDiv.innerHTML = schemeRules[selectedScheme];
            uploadSection.classList.remove('hidden');
            rulesSection.style.transform = 'translateY(0)';
            rulesSection.style.opacity = '1';
        } else {
            rulesSection.classList.add('hidden');
            uploadSection.classList.add('hidden');
            updateStatus('Ready', 'ready');
        }
        resetForm();
    });

    documentUploadInput.addEventListener('change', function(e) {
        if (isProcessing) return;
        
        const file = e.target.files[0];
        if (!file) {
            fileNameDiv.textContent = 'No file selected';
            statusMessageDiv.textContent = '';
            return;
        }

        if (!file.type.includes('pdf')) {
            showStatusMessage('Please select a valid PDF file', 'error');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            showStatusMessage('File size should be less than 10MB', 'error');
            return;
        }

        isProcessing = true;
        updateStatus('Processing...', 'processing');
        fileNameDiv.innerHTML = `<i class="fas fa-file-pdf"></i> ${file.name}`;
        showStatusMessage('Document uploaded successfully. Scanning content...', 'success');
        
        uploadArea.classList.add('scanning');
        formSection.classList.add('hidden');
        loader.classList.remove('hidden');
        
        let progress = 0;
        const progressFill = document.querySelector('.progress-fill');
        const loaderText = document.querySelector('.loader-text');
        
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressFill.style.width = progress + '%';
            
            if (progress < 30) {
                loaderText.textContent = 'Scanning document structure...';
            } else if (progress < 60) {
                loaderText.textContent = 'Extracting farmer information...';
            } else if (progress < 90) {
                loaderText.textContent = 'Validating eligibility criteria...';
            }
        }, 200);

        setTimeout(() => {
            clearInterval(progressInterval);
            progressFill.style.width = '100%';
            loaderText.textContent = 'Processing complete!';
            
            setTimeout(() => {
                const mockData = mockApiResponses[selectedScheme][file.name] || 
                    generateFallbackData(file.name);

                populateForm(mockData);
                checkEligibility(mockData);

                loader.classList.add('hidden');
                formSection.classList.remove('hidden');
                uploadArea.classList.remove('scanning');
                
                updateStatus('Document Processed', 'success');
                isProcessing = false;
                
                progressFill.style.width = '0%';
            }, 500);
        }, 3000);
    });

    function generateFallbackData(filename) {
        const crops = [{ name: 'Paddy (Rice)', threshold: 45, typical: 35 }, { name: 'Wheat', threshold: 35, typical: 28 }];
        const calamities = { 'yield_loss': ['Drought'], 'prevented_sowing': ['Deficient Rainfall'], 'post_harvest': ['Hailstorm (Post-Harvest)'] };
        const selectedCrop = crops[0];
        const actualYield = Math.max(0, selectedCrop.typical - (Math.random() * selectedCrop.typical * 0.8));
        const yieldLoss = ((selectedCrop.threshold - actualYield) / selectedCrop.threshold) * 100;
        
        const fallbackData = {
            farmerName: 'Auto-Extracted Name', mobileNumber: '98XXXXXXXX', cropType: selectedCrop.name,
            affectedArea: parseFloat((Math.random() * 4 + 1).toFixed(1)),
            calamityType: calamities[selectedScheme][0],
            sumInsured: Math.floor((selectedCrop.threshold * 2000) + (Math.random() * 20000)),
            photoVerificationStatus: 'Unverified',
            damagePhoto: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        };
        
        if (selectedScheme === 'yield_loss') {
            fallbackData.actualYield = parseFloat(actualYield.toFixed(1));
            fallbackData.thresholdYield = selectedCrop.threshold;
        } else if (selectedScheme === 'prevented_sowing') {
            fallbackData.actualYield = 0; fallbackData.thresholdYield = selectedCrop.threshold; fallbackData.preventedSowing = true;
        } else if (selectedScheme === 'post_harvest') {
            fallbackData.yieldLossPercent = Math.max(0, parseFloat(yieldLoss.toFixed(1))); fallbackData.postHarvest = true;
        }
        return fallbackData;
    }

    function showStatusMessage(message, type) {
        statusMessageDiv.textContent = message;
        statusMessageDiv.className = `status-message ${type}`;
        if (type === 'error') {
            setTimeout(() => { statusMessageDiv.textContent = ''; statusMessageDiv.className = 'status-message'; }, 4000);
        }
    }

    function resetForm() {
        fileNameDiv.innerHTML = '<i class="fas fa-file"></i> No file selected';
        statusMessageDiv.textContent = '';
        statusMessageDiv.className = 'status-message';
        formSection.classList.add('hidden');
        loader.classList.add('hidden');
        uploadArea.classList.remove('scanning');
        uploadSection.classList.remove('hidden');
        approveBtn.disabled = true;
        rejectBtn.disabled = true;
        
        [farmerNameInput, mobileNumberInput, cropTypeInput, affectedAreaInput, actualYieldInput, thresholdYieldInput, sumInsuredInput, calamityTypeInput].forEach(input => { input.value = ''; });
        
        eligibilityResultDiv.innerHTML = '';
        eligibilityResultDiv.className = 'eligibility-result';
        damagePhoto.classList.add('hidden');
        photoStatusDiv.textContent = '';
        photoStatusDiv.className = 'photo-status';
        updateStatus('Ready', 'ready');
    }

    function populateForm(data) {
        farmerNameInput.value = data.farmerName; mobileNumberInput.value = data.mobileNumber; cropTypeInput.value = data.cropType;
        affectedAreaInput.value = data.affectedArea; sumInsuredInput.value = data.sumInsured; calamityTypeInput.value = data.calamityType;
        
        if (selectedScheme === 'yield_loss') { actualYieldInput.value = data.actualYield; thresholdYieldInput.value = data.thresholdYield; }
        
        if (data.damagePhoto) {
            damagePhoto.src = data.damagePhoto;
            damagePhoto.classList.remove('hidden');
            photoStatusDiv.textContent = `Photo verification status: ${data.photoVerificationStatus}`;
            photoStatusDiv.classList.add(data.photoVerificationStatus === 'Verified' ? 'verified' : 'unverified');
        } else {
            damagePhoto.classList.add('hidden');
            photoStatusDiv.textContent = 'No damage photo found in document.';
            photoStatusDiv.className = 'photo-status';
        }

        formSection.style.transform = 'translateY(10px)'; formSection.style.opacity = '0';
        setTimeout(() => { formSection.style.transform = 'translateY(0)'; formSection.style.opacity = '1'; }, 100);
    }

    function checkEligibility(data) {
        let isEligible = false; let message = ''; let claimAmount = 0;
        
        if (data.photoVerificationStatus === 'Unverified') {
            isEligible = false;
            message = `<strong><i class="fas fa-times-circle"></i> Claim Requires Manual Review:</strong> Damage photo could not be verified by AI.`;
            eligibilityResultDiv.innerHTML = message;
            eligibilityResultDiv.className = 'eligibility-result error';
            approveBtn.disabled = true;
            rejectBtn.disabled = false;
            return;
        }

        if (selectedScheme === 'prevented_sowing') {
            isEligible = data.preventedSowing;
            if (isEligible) { claimAmount = data.sumInsured * 0.25; message = `...` } else { message = `...` }
        } else if (selectedScheme === 'post_harvest') {
            const yieldLossPercent = data.yieldLossPercent;
            isEligible = yieldLossPercent >= 50;
            if (isEligible) { claimAmount = data.sumInsured * (yieldLossPercent / 100); message = `...` } else { message = `...` }
        } else { // yield_loss
            const yieldLossPercent = ((data.thresholdYield - data.actualYield) / data.thresholdYield) * 100;
            if (yieldLossPercent > 0) {
                isEligible = true;
                claimAmount = data.sumInsured * (yieldLossPercent / 100);
                const midSeasonEligible = yieldLossPercent >= 50;
                message = `...`
            } else {
                isEligible = false; message = `...`
            }
        }
        
        eligibilityResultDiv.innerHTML = message; eligibilityResultDiv.className = `eligibility-result ${isEligible ? 'success' : 'error'}`;
        approveBtn.disabled = !isEligible; rejectBtn.disabled = false; updateStatus(isEligible ? 'Eligible for Compensation' : 'Not Eligible', isEligible ? 'success' : 'error');
    }

    approveBtn.addEventListener('click', function() { showActionStatus('Claim Approved', 'success'); });
    rejectBtn.addEventListener('click', function() { showActionStatus('Claim Rejected', 'error'); });

    function showActionStatus(action, type) {
        const farmerName = farmerNameInput.value; const cropType = cropTypeInput.value; const actionText = action === 'approve' ? 'Approved' : 'Rejected';
        const actionClass = action === 'approve' ? 'success' : 'error'; const actionIcon = action === 'approve' ? 'fas fa-check-circle' : 'fas fa-times-circle';
        eligibilityResultDiv.innerHTML = `...`; eligibilityResultDiv.className = 'eligibility-result processing';
        approveBtn.disabled = true; rejectBtn.disabled = true; updateStatus('Submitting...', 'processing');

        setTimeout(() => {
            let message = '';
            if (type === 'success') { message = `...` } else { message = `...` }
            eligibilityResultDiv.innerHTML = message; eligibilityResultDiv.className = `eligibility-result ${actionClass}`;
            updateStatus(`Claim ${actionText}`, actionClass);
            setTimeout(() => { if (confirm('Would you like to process another claim?')) { location.reload(); } }, 10000);
        }, 2000);
    }

    updateStatus('Ready', 'ready');
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case '1': e.preventDefault(); schemeSelect.value = 'yield_loss'; schemeSelect.dispatchEvent(new Event('change')); break;
                case '2': e.preventDefault(); schemeSelect.value = 'prevented_sowing'; schemeSelect.dispatchEvent(new Event('change')); break;
                case '3': e.preventDefault(); schemeSelect.value = 'post_harvest'; schemeSelect.dispatchEvent(new Event('change')); break;
                case 'Enter': e.preventDefault(); if (!approveBtn.disabled) approveBtn.click(); break;
            }
        }
    });
});