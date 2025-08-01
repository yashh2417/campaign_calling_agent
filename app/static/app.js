// Global state
let allCampaigns = [];
let allContacts = [];
let allUsers = [];
let selectedContactIds = new Set();
let selectedVoice = null;

const API_BASE = '/api';

// --- Tab Management ---
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('hidden'));
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.remove('hidden');
    event.currentTarget.classList.add('active');

    switch (tabName) {
        case 'campaigns': loadCampaigns(); break;
        case 'contacts': loadContacts(); break;
        case 'calls': loadCalls(); break;
        case 'users': loadUsers(); break;
        case 'test-voice': loadVoices(); break;
    }
}

// --- Modal Management ---
function showModal(modalId) { document.getElementById(modalId).classList.remove('hidden'); }
function hideModal(modalId) { document.getElementById(modalId).classList.add('hidden'); }
function showCreateCampaignModal() { showModal('create-campaign-modal'); }
function showCreateContactModal() { showModal('create-contact-modal'); }
function showCreateUserModal() { showModal('create-user-modal'); }

async function showContactSelector() {
    await loadContactsForSelector();
    showModal('contact-selector-modal');
}

// --- Voice Testing Functions ---
function selectVoice(voiceId) {
    // Remove previous selection
    document.querySelectorAll('.voice-option').forEach(option => {
        option.classList.remove('selected');
    });

    // Add selection to clicked voice
    document.querySelector(`[data-voice="${voiceId}"]`).classList.add('selected');
    selectedVoice = voiceId;

    // Enable test button
    document.getElementById('test-voice-btn').disabled = false;
}

async function testVoice() {
    const phoneNumber = document.getElementById('test-phone').value.trim();
    const resultDiv = document.getElementById('voice-test-result');
    const testBtn = document.getElementById('test-voice-btn');

    if (!phoneNumber) {
        showMessage('Please enter your phone number', 'error', resultDiv);
        return;
    }

    if (!selectedVoice) {
        showMessage('Please select a voice', 'error', resultDiv);
        return;
    }

    if (!phoneNumber.startsWith('+')) {
        showMessage('Phone number must start with + (international format)', 'error', resultDiv);
        return;
    }

    testBtn.disabled = true;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Making Test Call...';

    try {
        const response = await fetch(`${API_BASE}/features/test-voice`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_phone_number: phoneNumber,
                voice: selectedVoice
            })
        });

        const result = await response.json();

        if (response.ok) {
            showMessage(
                `✅ ${result.message} Check your phone - you should receive a call shortly!`,
                'success',
                resultDiv
            );

            if (result.call_id) {
                showMessage(
                    `Call ID: ${result.call_id}`,
                    'info',
                    resultDiv,
                    true
                );
            }
        } else {
            showMessage(`❌ ${result.detail || 'Test call failed'}`, 'error', resultDiv);
        }
    } catch (error) {
        showMessage(`❌ Error: ${error.message}`, 'error', resultDiv);
        console.error('Voice test error:', error);
    } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = '<i class="fas fa-phone"></i> Test Selected Voice';
    }
}

async function generateAudio() {
    const text = document.getElementById('audio-text').value.trim();
    const resultDiv = document.getElementById('audio-result');

    if (!text) {
        showMessage('Please enter some text', 'error', resultDiv);
        return;
    }

    if (!selectedVoice) {
        showMessage('Please select a voice', 'error', resultDiv);
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/features/generate-audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                voice: selectedVoice
            })
        });

        if (response.ok) {
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            resultDiv.innerHTML = `
                <div class="success-message">
                    ✅ Audio generated successfully!
                    <audio controls style="width: 100%; margin-top: 10px;">
                        <source src="${audioUrl}" type="audio/wav">
                        Your browser does not support audio playback.
                    </audio>
                    <br>
                    <a href="${audioUrl}" download="voice_${selectedVoice}.wav" class="btn btn-secondary" style="margin-top: 10px;">
                        <i class="fas fa-download"></i> Download Audio
                    </a>
                </div>
            `;
        } else {
            const error = await response.json();
            showMessage(`❌ ${error.detail || 'Audio generation failed'}`, 'error', resultDiv);
        }
    } catch (error) {
        showMessage(`❌ Error: ${error.message}`, 'error', resultDiv);
        console.error('Audio generation error:', error);
    }
}

