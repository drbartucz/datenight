// Tab Switching Logic
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));

    if (tabName === 'search') {
        document.getElementById('btn-search').classList.add('active');
        document.getElementById('view-search').classList.add('active');
    } else if (tabName === 'directory') {
        document.getElementById('btn-directory').classList.add('active');
        document.getElementById('view-directory').classList.add('active');
        loadVenues();
    }
}

// Format URL helper
function formatUrl(url) {
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return 'https://' + url;
    }
    return url;
}

// --- Event Search Section ---
async function performSearch(event) {
    if (event) event.preventDefault();

    const queryInput = document.getElementById('search-date-query');
    const loader = document.getElementById('search-loader');
    const resultsSection = document.getElementById('search-results-section');
    const eventsDisplay = document.getElementById('events-display');
    const dateHeading = document.getElementById('resolved-date-heading');
    const reportLink = document.getElementById('view-report-link');

    loader.style.display = 'flex';
    resultsSection.style.display = 'none';
    eventsDisplay.innerHTML = '';
    reportLink.style.display = 'none';

    try {
        const response = await fetch('/api/events/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date_query: queryInput.value.trim() })
        });

        if (!response.ok) {
            throw new Error(`Search failed: ${response.statusText}`);
        }

        const data = await response.json();
        loader.style.display = 'none';

        dateHeading.textContent = `Events for ${data.resolved_date}`;
        reportLink.href = `/reports/${data.html_filename}`;
        reportLink.style.display = 'inline-flex';

        if (data.events.length === 0) {
            eventsDisplay.innerHTML = `
                <div class="event-card" style="grid-column: 1 / -1; align-items: center; text-align: center; padding: 3rem 1rem;">
                    <h3 class="event-name">No events found for this date.</h3>
                    <p class="event-desc">Try searching for a different date or update your venue source list.</p>
                </div>
            `;
        } else {
            data.events.forEach(ev => {
                const searchFallback = `https://www.google.com/search?q=${encodeURIComponent(ev.name + ' ' + ev.venue + ' Twin Cities')}`;
                const finalLink = ev.link ? formatUrl(ev.link) : searchFallback;
                
                eventsDisplay.innerHTML += `
                    <div class="event-card">
                        <div>
                            <span class="venue-tag">${ev.venue}</span>
                            <h3 class="event-name">${ev.name}</h3>
                            <div class="event-meta">
                                <div>
                                    <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                                    <span>${ev.venue}</span>
                                </div>
                                <div>
                                    <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
                                    <span>${ev.time || 'See details'}</span>
                                </div>
                            </div>
                            <p class="event-desc">${ev.details || 'No additional details provided.'}</p>
                        </div>
                        <a href="${finalLink}" target="_blank" rel="noopener noreferrer" class="card-link">
                            <span>More Info</span>
                            <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                        </a>
                    </div>
                `;
            });
        }

        resultsSection.style.display = 'block';

    } catch (err) {
        loader.style.display = 'none';
        alert(`An error occurred: ${err.message}`);
    }
}

// --- Venue Directory Management ---
async function loadVenues() {
    const venuesDisplay = document.getElementById('venues-display');
    const venuesCount = document.getElementById('venues-count');
    venuesDisplay.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 2rem;">Loading venues...</div>';

    try {
        const response = await fetch('/api/venues');
        const directory = await response.json();
        
        venuesCount.textContent = `${directory.length} Venues loaded`;
        venuesDisplay.innerHTML = '';

        if (directory.length === 0) {
            venuesDisplay.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 2rem;">No venues in the directory.</div>';
            return;
        }

        directory.forEach(v => {
            const formattedUrl = formatUrl(v.url);
            venuesDisplay.innerHTML += `
                <div class="venue-item">
                    <div class="venue-info">
                        <span class="venue-name-txt">${v.name}</span>
                        <a href="${formattedUrl}" target="_blank" rel="noopener noreferrer" class="venue-url-txt">${v.url}</a>
                        <span class="type-badge">${v.type}</span>
                    </div>
                    <button class="delete-btn" onclick="deleteVenue('${v.name}')" title="Delete venue">
                        <svg viewBox="0 0 24 24"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6"/></svg>
                    </button>
                </div>
            `;
        });
    } catch (err) {
        venuesDisplay.innerHTML = `<div style="color: #f87171; text-align: center; padding: 2rem;">Error: ${err.message}</div>`;
    }
}

