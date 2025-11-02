function updateActivityTypes(preserveSelected) {
    console.log('updateActivityTypes called');
    const employeeSelect = document.getElementById('employee_id');
    const activitySelect = document.getElementById('intervention_type');
    
    if (!employeeSelect || !activitySelect) {
        console.error('Required select elements not found:', {
            employeeSelect: !!employeeSelect,
            activitySelect: !!activitySelect
        });
        return;
    }

    // Store the currently selected value if needed
    const currentValue = preserveSelected ? activitySelect.value : null;
    
    // Clear current options
    activitySelect.innerHTML = '<option value="">Select Activity Type</option>';
    
    // If no employee is selected, return
    if (!employeeSelect.value) {
        console.log('No employee selected');
        return;
    }

    console.log('Fetching activities for employee:', employeeSelect.value);
    
    // Fetch activities based on selected employee
    fetch(`/interventions/get_activities/${employeeSelect.value}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('Response received:', response);
            return response.json();
        })
        .then(activities => {
            console.log('Activities received:', activities);
            activities.forEach(activity => {
                const option = document.createElement('option');
                option.value = activity.name;
                option.textContent = activity.name;
                activitySelect.appendChild(option);
                
                // If this is the previously selected value, select it again
                if (currentValue === activity.name) {
                    option.selected = true;
                }
            });
            console.log('Activity options updated');
        })
        .catch(error => {
            console.error('Error fetching activities:', error);
            // Show an error message in the activity select
            activitySelect.innerHTML = '<option value="">Error loading activities</option>';
        });
}

document.addEventListener('DOMContentLoaded', function() {
    const employeeSelect = document.getElementById('employee_id');
    if (employeeSelect) {
        // For updates, we want to preserve the selected value on initial load
        const isUpdateForm = window.location.pathname.includes('/update/');
        
        employeeSelect.addEventListener('change', () => updateActivityTypes(false));
        
        // Initial update if employee is pre-selected
        if (employeeSelect.value) {
            updateActivityTypes(isUpdateForm);
        }
    }
});