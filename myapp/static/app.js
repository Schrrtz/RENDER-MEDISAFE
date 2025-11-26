// MediSafe+ Application JavaScript
// This file contains common JavaScript functionality for the healthcare management system

console.log('MediSafe+ Application loaded successfully');

// API handling functions
const HealthcareAPI = {
    async login(userData) {
        try {
            const response = await fetch('/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            if (response.ok) {
                // Redirect based on the response
                window.location.href = data.redirect;
            } else {
                alert(data.message || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('An error occurred during login. Please try again.');
        }
    },

    async register(userData) {
        console.log('Starting registration with userData:', userData);
        try {
            // Get CSRF token
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

            const csrfToken = getCookie('csrftoken');
            console.log('CSRF Token:', csrfToken ? 'Found' : 'Not found');

            const response = await fetch('/signup/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || ''
                },
                body: JSON.stringify(userData),
                credentials: 'same-origin'
            });

            console.log('Response status:', response.status);

            // Get response text first to check if it's JSON
            const responseText = await response.text();
            console.log('Response text:', responseText.substring(0, 200));

            let data;
            try {
                data = JSON.parse(responseText);
            } catch (e) {
                console.error('Failed to parse JSON response:', e);
                console.error('Full response text:', responseText);
                throw new Error('Server returned invalid response: ' + responseText.substring(0, 100));
            }

            console.log('Parsed response data:', data);

            if (!response.ok) {
                throw new Error(data.message || 'Registration failed');
            }

            // Show success message
            const successMessage = document.createElement('div');
            successMessage.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 ease-in-out z-50';
            successMessage.innerHTML = `
                <div class="flex items-center">
                    <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <span>${data.message || 'Account created successfully! Logging you in...'}</span>
                </div>`;
            document.body.appendChild(successMessage);

            // Clear the form
            const signupForm = document.getElementById('signupForm');
            if (signupForm) {
                signupForm.reset();
            }

            // Hide the signup modal
            const signupModal = document.getElementById('signupModal');
            if (signupModal) {
                signupModal.style.opacity = '0';
                signupModal.style.transition = 'opacity 0.3s ease-out';
                setTimeout(() => {
                    signupModal.classList.add('hidden');
                    signupModal.classList.remove('flex');
                }, 300);
            }

            // If there's a redirect URL, navigate to it after a short delay
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }

            return true;
        } catch (error) {
            console.error('Registration error:', error);
            throw new Error(error.message || 'An error occurred during registration');
        }
    }
};

// Small spinner helpers for buttons
function createButtonSpinner(dark) {
    const s = document.createElement('span');
    s.className = 'btn-spinner' + (dark ? ' dark' : '');
    return s;
}

function showButtonSpinner(btn, dark) {
    if (!btn) return;
    if (btn._ms_spinner) return; // already shown
    btn._ms_spinner = createButtonSpinner(dark);
    // store original disabled state + set disabled
    try { btn._ms_prev_disabled = btn.disabled; } catch(e){}
    btn.disabled = true;
    // append spinner
    btn.appendChild(btn._ms_spinner);
}

function hideButtonSpinner(btn) {
    if (!btn) return;
    if (btn._ms_spinner) {
        try { btn.removeChild(btn._ms_spinner); } catch(e){}
        btn._ms_spinner = null;
    }
    try { if (typeof btn._ms_prev_disabled !== 'undefined') btn.disabled = btn._ms_prev_disabled; else btn.disabled = false; } catch(e){}
}

// Expose to global for templates to use
window.showButtonSpinner = showButtonSpinner;
window.hideButtonSpinner = hideButtonSpinner;

// Common utility functions
const HealthcareApp = {
    // Initialize the application
    init: function() {
        console.log('Initializing MediSafe+ Application...');
        this.setupEventListeners();
        this.checkAdminStatus();
    },

    // Setup common event listeners
    setupEventListeners: function() {
        // Add event listeners for login and signup forms
        const loginForm = document.getElementById('loginForm');
        const signupForm = document.getElementById('signupForm');

        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = loginForm.querySelector('input[type="text"]').value;
                const password = loginForm.querySelector('input[type="password"]').value;

                if (username && password) {
                    await HealthcareAPI.login({ username, password });
                } else {
                    alert('Please fill in all required fields');
                }
            });
        }

        if (signupForm) {
            // Skip attaching the default signup listener if a custom handler is present
            try {
                if (signupForm.getAttribute && signupForm.getAttribute('data-custom-handler') === '1') {
                    console.log('Custom signup handler detected; skipping default signup listener.');
                } else {
                    signupForm.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const form = e.target;
                        const userData = {
                            first_name: form.querySelector('input[name="first_name"]').value.trim(),
                            last_name: form.querySelector('input[name="last_name"]').value.trim(),
                            username: form.querySelector('input[name="username"]').value.trim(),
                            email: form.querySelector('input[name="email"]').value.trim(),
                            password: form.querySelector('input[name="password"]').value,
                            role: 'patient'
                        };

                        // Check if all required fields are filled
                        if (!userData.first_name || !userData.last_name || !userData.username || !userData.email || !userData.password) {
                            alert('Please fill in all required fields');
                            return;
                        }
                        
                        try {
                            const result = await HealthcareAPI.register(userData);
                            if (result === true) {
                                console.log('Registration successful');
                            }
                        } catch (error) {
                            // Create error message div
                            const errorMessage = document.createElement('div');
                            errorMessage.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 ease-in-out z-50';
                            errorMessage.innerHTML = `
                                <div class="flex items-center">
                                    <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                    <span>${error.message || 'Registration failed. Please try again.'}</span>
                                </div>`;
                            document.body.appendChild(errorMessage);

                            // Remove error message after 5 seconds
                            setTimeout(() => {
                                errorMessage.style.opacity = '0';
                                setTimeout(() => {
                                    document.body.removeChild(errorMessage);
                                }, 500);
                            }, 5000);
                            return;
                        }
                    });
                }
            } catch (err) {
                console.warn('Error while checking for custom signup handler:', err);
            }
        }
    },

    // Check admin status from localStorage
    checkAdminStatus: function() {
        try {
            const isAdmin = localStorage.getItem('isAdmin') === 'true';
            if (isAdmin) {
                console.log('Admin user detected');
                // Show admin-only elements
                const adminElements = document.querySelectorAll('.std-analytics');
                adminElements.forEach(element => {
                    element.style.display = 'inline-block';
                });
            }
        } catch (e) {
            console.log('Could not check admin status:', e);
        }
    },

    // Show notification
    showNotification: function(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
        // You can implement a toast notification system here
    },

    // Format date
    formatDate: function(date) {
        return new Date(date).toLocaleDateString();
    },

    // Validate form
    validateForm: function(formElement) {
        const inputs = formElement.querySelectorAll('input[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                input.style.borderColor = '#DC2626';
            } else {
                input.style.borderColor = '';
            }
        });
        
        return isValid;
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    HealthcareApp.init();
});

// Export for use in other scripts
window.HealthcareApp = HealthcareApp;
