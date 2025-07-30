// Global state
let allCampaigns = [];
let allContacts = [];
let selectedContactIds = new Set();

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
    }
}

// --- Modal Management ---
function showModal(modalId) { document.getElementById(modalId).classList.remove('hidden'); }
function hideModal(modalId) { document.getElementById(modalId).classList.add('hidden'); }
function showCreateCampaignModal() { showModal('create-campaign-modal'); }
function showCreateContactModal() { showModal('create-contact-modal'); }
async function showContactSelector() {
    await loadContactsForSelector();
    showModal('contact-selector-modal');
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
    if (!confirm('Are you sure you want to start this campaign?')) return;
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

// --- Call History ---
function loadCalls() {
    const list = document.getElementById('calls-list');
    list.innerHTML = '<p>Call history functionality is coming soon.</p>';
}

// --- Form Handlers ---
document.getElementById('campaign-form').addEventListener('submit', async function (e) {
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

document.getElementById('contact-form').addEventListener('submit', async function (e) {
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
        alert('Error: ' + error.message);
        console.error('Error creating contact:', error);
    }
});


// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    loadCampaigns();
});