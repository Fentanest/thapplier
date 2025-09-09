document.addEventListener('DOMContentLoaded', () => {
    // Buttons
    const runBtn = document.getElementById('run-selected-btn');
    const forceRunBtn = document.getElementById('force-run-btn');
    const saveUidsBtn = document.getElementById('save-uids-btn');
    const saveCouponsBtn = document.getElementById('save-coupons-btn');
    const selectAllUidsBtn = document.getElementById('select-all-btn');
    const deselectAllUidsBtn = document.getElementById('deselect-all-btn');
    const selectAllCouponsBtn = document.getElementById('select-all-coupons-btn');
    const deselectAllCouponsBtn = document.getElementById('deselect-all-coupons-btn');

    // Textareas
    const uidsRaw = document.getElementById('uids-raw');
    const couponsRaw = document.getElementById('coupons-raw');

    // Generic function to handle run logic
    const handleRun = (url, force = false) => {
        const selectedUids = Array.from(document.querySelectorAll('input[name="uids"]:checked'))
            .map(cb => cb.value);
        
        const selectedCoupons = Array.from(document.querySelectorAll('input[name="coupons"]:checked'))
            .map(cb => cb.value);

        if (selectedUids.length === 0) {
            alert('Please select at least one UID to run.');
            return;
        }
        
        // For normal run, coupons are required. For force run, they are not, but we warn the user.
        if (selectedCoupons.length === 0 && !force) {
            alert('Please select at least one Coupon to apply for a normal run.');
            return;
        }

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uids: selectedUids, coupons: selectedCoupons })
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.status === 'success') {
                window.location.href = '/monitoring';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while starting the process.');
        });
    };

    // Run selected UIDs with selected Coupons
    if (runBtn) {
        runBtn.addEventListener('click', () => handleRun('/run', false));
    }

    // Force run selected UIDs
    if (forceRunBtn) {
        forceRunBtn.addEventListener('click', () => handleRun('/force_run', true));
    }

    // Save UIDs
    if (saveUidsBtn) {
        saveUidsBtn.addEventListener('click', () => {
            fetch('/save/uids', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: uidsRaw.value })
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if(data.status === 'success') {
                    window.location.reload();
                }
            });
        });
    }

    // Save Coupons
    if (saveCouponsBtn) {
        saveCouponsBtn.addEventListener('click', () => {
            fetch('/save/coupons', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: couponsRaw.value })
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if(data.status === 'success') {
                    window.location.reload();
                }
            });
        });
    }
    
    // Select/Deselect All UIDs
    if (selectAllUidsBtn) {
        selectAllUidsBtn.addEventListener('click', () => {
            document.querySelectorAll('input[name="uids"]').forEach(cb => cb.checked = true);
        });
    }

    if (deselectAllUidsBtn) {
        deselectAllUidsBtn.addEventListener('click', () => {
            document.querySelectorAll('input[name="uids"]').forEach(cb => cb.checked = false);
        });
    }

    // Select/Deselect All Coupons
    if (selectAllCouponsBtn) {
        selectAllCouponsBtn.addEventListener('click', () => {
            document.querySelectorAll('input[name="coupons"]').forEach(cb => cb.checked = true);
        });
    }

    if (deselectAllCouponsBtn) {
        deselectAllCouponsBtn.addEventListener('click', () => {
            document.querySelectorAll('input[name="coupons"]').forEach(cb => cb.checked = false);
        });
    }

    // --- Deletion Logic ---

    // Delete Coupon
    const deleteCouponBtns = document.querySelectorAll('.delete-coupon-btn');
    deleteCouponBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const couponName = e.target.dataset.couponName;
            if (confirm(`Are you sure you want to delete the coupon "${couponName}"?`)) {
                fetch('/delete_coupon', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ coupon_name: couponName })
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.status === 'success') {
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while deleting the coupon.');
                });
            }
        });
    });

    // Delete UID
    const deleteUidBtns = document.querySelectorAll('.delete-uid-btn');
    deleteUidBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const uid = e.target.dataset.uid;
            if (confirm(`Are you sure you want to delete the UID "${uid}"?`)) {
                fetch('/delete_uid', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uid: uid })
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.status === 'success') {
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while deleting the UID.');
                });
            }
        });
    });
});