async function addVenueManually(event) {
    event.preventDefault();

    const nameInput = document.getElementById('manual-name');
    const urlInput = document.getElementById('manual-url');
    const typeInput = document.getElementById('manual-type');

    try {
        const response = await fetch('/api/venues', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: nameInput.value.trim(),
                url: urlInput.value.trim(),
                type: typeInput.value.trim()
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to add venue');
        }

        nameInput.value = '';
        urlInput.value = '';
        typeInput.value = '';
        
        loadVenues();
        alert('Venue added successfully!');

    } catch (err) {
        alert(`Error adding venue: ${err.message}`);
    }
}

async function deleteVenue(name) {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;

    try {
        const response = await fetch(`/api/venues?name=${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete venue');
        }

        loadVenues();
    } catch (err) {
        alert(`Error deleting venue: ${err.message}`);
    }
}

// --- Gemini Discovered Venues ---
let discoveredVenuesList = [];

async function discoverVenuesGemini(event) {
    event.preventDefault();

    const focusInput = document.getElementById('discover-focus');
    const discoverBtn = document.getElementById('discover-btn');
    const loader = document.getElementById('discover-loader');
    const resultsDisplay = document.getElementById('discovered-results-display');

    discoverBtn.disabled = true;
    loader.style.display = 'flex';
    resultsDisplay.style.display = 'none';
    resultsDisplay.innerHTML = '';

    try {
        const response = await fetch('/api/venues/discover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ custom_details: focusInput.value.trim() })
        });

        if (!response.ok) {
            throw new Error('Failed to discover venues');
        }

        discoveredVenuesList = await response.json();
        loader.style.display = 'none';
        discoverBtn.disabled = false;

        if (discoveredVenuesList.length === 0) {
            resultsDisplay.innerHTML = '<div style="color: var(--text-secondary); padding: 1rem; text-align: center;">No new venues discovered.</div>';
        } else {
            renderDiscoveredVenues();
        }
        resultsDisplay.style.display = 'block';

    } catch (err) {
        loader.style.display = 'none';
        discoverBtn.disabled = false;
        alert(`Discovery error: ${err.message}`);
    }
}

function renderDiscoveredVenues() {
    const resultsDisplay = document.getElementById('discovered-results-display');
    resultsDisplay.innerHTML = '<h4 style="margin-bottom: 0.5rem; font-size: 1rem; color: var(--neon-blue);">Discovered Venues:</h4>';

    if (discoveredVenuesList.length === 0) {
        resultsDisplay.style.display = 'none';
        return;
    }

    discoveredVenuesList.forEach((v, index) => {
        resultsDisplay.innerHTML += `
            <div class="discovered-item">
                <div class="venue-info">
                    <span class="venue-name-txt">${v.name}</span>
                    <a href="${formatUrl(v.url)}" target="_blank" rel="noopener noreferrer" class="venue-url-txt">${v.url}</a>
                    <span class="type-badge" style="background: rgba(139, 92, 246, 0.1); color: #c084fc; border-color: rgba(139, 92, 246, 0.2);">${v.type}</span>
                </div>
                <button class="add-discovered-btn" onclick="saveDiscoveredVenue(${index})" title="Add to directory">
                    <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
                </button>
            </div>
        `;
    });
}

async function saveDiscoveredVenue(index) {
    const venue = discoveredVenuesList[index];

    try {
        const response = await fetch('/api/venues', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: venue.name,
                url: venue.url,
                type: venue.type
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to save discovered venue');
        }

        // Remove from local discovered list and re-render
        discoveredVenuesList.splice(index, 1);
        renderDiscoveredVenues();
        
        // Reload directory view
        loadVenues();
        alert(`Successfully added "${venue.name}" to your venues list!`);

    } catch (err) {
        alert(`Error adding venue: ${err.message}`);
    }
}
