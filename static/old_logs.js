document.addEventListener('DOMContentLoaded', () => {
    const logFilesList = document.getElementById('log-files-list');
    const couponLogFilesList = document.getElementById('coupon-log-files-list');
    const logFilename = document.getElementById('log-filename');
    const logContent = document.getElementById('log-content');

    function fetchLogContent(type, file) {
        fetch(`/api/log-content?type=${type}&file=${file}`)
            .then(response => response.json())
            .then(data => {
                logFilename.textContent = data.filename;
                logContent.textContent = data.content;
            })
            .catch(error => {
                console.error('Error fetching log content:', error);
                logContent.textContent = 'Error loading log file.';
            });
    }

    function populateLogList(listElement, files, type) {
        if (!files || files.length === 0) {
            listElement.innerHTML = '<li>No logs found.</li>';
            return;
        }
        listElement.innerHTML = '';
        files.forEach(file => {
            const listItem = document.createElement('li');
            const link = document.createElement('a');
            link.href = '#';
            link.textContent = file;
            link.addEventListener('click', (e) => {
                e.preventDefault();
                // Remove active class from all other links
                document.querySelectorAll('.log-list a.active').forEach(el => el.classList.remove('active'));
                // Add active class to the clicked link
                link.classList.add('active');
                fetchLogContent(type, file);
            });
            listItem.appendChild(link);
            listElement.appendChild(listItem);
        });
    }

    fetch('/api/logs')
        .then(response => response.json())
        .then(data => {
            populateLogList(logFilesList, data.logs, 'log');
            populateLogList(couponLogFilesList, data.coupon_logs, 'coupon');
        })
        .catch(error => {
            console.error('Error fetching log list:', error);
            logFilesList.innerHTML = '<li>Error loading logs.</li>';
            couponLogFilesList.innerHTML = '<li>Error loading logs.</li>';
        });
});
