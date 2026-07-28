/* SpeakMate AI Shared Javascript */

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initMobileSidebar();
    initFeedbackDrawer();
});

// Theme Management (Persist in LocalStorage)
function initTheme() {
    const themeToggle = document.getElementById("themeToggle");
    if (!themeToggle) return;

    const currentTheme = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", currentTheme);
    updateThemeIcon(currentTheme);

    themeToggle.addEventListener("click", () => {
        const activeTheme = document.documentElement.getAttribute("data-theme");
        const nextTheme = activeTheme === "dark" ? "light" : "dark";
        
        document.documentElement.setAttribute("data-theme", nextTheme);
        localStorage.setItem("theme", nextTheme);
        updateThemeIcon(nextTheme);
    });
}

function updateThemeIcon(theme) {
    const themeToggle = document.getElementById("themeToggle");
    if (!themeToggle) return;
    
    if (theme === "dark") {
        themeToggle.innerHTML = `<i class="fa-solid fa-sun"></i>`;
    } else {
        themeToggle.innerHTML = `<i class="fa-solid fa-moon"></i>`;
    }
}

// Collapsible Mobile Navigation Drawer
function initMobileSidebar() {
    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("appSidebar");
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            sidebar.classList.toggle("open");
        });

        // Close sidebar on document clicks
        document.addEventListener("click", (e) => {
            if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && e.target !== menuToggle) {
                sidebar.classList.remove("open");
            }
        });
    }
}

// Feedback Drawer Control
function initFeedbackDrawer() {
    const closeBtn = document.getElementById("closeFeedbackDrawer");
    const drawer = document.getElementById("feedbackDrawer");
    
    if (closeBtn && drawer) {
        closeBtn.addEventListener("click", () => {
            drawer.classList.remove("open");
        });
    }
}

// Global Text-to-Speech (TTS) Browser Speech Synthesis helper
window.speakText = function(text) {
    if (!('speechSynthesis' in window)) {
        console.warn("Speech Synthesis is not supported in this browser.");
        return;
    }
    
    // Stop any ongoing voice synthesis
    window.speechSynthesis.cancel();
    
    // Clean markdown stars from string to pronounce neatly
    const cleanText = text.replace(/[*#_`~]/g, '');
    
    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    // Attempt to pick a natural-sounding English voice
    let voices = window.speechSynthesis.getVoices();
    
    function setBestVoice() {
        voices = window.speechSynthesis.getVoices();
        // Look for Google US English or standard EN voices
        const englishVoice = voices.find(voice => voice.lang.includes("en-US") || voice.lang.includes("en-GB")) || voices[0];
        if (englishVoice) {
            utterance.voice = englishVoice;
        }
    }
    
    setBestVoice();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = setBestVoice;
    }
    
    // Configure voice tone (Default/Saved preferences)
    utterance.rate = parseFloat(localStorage.getItem("tts_rate") || "1.0");
    utterance.pitch = parseFloat(localStorage.getItem("tts_pitch") || "1.0");
    
    window.speechSynthesis.speak(utterance);
};
