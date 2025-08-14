function setupDurationCalculation(startId, endId, durationId) {
    function calculateDuration() {
        const start = document.getElementById(startId).value;
        const end = document.getElementById(endId).value;
        const durationField = document.getElementById(durationId);
        if (start && end) {
            const [startHour, startMin] = start.split(':').map(Number);
            const [endHour, endMin] = end.split(':').map(Number);
            let startDate = new Date(0, 0, 0, startHour, startMin, 0);
            let endDate = new Date(0, 0, 0, endHour, endMin, 0);
            let diff = (endDate - startDate) / (1000 * 60 * 60);
            if (diff < 0) diff += 24;
            durationField.value = diff.toFixed(2);
        } else {
            durationField.value = '';
        }
    }
    document.getElementById(startId).addEventListener('input', calculateDuration);
    document.getElementById(endId).addEventListener('input', calculateDuration);
}