async function loadVoices() {
    try {
        const response = await fetch(`${API_BASE}/features/available-voices`);
        const data = await response.json();

        if (response.ok && data.voices) {
            const container = document.querySelector('.voice-selector');
            container.innerHTML = data.voices.map(voice => `
                <div class="voice-option" data-voice="${voice.id}" onclick="selectVoice('${voice.id}')">
                    <i class="fas fa-${voice.gender === 'female' ? 'female' : 'male'}"></i><br>
                    ${voice.name}<br>
                    <small>${voice.description}</small>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading voices:', error);
    }
}

// --- Utility Functions ---
function showMessage(message, type, container, append = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `${type}-message`;
    messageDiv.textContent = message;

    if (append) {
        container.appendChild(messageDiv);
    } else {
        container.innerHTML = '';
        container.appendChild(messageDiv);
    }

    // Auto-remove success messages after 10 seconds
    if (type === 'success') {
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 10000);
    }
}

// --- Campaign Management ---
async function loadCampaigns() {
    const grid = document.getElementById('campaigns-grid');
    grid.innerHTML = '<div class="loading">Loading campaigns...</div>';
    try {
        const response = await fetch(`${API_BASE}/campaigns/`);
        allCampaigns = await response.json();
        renderCampaigns();
    } catch (error) {
        grid.innerHTML = '<div class="error">Failed to load campaigns.</div>';
        console.error('Error loading campaigns:', error);
    }
}

function renderCampaigns() {
    const grid = document.getElementById('campaigns-grid');
    if (allCampaigns.length === 0) {
        grid.innerHTML = `<p>No campaigns found. Click "Create New Campaign" to start.</p>`;
        return;
    }
    grid.innerHTML = allCampaigns.map(c => `
        <div class="card campaign-card">
            <div class="campaign-header">
                <div>
                    <div class="campaign-title">${c.campaign_name}</div>
                    <div class="campaign-subtitle">Version ${c.version} • Agent: ${c.agent_name || 'N/A'}</div>
                </div>
                <span class="campaign-status status-${c.status}">${c.status}</span>
            </div>
            <div class="campaign-details">
                <div><i class="fas fa-users"></i> Contacts: ${c.contact_list?.length || 0}</div>
                <div><i class="fas fa-calendar-alt"></i> Created: ${new Date(c.created_at).toLocaleDateString()}</div>
                ${c.batch_id ? `<div><i class="fas fa-id-badge"></i> Batch: ${c.batch_id}</div>` : ''}
            </div>
            <div class="campaign-actions">
                <button class="btn btn-secondary" onclick="editCampaign('${c.campaign_id}')"><i class="fas fa-edit"></i> Edit</button>
                <button class="btn btn-success" onclick="startCampaign('${c.campaign_id}')" ${c.status === 'active' ? 'disabled' : ''}>
                    <i class="fas fa-play"></i> Start
                </button>
            </div>
        </div>
    `).join('');
}

async function startCampaign(campaignId) {
    if (!confirm('Are you sure you want to start this campaign? This will make actual phone calls.')) return;
    try {
        const response = await fetch('/start_campaign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ campaign_id: campaignId })
        });
        if (!response.ok) throw new Error('Server responded with an error.');
        alert('Campaign started successfully!');
        loadCampaigns();
    } catch (error) {
        alert('Failed to start campaign.');
        console.error('Error starting campaign:', error);
    }
}

// --- Contact Management ---
async function loadContacts() {
    const list = document.getElementById('contacts-list');
    list.innerHTML = '<div class="loading">Loading contacts...</div>';
    try {
        const response = await fetch(`${API_BASE}/contacts/`);
        allContacts = await response.json();
        renderContacts();
    } catch (error) {
        list.innerHTML = '<div class="error">Failed to load contacts.</div>';
        console.error('Error loading contacts:', error);
    }
}

function renderContacts() {
    const container = document.getElementById('contacts-list');
    if (allContacts.length === 0) {
        container.innerHTML = `<p>No contacts found. Click "Add Contact" to create one.</p>`;
        return;
    }
    container.innerHTML = allContacts.map(c => `
        <div class="contact-list-item">
            <div class="contact-info">
                <h4>${c.name}</h4>
                <p>${c.phone_number} • ${c.company_name || 'No Company'}</p>
            </div>
            <div class="button-group">
                <button class="btn btn-secondary"><i class="fas fa-edit"></i></button>
                <button class="btn btn-danger"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `).join('');
}

async function loadContactsForSelector() {
    if (allContacts.length === 0) await loadContacts();
    const container = document.getElementById('contact-selector-list');
    container.innerHTML = allContacts.map(c => `
        <div class="contact-selector-item">
            <input type="checkbox" id="contact-${c.id}" value="${c.id}" ${selectedContactIds.has(c.id) ? 'checked' : ''} onchange="toggleContactSelection(${c.id})">
            <label for="contact-${c.id}">${c.name} (${c.phone_number})</label>
        </div>
    `).join('');
}

function toggleContactSelection(contactId) {
    if (selectedContactIds.has(contactId)) {
        selectedContactIds.delete(contactId);
    } else {
        selectedContactIds.add(contactId);
    }
}

function confirmContactSelection() {
    const summaryDiv = document.getElementById('selected-contacts-summary');
    summaryDiv.textContent = `${selectedContactIds.size} contacts selected.`;
    hideModal('contact-selector-modal');
}

// --- User Management ---
async function loadUsers() {
    const list = document.getElementById('users-list');
    list.innerHTML = '<div class="loading">Loading users...</div>';
    try {
        const response = await fetch(`${API_BASE}/users/`);
        allUsers = await response.json();
        renderUsers();
    } catch (error) {
        list.innerHTML = '<div class="error">Failed to load users.</div>';
        console.error('Error loading users:', error);
    }
}

function renderUsers() {
    const container = document.getElementById('users-list');
    if (allUsers.length === 0) {
        container.innerHTML = `<p>No users found. Click "Add User" to create one.</p>`;
        return;
    }
    container.innerHTML = allUsers.map(u => `
        <div class="user-management">
            <div class="contact-info">
                <h4>${u.name}</h4>
                <p>${u.email} • ${u.phone_number}</p>
                ${u.business_name ? `<p><strong>Business:</strong> ${u.business_name}</p>` : ''}
            </div>
            <div class="button-group">
                <button class="btn btn-secondary"><i class="fas fa-edit"></i></button>
                <button class="btn btn-danger"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `).join('');
}

// --- Call History ---
function loadCalls() {
    const list = document.getElementById('calls-list');
    list.innerHTML = '<p>Call history functionality is coming soon.</p>';
}

// --- Form Handlers ---
document.addEventListener('DOMContentLoaded', () => {
    // Campaign form
    document.getElementById('campaign-form')?.addEventListener('submit', async function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        const campaignData = {
            campaign_name: formData.get('campaign_name'),
            agent_name: formData.get('agent_name'),
            task: formData.get('task'),
            contact_list: Array.from(selectedContactIds)
        };

        try {
            const response = await fetch(`${API_BASE}/campaigns/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(campaignData)
            });
            if (!response.ok) throw new Error('Failed to create campaign');

            alert('Campaign created successfully!');
            hideModal('create-campaign-modal');
            this.reset();
            selectedContactIds.clear();
            document.getElementById('selected-contacts-summary').textContent = '';
            loadCampaigns();
        } catch (error) {
            alert('Error: ' + error.message);
            console.error('Error creating campaign:', error);
        }
    });

    // Contact form
    document.getElementById('contact-form')?.addEventListener('submit', async function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        const contactData = Object.fromEntries(formData.entries());

        try {
            const response = await fetch(`${API_BASE}/contacts/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(contactData)
            });
            if (!response.ok) throw new Error('Failed to add contact');

            alert('Contact added successfully!');
            hideModal('create-contact-modal');
            this.reset();
            loadContacts();
        } catch (error) {
            alert('Error