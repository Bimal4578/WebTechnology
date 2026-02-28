// Custom JS for Lumina Clothing

document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-danger)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Password matcher validation on register form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        const password = document.getElementById('password');
        const confirm_password = document.getElementById('confirm_password');

        function validatePassword() {
            if(password.value != confirm_password.value) {
                confirm_password.setCustomValidity("Passwords Don't Match");
            } else {
                confirm_password.setCustomValidity('');
            }
        }

        password.addEventListener('change', validatePassword);
        confirm_password.addEventListener('keyup', validatePassword);
    }
});
