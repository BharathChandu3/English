/* SpeakMate AI Profile Settings JS */

document.addEventListener("DOMContentLoaded", () => {
    initProfileActions();
});

function initProfileActions() {
    const profileForm = document.getElementById("profileUpdateForm");
    const resetMemoryBtn = document.getElementById("resetMemoryBtn");
    
    if (profileForm) {
        profileForm.addEventListener("submit", (e) => {
            e.preventDefault();
            
            const level = document.getElementById("profileLevel").value;
            const focus = document.getElementById("profileFocus").value;
            
            const submitBtn = profileForm.querySelector("button[type='submit']");
            const origText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...`;
            
            fetch("/api/profile/update", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    target_level: level,
                    focus_area: focus
                })
            })
            .then(res => res.json())
            .then(data => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-check"></i> Saved successfully`;
                setTimeout(() => {
                    submitBtn.innerHTML = origText;
                }, 2000);
            })
            .catch(err => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origText;
                alert("Failed to update profile settings.");
                console.error("Profile update error: ", err);
            });
        });
    }
    
    if (resetMemoryBtn) {
        resetMemoryBtn.addEventListener("click", () => {
            if (!confirm("Are you sure you want to reset all conversational tutor history and grammar memory tags? This action is irreversible.")) {
                return;
            }
            
            const origText = resetMemoryBtn.innerHTML;
            resetMemoryBtn.disabled = true;
            resetMemoryBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Resetting...`;
            
            fetch("/api/settings/reset", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
            .then(res => res.json())
            .then(data => {
                resetMemoryBtn.disabled = false;
                resetMemoryBtn.innerHTML = `<i class="fa-solid fa-check"></i> Memory Flushed`;
                setTimeout(() => {
                    resetMemoryBtn.innerHTML = origText;
                    window.location.reload();
                }, 1500);
            })
            .catch(err => {
                resetMemoryBtn.disabled = false;
                resetMemoryBtn.innerHTML = origText;
                alert("Failed to reset memory.");
                console.error("Memory reset error: ", err);
            });
        });
    }
}
