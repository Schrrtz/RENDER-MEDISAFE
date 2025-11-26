// Enhanced consultation filters and sorting
function filterConsultations() {
    const statusFilter = document.getElementById('status-filter').value;
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    const searchInput = document.getElementById('search-input')?.value.toLowerCase();
    const consultationTypeFilter = document.getElementById('consultation-type-filter').value;
    const rows = document.querySelectorAll('table tbody tr');

    rows.forEach(row => {
        if (!row.querySelector('td')) return;

        // Get cell values
        const date = row.querySelector('td:nth-child(5)').textContent.trim();
        const status = row.querySelector('td:nth-child(8)').textContent.trim().toLowerCase();
        const type = row.querySelector('td:nth-child(4)').textContent.trim();
        const rowText = row.textContent.toLowerCase();

        // Check each filter condition
        const matchesStatus = statusFilter === 'all' || status.includes(statusFilter.toLowerCase());
        const matchesDateRange = (!startDate || new Date(date) >= new Date(startDate)) && 
                                (!endDate || new Date(date) <= new Date(endDate));
        const matchesType = consultationTypeFilter === 'all' || type === consultationTypeFilter;
        const matchesSearch = !searchInput || rowText.includes(searchInput);

        // Show/hide row based on all filters
        row.style.display = (matchesStatus && matchesDateRange && matchesType && matchesSearch) ? '' : 'none';
    });

    // Update visible count
    const visibleRows = document.querySelectorAll('table tbody tr[style=""]').length;
    updateVisibleCount(visibleRows);
}

function updateVisibleCount(count) {
    const feedback = document.getElementById('filter-feedback');
    if (feedback) {
        const totalRows = document.querySelectorAll('table tbody tr:not([data-empty-message])').length;
        feedback.innerHTML = `
            <span class="font-medium">Showing ${count} of ${totalRows} appointment${totalRows !== 1 ? 's' : ''}</span>
            ${count < totalRows ? `
                <span class="text-gray-500 ml-1">(${totalRows - count} filtered out)</span>
            ` : ''}
        `;
    }
}

function clearAllFilters() {
    // Reset all filter inputs
    const statusFilter = document.getElementById('status-filter');
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    const searchInput = document.getElementById('search-input');
    const consultationTypeFilter = document.getElementById('consultation-type-filter');
    const sortSelect = document.getElementById('sort-select');

    if (statusFilter) statusFilter.value = 'all';
    if (startDate) startDate.value = '';
    if (endDate) endDate.value = '';
    if (searchInput) searchInput.value = '';
    if (consultationTypeFilter) consultationTypeFilter.value = 'all';
    if (sortSelect) sortSelect.value = 'date-asc';

    // Reapply filters to show all rows
    filterConsultations();

    // Update sort icons
    document.querySelectorAll('th[data-sort] i.fas').forEach(icon => {
        icon.className = 'fas fa-sort text-gray-400';
    });
}

// Initialize filters and feedback element
document.addEventListener('DOMContentLoaded', function() {
    // Initialize feedback element
    const filterContainer = document.querySelector('.filters-container');
    if (filterContainer) {
        const feedback = document.createElement('div');
        feedback.id = 'filter-feedback';
        feedback.className = 'text-sm text-gray-600 mt-2';
        filterContainer.appendChild(feedback);
        
        // Initial count
        const totalRows = document.querySelectorAll('table tbody tr:not([data-empty-message])').length;
        updateVisibleCount(totalRows);
    }

    // Add event listeners to all filter elements
    const filterElements = [
        'status-filter',
        'start-date',
        'end-date',
        'search-input',
        'consultation-type-filter'
    ];

    filterElements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            if (element.type === 'text') {
                element.addEventListener('input', filterConsultations);
            } else {
                element.addEventListener('change', filterConsultations);
            }
        }
    });

    // Add sort functionality to column headers
    document.querySelectorAll('th[data-sort]').forEach(header => {
        header.addEventListener('click', () => {
            const columnIndex = parseInt(header.dataset.sort);
            const isNumeric = header.dataset.numeric === 'true';
            sortTable(columnIndex, isNumeric);
        });
    });
});

// Handle sorting with visual feedback
function sortTable(columnIndex, numeric = false) {
    const table = document.querySelector('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr:not([data-empty-message])'));
    const th = table.querySelector(`th[data-sort="${columnIndex}"]`);
    const icon = th.querySelector('i.fas');
    
    // Toggle sort direction
    let sortOrder = th.dataset.sortOrder === 'asc' ? -1 : 1;
    th.dataset.sortOrder = sortOrder === 1 ? 'asc' : 'desc';

    // Update sort icons
    document.querySelectorAll('th[data-sort] i.fas').forEach(i => {
        i.className = 'fas fa-sort text-gray-400';
    });
    icon.className = `fas fa-sort-${sortOrder === 1 ? 'up' : 'down'} text-healthcare-blue`;

    rows.sort((a, b) => {
        const aValue = a.children[columnIndex].textContent.trim();
        const bValue = b.children[columnIndex].textContent.trim();

        if (numeric) {
            return sortOrder * (parseFloat(aValue) - parseFloat(bValue));
        } else if (columnIndex === 4) { // Date column
            return sortOrder * (new Date(aValue) - new Date(bValue));
        } else {
            return sortOrder * aValue.localeCompare(bValue);
        }
    });

    // Reorder rows
    rows.forEach(row => tbody.appendChild(row));
    
    // Reapply filters after sorting
    filterConsultations();
}