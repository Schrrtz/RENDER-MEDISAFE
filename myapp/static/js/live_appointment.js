// Live Appointment Panel JavaScript
// Optimized for performance with minimal DOM operations

(function() {
    'use strict';
    
    // Cache DOM elements for better performance
    const DOMCache = {
        details: null,
        emptyState: null,
        patientProfile: null,
        emptyPatientProfile: null,
        profilePictureImg: null,
        profilePictureIcon: null,
        elements: {}
    };
    
    // Initialize DOM cache
    function initDOMCache() {
        DOMCache.details = document.getElementById('details');
        DOMCache.emptyState = document.getElementById('emptyState');
        DOMCache.patientProfile = document.getElementById('patientProfile');
        DOMCache.emptyPatientProfile = document.getElementById('emptyPatientProfile');
        DOMCache.profilePictureImg = document.getElementById('profilePicture');
        DOMCache.profilePictureIcon = document.getElementById('profilePictureIcon');
        
        // Cache frequently used elements
        const elementIds = [
            'detailId', 'detailName', 'detailDOB', 'detailGender', 
            'detailContact', 'ecPhone', 'appointmentTime', 'appointmentType',
            'appointmentDate', 'appointmentStatus', 'appointmentNotes',
            'meetingLinkSection', 'meetingLink', 'bpVal', 'hrVal', 'tempVal'
        ];
        
        elementIds.forEach(id => {
            DOMCache.elements[id] = document.getElementById(id);
        });
    }
    
    // Optimized showDetailsFromElement function
    window.showDetailsFromElement = function(el) {
        if (!el || !el.dataset) return;
        
        const data = el.dataset;
        const id = data.id || data.patientId || el.getAttribute('data-id') || '';
        const first = data.first || data.firstname || '';
        const middle = data.middle || '';
        const last = data.last || data.lastname || '';
        const name = (first + (middle ? ' ' + middle : '') + ' ' + last).trim();
        
        // Batch DOM updates for better performance
        requestAnimationFrame(() => {
            updatePatientInfo({
                id,
                name,
                dob: data.dob || data.dobRaw || '',
                gender: data.gender || '',
                contact: data.contact || '',
                ecNumber: data.ecNumber || data.ec_phone || '',
                profilePicture: data.profilePicture || ''
            });
            
            updateAppointmentInfo({
                time: data.appointmentTime || '',
                type: data.appointmentType || '',
                date: data.appointmentDate || '',
                status: data.appointmentStatus || '',
                notes: data.appointmentNotes || '',
                meetingLink: data.appointmentMeetingLink || ''
            });
            
            updateVitals();
            showDetailsPanel();
        });
    };
    
    // Batch patient info updates
    function updatePatientInfo(patient) {
        if (DOMCache.elements.detailId) DOMCache.elements.detailId.textContent = patient.id;
        if (DOMCache.elements.detailName) DOMCache.elements.detailName.textContent = patient.name;
        if (DOMCache.elements.detailDOB) DOMCache.elements.detailDOB.textContent = patient.dob || '—';
        if (DOMCache.elements.detailGender) DOMCache.elements.detailGender.textContent = patient.gender || '—';
        if (DOMCache.elements.detailContact) DOMCache.elements.detailContact.textContent = patient.contact;
        if (DOMCache.elements.ecPhone) DOMCache.elements.ecPhone.textContent = patient.ecNumber;
        
        // Handle profile picture efficiently
        if (patient.profilePicture && DOMCache.profilePictureImg && DOMCache.profilePictureIcon) {
            DOMCache.profilePictureImg.src = patient.profilePicture;
            DOMCache.profilePictureImg.style.display = 'block';
            DOMCache.profilePictureIcon.style.display = 'none';
        } else if (DOMCache.profilePictureImg && DOMCache.profilePictureIcon) {
            DOMCache.profilePictureImg.style.display = 'none';
            DOMCache.profilePictureIcon.style.display = 'block';
        }
    }
    
    // Batch appointment info updates
    function updateAppointmentInfo(appointment) {
        if (DOMCache.elements.appointmentTime) DOMCache.elements.appointmentTime.textContent = appointment.time || '—';
        if (DOMCache.elements.appointmentType) DOMCache.elements.appointmentType.textContent = appointment.type || '—';
        if (DOMCache.elements.appointmentDate) DOMCache.elements.appointmentDate.textContent = appointment.date || '—';
        if (DOMCache.elements.appointmentStatus) DOMCache.elements.appointmentStatus.textContent = appointment.status || '—';
        if (DOMCache.elements.appointmentNotes) DOMCache.elements.appointmentNotes.textContent = appointment.notes || 'No notes available';
        
        // Handle meeting link
        if (DOMCache.elements.meetingLinkSection && DOMCache.elements.meetingLink) {
            if (appointment.meetingLink) {
                DOMCache.elements.meetingLink.href = appointment.meetingLink;
                DOMCache.elements.meetingLinkSection.style.display = 'block';
            } else {
                DOMCache.elements.meetingLinkSection.style.display = 'none';
            }
        }
    }
    
    // Update vitals with simulated data
    function updateVitals() {
        if (DOMCache.elements.bpVal) {
            DOMCache.elements.bpVal.textContent = Math.floor(110 + Math.random() * 20) + '/' + Math.floor(70 + Math.random() * 12);
        }
        if (DOMCache.elements.hrVal) {
            DOMCache.elements.hrVal.textContent = Math.floor(60 + Math.random() * 30) + ' bpm';
        }
        if (DOMCache.elements.tempVal) {
            DOMCache.elements.tempVal.textContent = (36 + Math.random() * 1.6).toFixed(1) + ' °C';
        }
    }
    
    // Show details panel
    function showDetailsPanel() {
        if (DOMCache.details) {
            DOMCache.details.style.display = 'block';
            DOMCache.details.setAttribute('aria-hidden', 'false');
        }
        if (DOMCache.emptyState) {
            DOMCache.emptyState.style.display = 'none';
        }
        if (DOMCache.patientProfile && DOMCache.emptyPatientProfile) {
            DOMCache.patientProfile.style.display = 'block';
            DOMCache.emptyPatientProfile.style.display = 'none';
        }
    }
    
    // Debounced notification system
    const notificationQueue = [];
    let notificationTimeout = null;
    
    function showNotification(message, type = 'info') {
        notificationQueue.push({ message, type });
        
        if (!notificationTimeout) {
            notificationTimeout = setTimeout(processNotificationQueue, 100);
        }
    }
    
    function processNotificationQueue() {
        if (notificationQueue.length === 0) {
            notificationTimeout = null;
            return;
        }
        
        const { message, type } = notificationQueue.shift();
        createNotification(message, type);
        
        if (notificationQueue.length > 0) {
            notificationTimeout = setTimeout(processNotificationQueue, 100);
        } else {
            notificationTimeout = null;
        }
    }
    
    function createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            animation: slideInRight 0.3s ease-out;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-in forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    // Utility functions
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Initialize when DOM is ready
    function init() {
        initDOMCache();
        console.log('Live Appointment Panel initialized');
    }
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Expose functions globally
    window.showNotification = showNotification;
    window.getCookie = getCookie;
    window.debounce = debounce;
    
})();

