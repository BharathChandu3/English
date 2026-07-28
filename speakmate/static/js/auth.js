/* SpeakMate AI Auth Validation script */

document.addEventListener("DOMContentLoaded", () => {
    initAuthValidation();
});

function initAuthValidation() {
    const registerForm = document.getElementById("registerForm");
    const loginForm = document.getElementById("loginForm");
    
    if (registerForm) {
        registerForm.addEventListener("submit", (e) => {
            const username = document.getElementById("username").value.trim();
            const email = document.getElementById("email").value.trim();
            const password = document.getElementById("password").value;
            
            if (username.length < 3) {
                e.preventDefault();
                alert("Username must be at least 3 characters long.");
                return;
            }
            
            if (password.length < 6) {
                e.preventDefault();
                alert("Password must be at least 6 characters long.");
                return;
            }
            
            // Basic email match regex
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                e.preventDefault();
                alert("Please enter a valid email address.");
                return;
            }
        });
    }
    
    if (loginForm) {
        loginForm.addEventListener("submit", (e) => {
            const username = document.getElementById("username").value.trim();
            const password = document.getElementById("password").value;
            
            if (!username || !password) {
                e.preventDefault();
                alert("Please fill in both fields.");
            }
        });
    }
}
