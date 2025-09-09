document.addEventListener('DOMContentLoaded', () => {
    const logOutput = document.getElementById('log-output');
    const logContainer = document.getElementById('log-container');

    function colorizeLog(line) {
        // Colorize UID
        line = line.replace(/(UID: \S+)/g, '<span class="log-uid">$1</span>');
        // Colorize thread identifier
        line = line.replace(/(\[Thread-\d+\])/g, '<span class="log-thread">$1</span>');
        return line;
    }

    function connectEventSource() {
        const eventSource = new EventSource('/stream-all-logs');

        eventSource.onmessage = function(event) {
            const newLogEntry = document.createElement('div');
            newLogEntry.innerHTML = colorizeLog(event.data);
            logOutput.appendChild(newLogEntry);
            // Auto-scroll to the bottom
            logContainer.scrollTop = logContainer.scrollHeight;
        };

        eventSource.onerror = function(err) {
            console.error('EventSource failed:', err);
            eventSource.close();
            // Optional: try to reconnect after a delay
            setTimeout(connectEventSource, 5000);
        };
    }

    connectEventSource();
});
