// Function to switch between tabs
function switchTab(tabName) {
    // Hide all sections first
    document.getElementById('patient-records-section').style.display = 'none';
    document.getElementById('lab-results-section').style.display = 'none';
    document.getElementById('booked-services-section').style.display = 'none';
    document.getElementById('patient-prescriptions-section').style.display = 'none';

    // Remove active state from all tab buttons
    document.getElementById('patient-records-tab').classList.remove('border-healthcare-blue', 'text-healthcare-blue');
    document.getElementById('lab-results-tab').classList.remove('border-healthcare-blue', 'text-healthcare-blue');
    document.getElementById('booked-services-tab').classList.remove('border-healthcare-blue', 'text-healthcare-blue');
    document.getElementById('patient-prescriptions-tab').classList.remove('border-healthcare-blue', 'text-healthcare-blue');

    // Add inactive state to all tab buttons
    document.getElementById('patient-records-tab').classList.add('border-transparent', 'text-gray-500');
    document.getElementById('lab-results-tab').classList.add('border-transparent', 'text-gray-500');
    document.getElementById('booked-services-tab').classList.add('border-transparent', 'text-gray-500');
    document.getElementById('patient-prescriptions-tab').classList.add('border-transparent', 'text-gray-500');

    // Show selected section
    document.getElementById(`${tabName}-section`).style.display = 'block';
    
    // Add active state to selected tab
    document.getElementById(`${tabName}-tab`).classList.remove('border-transparent', 'text-gray-500');
    document.getElementById(`${tabName}-tab`).classList.add('border-healthcare-blue', 'text-healthcare-blue');
}

// Initialize tab state on page load
document.addEventListener('DOMContentLoaded', function() {
    // Show patient records tab by default
    switchTab('patient-records');
});