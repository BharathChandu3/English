/* SpeakMate AI Timed Speaking Challenges controller */

let challengeTimerInterval = null;
let challengeTimeLimit = 60;
let challengeRecording = false;
let activeChallengeType = "";
let activeChallengeTitle = "";
let activeChallengeInstructions = "";

document.addEventListener("DOMContentLoaded", () => {
    initChallengeSpeech();
});

window.startChallenge = function(type) {
    activeChallengeType = type;
    
    // UI Layout updates
    document.getElementById("challengePlaceholder").style.display = "none";
    
    const workspace = document.getElementById("challengeWorkspace");
    workspace.style.display = "block";
    
    // Show loadings
    document.getElementById("challengeTitle").innerText = "Generating Challenge details...";
    document.getElementById("challengeInstructions").innerText = "";
    document.getElementById("targetVocabList").innerText = "";
    document.getElementById("challengeTextarea").value = "";
    
    clearInterval(challengeTimerInterval);
    document.getElementById("challengeTimer").innerHTML = `<i class="fa-solid fa-clock"></i> 60s`;
    
    fetch("/api/challenges/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_type: type })
    })
    .then(res => res.json())
    .then(data => {
        activeChallengeTitle = data.title;
        activeChallengeInstructions = data.instructions;
        challengeTimeLimit = data.time_limit_seconds || 60;
        
        document.getElementById("challengeTitle").innerText = data.title;
        
        let instructText = data.instructions;
        if (data.prompt_media) {
            instructText += `\n\nPrompt details:\n"${data.prompt_media}"`;
        }
        document.getElementById("challengeInstructions").innerText = instructText;
        
        const vocabs = data.target_vocabulary || [];
        document.getElementById("targetVocabList").innerText = vocabs.length ? vocabs.join(", ") : "Any fluent English vocabulary";
        
        // Boot up timer countdown
        startChallengeTimer();
    })
    .catch(err => {
        document.getElementById("challengeTitle").innerText = "Failed to load challenge prompt.";
        console.error("Challenge loading error: ", err);
    });
};

function startChallengeTimer() {
    let timeLeft = challengeTimeLimit;
    const timerEl = document.getElementById("challengeTimer");
    
    timerEl.innerHTML = `<i class="fa-solid fa-clock"></i> ${timeLeft}s`;
    timerEl.style.color = "var(--color-primary)";
    
    challengeTimerInterval = setInterval(() => {
        timeLeft--;
        timerEl.innerHTML = `<i class="fa-solid fa-clock"></i> ${timeLeft}s`;
        
        if (timeLeft <= 10) {
            timerEl.style.color = "var(--color-danger)";
        }
        
        if (timeLeft <= 0) {
            clearInterval(challengeTimerInterval);
            // End recording and auto-submit if text exists
            stopChallengeSpeech();
            alert("Time's up! Grading your recording.");
            submitChallengeAnswer();
        }
    }, 1000);
}

// Answer submission
document.getElementById("submitChallengeBtn").addEventListener("click", () => {
    submitChallengeAnswer();
});

