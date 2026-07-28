/* SpeakMate AI Interview Prep controller */

let interviewRecording = false;

document.addEventListener("DOMContentLoaded", () => {
    initInterviewSpeech();
});

window.startInterview = function(mode) {
    // UI Setup
    document.getElementById("interviewPlaceholder").style.display = "none";
    document.getElementById("interviewRoom").style.display = "flex";
    
    const transcript = document.getElementById("interviewTranscript");
    transcript.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 24px; color: var(--color-primary);"></i>
            <p style="margin-top: 10px; color: var(--text-secondary);">Initializing mock room, boot-up interviewer...</p>
        </div>
    `;
    
    // API trigger
    fetch("/api/interview/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        transcript.innerHTML = "";
        appendInterviewBubble("assistant", data.reply);
        window.speakText(data.reply);
    })
    .catch(err => {
        transcript.innerHTML = "";
        appendInterviewBubble("assistant", "Could not initialize interview room. Please check connection.");
        console.error("Interview start API error: ", err);
    });
};

function appendInterviewBubble(role, content) {
    const transcript = document.getElementById("interviewTranscript");
    if (!transcript) return;
    
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    
    const p = document.createElement("p");
    p.innerText = content;
    bubble.appendChild(p);
    
    transcript.appendChild(bubble);
    transcript.scrollTop = transcript.scrollHeight;
}

// Answer submission
document.getElementById("interviewSendBtn").addEventListener("click", () => {
    submitInterviewAnswer();
});

document.getElementById("interviewInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        submitInterviewAnswer();
    }
});

function submitInterviewAnswer() {
    const input = document.getElementById("interviewInput");
    const answer = input.value.trim();
    if (!answer) return;
    
    appendInterviewBubble("user", answer);
    input.value = "";
    
    const loader = document.getElementById("interviewLoader");
    loader.style.display = "flex";
    
    fetch("/api/interview/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: answer })
    })
    .then(res => res.json())
    .then(data => {
        loader.style.display = "none";
        
        // Append Next Question
        appendInterviewBubble("assistant", data.reply);
        window.speakText(data.reply);
        
        // Populate Metric Drawer
        updateMetricsPanel(data);
    })
    .catch(err => {
        loader.style.display = "none";
        appendInterviewBubble("assistant", "Error sending answer to interviewer. Please retry.");
        console.error("Interview answer API call error: ", err);
    });
}

function updateMetricsPanel(data) {
    const panel = document.getElementById("interviewMetricsPanel");
    if (!panel) return;
    
    panel.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 14px; margin-top: 10px;">
            <div class="glass-card" style="padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--color-primary)">
                <strong>Overall Score:</strong>
                <span style="font-size: 16px; font-weight: 800; color: var(--color-primary);">${data.score}%</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div class="glass-card" style="padding: 10px; font-size: 13px;">
                    <div style="color: var(--text-secondary);">Confidence</div>
                    <strong style="font-size: 15px; color: var(--color-warning);">${data.confidence}%</strong>
                </div>
                <div class="glass-card" style="padding: 10px; font-size: 13px;">
                    <div style="color: var(--text-secondary);">Grammar</div>
                    <strong style="font-size: 15px; color: var(--color-success);">${data.grammar}%</strong>
                </div>
            </div>
            
            <div class="glass-card" style="padding: 10px; font-size: 13px;">
                <div style="color: var(--text-secondary);">Professionalism Rating</div>
                <strong style="font-size: 15px; color: var(--color-primary);">${data.professionalism}%</strong>
            </div>
            
            <div class="better-phrase-box" style="margin-top: 5px;">
                <strong>Key Suggestions:</strong>
                <p style="font-size: 13px; line-height: 1.5; color: var(--text-primary); margin-top: 4px;">${data.suggestions}</p>
            </div>
        </div>
    `;
    
    // Add row to historical scores list if available
    const historyList = document.getElementById("interviewHistoryList");
    if (historyList) {
        // Remove empty paragraph
        const emptyMsg = historyList.querySelector("p");
        if (emptyMsg && emptyMsg.innerText.includes("No completed")) emptyMsg.remove();
        
        const mode = sessionStorage.getItem("interview_mode") || "Interview";
        const row = document.createElement("div");
        row.className = "glass-card";
        row.style.padding = "10px 14px";
        row.style.fontSize = "13px";
        row.innerHTML = `
            <div style="display: flex; justify-content: space-between;">
                <strong>Response Assessment</strong>
                <span style="color: var(--color-primary); font-weight: 700;">Score: ${data.score}%</span>
            </div>
            <p style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">
                Grammar: ${data.grammar} | Conf: ${data.confidence} | Prof: ${data.professionalism}
            </p>
        `;
        historyList.insertBefore(row, historyList.firstChild);
    }
}

// Dictations Recognition Setup
function initInterviewSpeech() {
    const mic = document.getElementById("interviewMicBtn");
    const input = document.getElementById("interviewInput");
    if (!mic || !input) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = "en-US";
    
    mic.addEventListener("click", () => {
        if (interviewRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
    
    recognition.onstart = () => {
        interviewRecording = true;
        mic.classList.add("recording");
        input.placeholder = "Listening...";
    };
    
    recognition.onend = () => {
        interviewRecording = false;
        mic.classList.remove("recording");
        input.placeholder = "Say or type your answer here...";
    };
    
    recognition.onerror = () => {
        interviewRecording = false;
        mic.classList.remove("recording");
        input.placeholder = "Say or type your answer here...";
    };
    
    recognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        input.value = text;
        submitInterviewAnswer();
    };
}
