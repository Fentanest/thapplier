document.addEventListener('DOMContentLoaded', function() {

    const sessionsContainer = document.getElementById('monitoring-grid');
    const seleniumHubUrl = sessionsContainer.dataset.seleniumHubUrl || '';

    function createSessionCard(key, session) {
        const card = document.createElement('div');
        card.className = 'session-card'; 
        card.id = `session-card-${key}`;

        let statusBadge;
        switch (session.status) {
            case 'Running':
                statusBadge = '<span class="badge bg-primary">Running</span>';
                break;
            case 'Queued':
                statusBadge = '<span class="badge bg-secondary">Queued</span>';
                break;
            case 'Finished':
                statusBadge = '<span class="badge bg-success">Finished</span>';
                break;
            case 'Error':
                statusBadge = '<span class="badge bg-danger">Error</span>';
                break;
            default:
                statusBadge = `<span class="badge bg-info">${session.status}</span>`;
        }

        const vncButton = (session.status === 'Running' && session.session_id)
            ? `<a href="${seleniumHubUrl}/ui/#/session/${session.session_id}" target="_blank" class="btn btn-sm btn-outline-primary float-end">Go to Session</a>`
            : '';

        card.innerHTML = `
            <div class="card h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="card-title mb-0" title="${key}">${session.display_name}</h6>
                    ${vncButton}
                </div>
                <div class="card-body">
                    <p class="card-text mb-1"><strong>Status:</strong> ${statusBadge}</p>
                    <p class="card-text text-muted" style="font-size: 0.8rem;">${session.log_preview}</p>
                </div>
            </div>
        `;
        return card;
    }

    async function fetchAndUpdateStatus() {
        try {
            const response = await fetch('/status');
            if (!response.ok) {
                sessionsContainer.innerHTML = '<p class="text-center text-danger">Error fetching status.</p>';
                return;
            }
            const data = await response.json();
            
            const activeSessions = Object.entries(data).filter(([key, session]) => {
                return session.status !== 'Finished' && session.status !== 'Error';
            });

            sessionsContainer.innerHTML = '';

            if (activeSessions.length === 0) {
                sessionsContainer.innerHTML = '<p class="text-center text-muted">No active sessions.</p>';
                return;
            }

            for (const [key, session] of activeSessions) {
                const card = createSessionCard(key, session);
                sessionsContainer.appendChild(card);
            }

        } catch (error) {
            console.error('Error fetching status:', error);
            sessionsContainer.innerHTML = '<p class="text-center text-danger">Could not connect to server.</p>';
        }
    }

    fetchAndUpdateStatus();
    setInterval(fetchAndUpdateStatus, 2000);
});