function submitChallengeAnswer() {
    const textVal = document.getElementById("challengeTextarea").value.trim();
    if (!textVal) {
        alert("Please record or write your response first!");
        return;
    }
    
    clearInterval(challengeTimerInterval);
    
    const submitBtn = document.getElementById("submitChallengeBtn");
    const origText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Grading Speech...`;
    
    fetch("/api/challenges/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            challenge_type: activeChallengeType,
            title: activeChallengeTitle,
            instructions: activeChallengeInstructions,
            response: textVal
        })
    })
    .then(res => res.json())
    .then(data => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
        
        // Render grading panel results
        renderChallengeGrading(data);
    })
    .catch(err => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
        alert("Failed to submit response.");
        console.error("Challenge submit API error: ", err);
    });
}

function renderChallengeGrading(data) {
    const panel = document.getElementById("challengeGradingPanel");
    if (!panel) return;
    
    let mistakesHtml = `<p style="color: var(--text-secondary); font-style: italic;">Perfect grammar!</p>`;
    const mistakes = data.mistakes || [];
    if (mistakes.length > 0) {
        mistakesHtml = `<ul style="display: flex; flex-direction: column; gap: 6px;">`;
        mistakes.forEach(m => {
            mistakesHtml += `<li><span style="color: var(--color-danger);">❌</span> ${m}</li>`;
        });
        mistakesHtml += `</ul>`;
    }
    
    panel.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 14px; margin-top: 10px;">
            <div class="glass-card" style="padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--color-success)">
                <strong>IELTS Band Equivalent:</strong>
                <span style="font-size: 16px; font-weight: 800; color: var(--color-success);">${data.score}%</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div class="glass-card" style="padding: 10px; font-size: 12px;">
                    <div style="color: var(--text-secondary);">Fluency</div>
                    <strong style="font-size: 14px; color: var(--color-primary);">${data.fluency_score}%</strong>
                </div>
                <div class="glass-card" style="padding: 10px; font-size: 12px;">
                    <div style="color: var(--text-secondary);">Vocabulary</div>
                    <strong style="font-size: 14px; color: var(--color-warning);">${data.vocab_score}%</strong>
                </div>
            </div>
            
            <div class="glass-card" style="padding: 12px;">
                <h4 style="font-size: 13px; font-weight: 700; color: var(--color-danger); margin-bottom: 8px;">Grammar Slip-ups</h4>
                ${mistakesHtml}
            </div>
            
            <div class="better-phrase-box">
                <strong>Good Points:</strong>
                <p style="font-size: 13px; line-height: 1.5; color: var(--text-primary); margin-top: 4px;">${data.good_points}</p>
            </div>
            
            <div class="better-phrase-box" style="border-left-color: var(--color-warning);">
                <strong>Suggestions:</strong>
                <p style="font-size: 13px; line-height: 1.5; color: var(--text-primary); margin-top: 4px;">${data.suggestions}</p>
            </div>
        </div>
    `;
    
    // Add row to challenges list history
    const historyList = document.getElementById("challengeHistoryList");
    if (historyList) {
        const emptyMsg = historyList.querySelector("p");
        if (emptyMsg && emptyMsg.innerText.includes("No completed")) emptyMsg.remove();
        
        const row = document.createElement("div");
        row.className = "glass-card";
        row.style.padding = "10px 14px";
        row.style.fontSize = "13px";
        row.innerHTML = `
            <div style="display: flex; justify-content: space-between;">
                <strong>${activeChallengeType}</strong>
                <span style="color: var(--color-primary); font-weight: 700;">${data.score}%</span>
            </div>
            <p style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">${activeChallengeTitle}</p>
        `;
        historyList.insertBefore(row, historyList.firstChild);
    }
}

// Dictations mic logic
function initChallengeSpeech() {
    const mic = document.getElementById("challengeMicBtn");
    const textarea = document.getElementById("challengeTextarea");
    const status = document.getElementById("recordingStatus");
    
    if (!mic || !textarea) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.lang = "en-US";
    recognition.interimResults = true;
    
    mic.addEventListener("click", () => {
        if (challengeRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
    
    recognition.onstart = () => {
        challengeRecording = true;
        mic.classList.add("recording");
        status.innerText = "Recording... Click again to pause";
        status.style.color = "var(--color-danger)";
    };
    
    recognition.onend = () => {
        challengeRecording = false;
        mic.classList.remove("recording");
        status.innerText = "Recording paused. You can edit text before submitting.";
        status.style.color = "var(--text-secondary)";
    };
    
    recognition.onerror = () => {
        challengeRecording = false;
        mic.classList.remove("recording");
        status.innerText = "Speech error. Retrying...";
        status.style.color = "var(--text-secondary)";
    };
    
    recognition.onresult = (e) => {
        let transcript = "";
        for (let i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                transcript += e.results[i][0].transcript;
            }
        }
        if (transcript) {
            textarea.value = (textarea.value + " " + transcript).trim();
        }
    };
}

function stopChallengeSpeech() {
    challengeRecording = false;
    const mic = document.getElementById("challengeMicBtn");
    if (mic && mic.classList.contains("recording")) {
        mic.click(); // Trigger stop event click
    }
}
