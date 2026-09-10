/**
 * Conference Deadline Tracker - Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // API base URL - adjust if needed
    const API_BASE = '';
    
    // State
    let allDeadlines = [];
    let allConferences = [];
    
    // DOM Elements
    const conferenceFilter = document.getElementById('conference-filter');
    const addWorkshopBtn = document.getElementById('add-workshop-btn');
    const addConferenceBtn = document.getElementById('add-conference-btn');
    const workshopModal = document.getElementById('workshop-modal');
    const conferenceModal = document.getElementById('conference-modal');
    const closeModal = document.querySelector('.close');
    const closeWorkshopModal = document.getElementById('close-workshop-modal');
    const closeConferenceModal = document.getElementById('close-conference-modal');
    const workshopForm = document.getElementById('workshop-form');
    const conferenceForm = document.getElementById('conference-form');
    const workshopListContainer = document.getElementById('workshop-list-container');
    
    // Helper: Safely parses YYYY-MM-DD date strings in local time without UTC offset shifts
    function parseLocalDate(dateStr) {
        if (!dateStr) return null;
        const cleanDate = dateStr.split('T')[0];
        const parts = cleanDate.split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1;
            const day = parseInt(parts[2], 10);
            return new Date(year, month, day);
        }
        const date = new Date(dateStr);
        return isNaN(date.getTime()) ? null : date;
    }

    // Initialize
    init();
    
    async function init() {
        await loadConferences();
        await loadDeadlines();
        setupEventListeners();
    }
    
    async function loadConferences() {
        try {
            const response = await fetch(`${API_BASE}/api/conferences`);
            allConferences = await response.json();
            
            // Populate conference filter
            conferenceFilter.innerHTML = '<option value="all">All Conferences</option>';
            allConferences.forEach(conf => {
                const option = document.createElement('option');
                option.value = conf.name;
                option.textContent = conf.name;
                conferenceFilter.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading conferences:', error);
        }
    }
    
    async function loadDeadlines() {
        try {
            const response = await fetch(`${API_BASE}/api/deadlines`);
            allDeadlines = await response.json();
            console.log('Loaded deadlines:', allDeadlines.length);
            
            renderTimeline();
            renderWorkshopList();
        } catch (error) {
            console.error('Error loading deadlines:', error);
        }
    }
    
    function setupEventListeners() {
        conferenceFilter.addEventListener('change', renderTimeline);
        conferenceFilter.addEventListener('change', renderWorkshopList);
        
        addWorkshopBtn.addEventListener('click', () => {
            workshopModal.classList.remove('hidden');
        });
        
        addConferenceBtn.addEventListener('click', () => {
            conferenceModal.classList.remove('hidden');
        });
        
        closeModal.addEventListener('click', () => {
            workshopModal.classList.add('hidden');
        });
        
        closeWorkshopModal.addEventListener('click', () => {
            workshopModal.classList.add('hidden');
        });
        
        closeConferenceModal.addEventListener('click', () => {
            conferenceModal.classList.add('hidden');
        });
        
        window.addEventListener('click', (e) => {
            if (e.target === workshopModal) {
                workshopModal.classList.add('hidden');
            }
            if (e.target === conferenceModal) {
                conferenceModal.classList.add('hidden');
            }
        });
        
        workshopForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await addWorkshop();
        });
        
        conferenceForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await addConference();
        });
    }
    
    function getFilteredDeadlines() {
        const selectedConf = conferenceFilter.value;
        if (selectedConf === 'all') {
            return allDeadlines;
        }
        return allDeadlines.filter(d => d.conference_name === selectedConf);
    }

	function renderTimeline() {
        const rawDeadlines = getFilteredDeadlines();
        const container = document.getElementById('timeline-chart');
        if (!container) return;
        
        if (!rawDeadlines || rawDeadlines.length === 0) {
            container.innerHTML = '<div class="no-data">No data available for the selected conference</div>';
            return;
        }

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        // Set time window: 1 week ago to 1 year from today
        const minDate = new Date(today);
        minDate.setDate(minDate.getDate() - 7);

        const maxDate = new Date(today);
        maxDate.setFullYear(maxDate.getFullYear() + 1);

        const totalDays = (maxDate - minDate) / 86400000;
        const todayOffset = Math.max(0, Math.min(100, ((today - minDate) / 86400000) / totalDays * 100));

        // Filter deadlines that overlap with this 1-year range
        const deadlines = rawDeadlines.filter(d => {
            const start = parseLocalDate(d.paper_submission_date);
            const end = parseLocalDate(d.intimation_date);
            return start && end && end >= minDate && start <= maxDate;
        });

        if (deadlines.length === 0) {
            container.innerHTML = '<div class="no-data">No deadline date ranges found within the 1-year window</div>';
            return;
        }

        // Dynamic label width calculation
        let maxWidth = 180;
        deadlines.forEach(d => {
            const name = d.workshop_name || d.track_name || 'Main Track';
            const labelText = `${d.conference_name || ''} - ${name}`;
            const textWidth = Math.min(labelText.length * 7.5, 320);
            maxWidth = Math.max(maxWidth, textWidth);
        });

        // Render Header Scale
        let html = `
            <div class="timeline-wrapper">
                <div class="timeline-scale-row">
                    <div class="timeline-label-spacer" style="width: ${maxWidth}px"></div>
                    <div class="timeline-scale">
        `;

        const numMarkers = 6;
        for (let i = 0; i <= numMarkers; i++) {
            const date = new Date(minDate);
            date.setDate(date.getDate() + Math.round(totalDays * i / numMarkers));
            const left = (i / numMarkers) * 100;
            html += `<div class="scale-marker" style="left: ${left}%"><span>${date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}</span></div>`;
        }

        html += `
                    </div>
                </div>
                <div class="timeline-bars">
                    <!-- Single global Today line overlay -->
                    <div class="today-line-overlay" style="left: calc(${maxWidth}px + (100% - ${maxWidth}px) * ${todayOffset / 100})"></div>
        `;

        // Render Rows
        deadlines.forEach(d => {
            const start = parseLocalDate(d.paper_submission_date);
            const end = parseLocalDate(d.intimation_date);
            const abstractDate = parseLocalDate(d.abstract_deadline);

            const startOffset = Math.max(0, Math.min(100, ((start - minDate) / 86400000) / totalDays * 100));
            const endOffset = Math.max(0, Math.min(100, ((end - minDate) / 86400000) / totalDays * 100));
            const width = Math.max(1.5, endOffset - startOffset);

            const daysToSubmission = Math.ceil((start - today) / 86400000);

            let daysColorClass = 'days-green';
            if (daysToSubmission <= 10) daysColorClass = 'days-darkred';
            else if (daysToSubmission <= 30) daysColorClass = 'days-red';
            else if (daysToSubmission <= 60) daysColorClass = 'days-yellow';

            const daysDisplay = daysToSubmission > 0 ? `${daysToSubmission} days left` : 
                               daysToSubmission === 0 ? 'Today!' : 
                               `${Math.abs(daysToSubmission)} days ago`;

            const name = d.workshop_name || d.track_name || 'Main Track';
            const confName = d.conference_name || 'Conference';
            const strikeClass = daysToSubmission <= 0 ? 'strike-through' : '';
            const durationDays = Math.round((end - start) / 86400000);

            html += `
                <div class="timeline-row">
                    <div class="timeline-label" style="width: ${maxWidth}px">
                        <div class="conference-name" title="${confName} - ${name}">${confName} - ${name}</div>
                        <div class="days-left ${daysColorClass} ${strikeClass}">${daysDisplay}</div>
                    </div>
                    <div class="timeline-bar-container">
                        <div class="timeline-bar submission-start" style="left: ${startOffset}%; width: ${width}%">
                            <span class="duration">${durationDays}d</span>
                        </div>
                        ${abstractDate && abstractDate >= minDate && abstractDate <= maxDate ? `<div class="timeline-marker abstract-marker" style="left: ${((abstractDate - minDate) / 86400000) / totalDays * 100}%" title="Abstract Deadline"></div>` : ''}
                        ${end >= minDate && end <= maxDate ? `<div class="timeline-marker notification-marker" style="left: ${((end - minDate) / 86400000) / totalDays * 100}%" title="Notification Date"></div>` : ''}
                    </div>
                </div>
            `;
        });

        html += '</div></div>';
        container.innerHTML = html;
    }

    function renderWorkshopList() {
        const deadlines = getFilteredDeadlines();
        
        if (deadlines.length === 0) {
            workshopListContainer.innerHTML = '<p>No workshops or tracks found.</p>';
            return;
        }
        
        const html = deadlines.map(d => {
            const isWorkshop = !!d.workshop_name;
            const cardClass = isWorkshop ? 'workshop-card workshop' : 'workshop-card';
            const name = d.workshop_name || (d.track_name || 'Main Track');
            const url = d.url || d.link || d.website;
            
            const titleHtml = url 
                ? `<a href="${url}" target="_blank" rel="noopener noreferrer" class="workshop-title-link">${name} ↗</a>`
                : name;

            return `
                <div class="${cardClass}">
                    <div class="workshop-header">
                        <div class="workshop-name">${titleHtml}</div>
                    </div>
                    <div class="workshop-dates">
                        <strong>Conference:</strong> ${d.conference_name}<br>
                        <strong>Paper:</strong> ${formatDate(d.paper_submission_date)} | 
                        ${d.abstract_deadline ? `<strong>Abstract:</strong> ${formatDate(d.abstract_deadline)} | ` : ''}
                        <strong>Notification:</strong> ${formatDate(d.intimation_date)}
                    </div>
                </div>
            `;
        }).join('');
        
        workshopListContainer.innerHTML = html;
    }
	
    async function addWorkshop() {
        const data = {
            conference_name: document.getElementById('conference-name').value,
            track_name: document.getElementById('track-name').value,
            workshop_name: document.getElementById('workshop-name').value,
            paper_submission_date: document.getElementById('paper-date').value,
            abstract_deadline: document.getElementById('abstract-date').value || null,
            intimation_date: document.getElementById('intimation-date').value
        };
        
        try {
            const response = await fetch(`${API_BASE}/api/workshops`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                workshopModal.classList.add('hidden');
                workshopForm.reset();
                await loadDeadlines();
            } else {
                const error = await response.json();
                alert(`Error: ${error.error}`);
            }
        } catch (error) {
            console.error('Error adding workshop:', error);
            alert('Failed to add workshop. Please try again.');
        }
    }
    
    async function addConference() {
        const data = {
            name: document.getElementById('conference-name-input').value,
            year: document.getElementById('conference-year').value
        };
        
        try {
            const response = await fetch(`${API_BASE}/api/conferences`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                conferenceModal.classList.add('hidden');
                conferenceForm.reset();
                await loadConferences();
            } else {
                const error = await response.json();
                alert(`Error: ${error.error}`);
            }
        } catch (error) {
            console.error('Error adding conference:', error);
            alert('Failed to add conference. Please try again.');
        }
    }
    
    function formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        const date = parseLocalDate(dateStr);
        if (!date) return 'N/A';
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }
});