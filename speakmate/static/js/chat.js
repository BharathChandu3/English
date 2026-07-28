/* SpeakMate AI Chat JS Handler */

document.addEventListener("DOMContentLoaded", () => {
    initChatInterface();
    initSpeechRecognition();
});

// Chat Interface Core Operations
function initChatInterface() {
    const sendBtn = document.getElementById("sendBtn");
    const chatInput = document.getElementById("chatInput");
    const transcript = document.getElementById("chatTranscript");
    
    if (!chatInput) return;
    
    // Auto-scroll chat transcript to bottom
    scrollTranscript();
    
    // Submit on send button click
    sendBtn.addEventListener("click", () => {
        submitUserMessage();
    });
    
    // Submit on pressing Enter key
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            submitUserMessage();
        }
    });
}

function scrollTranscript() {
    const transcript = document.getElementById("chatTranscript");
    if (transcript) {
        transcript.scrollTop = transcript.scrollHeight;
    }
}

function submitUserMessage() {
    const chatInput = document.getElementById("chatInput");
    const text = chatInput.value.trim();
    if (!text) return;
    
    // Append user bubble instantly
    appendChatBubble("user", text);
    chatInput.value = "";
    
    // Show typing loader
    const loader = document.getElementById("chatLoader");
    if (loader) loader.style.display = "flex";
    scrollTranscript();
    
    fetch("/api/chat/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        if (loader) loader.style.display = "none";
        
        // Append tutor bubble
        // We will generate a unique ID for referencing feedback values
        const msgId = "msg-" + Date.now();
        appendChatBubble("assistant", data.reply, msgId, data);
        
        // Speak response out loud using Web Speech Synthesis TTS
        window.speakText(data.reply);
        
        // Update user stats values in header if dashboard is open
        const streakEl = document.getElementById("streakCount");
        if (streakEl && data.streak) {
            streakEl.innerText = data.streak;
        }
    })
    .catch(err => {
        if (loader) loader.style.display = "none";
        appendChatBubble("assistant", "Sorry, I had trouble reaching the AI server. Please make sure your internet is working.");
        console.error("Chat API Call Error: ", err);
    });
}

function appendChatBubble(role, content, msgId = null, fullResponseData = null) {
    const transcript = document.getElementById("chatTranscript");
    if (!transcript) return;
    
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    
    const textNode = document.createElement("p");
    textNode.innerText = content;
    bubble.appendChild(textNode);
    
    if (role === "assistant" && msgId && fullResponseData) {
        // Create feedback review button
        const fButton = document.createElement("button");
        fButton.className = "chat-feedback-btn";
        fButton.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Review Feedback`;
        fButton.onclick = () => {
            renderFeedbackOverlay(fullResponseData);
        };
        bubble.appendChild(fButton);
        
        // Create script tags holding data locally for retrieval
        const scriptData = document.createElement("script");
        scriptData.type = "application/json";
        scriptData.id = `feedback-data-${msgId}`;
        scriptData.textContent = JSON.stringify(fullResponseData);
        bubble.appendChild(scriptData);
    }
    
    transcript.appendChild(bubble);
    scrollTranscript();
}

// Open and render analysis data inside feedback sidebar drawer overlay
function renderFeedbackOverlay(data) {
    const drawer = document.getElementById("feedbackDrawer");
    const content = document.getElementById("feedbackContent");
    if (!drawer || !content) return;
    
    const feedback = data.feedback || {};
    const mistakes = feedback.mistakes || [];
    const newVocab = feedback.new_vocabulary || [];
    
    let mistakesHtml = `<p style="color: var(--text-secondary); font-style: italic;">No spelling or grammar errors found!</p>`;
    if (mistakes.length > 0) {
        mistakesHtml = `<ul style="display: flex; flex-direction: column; gap: 8px;">`;
        mistakes.forEach(m => {
            mistakesHtml += `<li><span style="color: var(--color-danger); font-weight: bold;">❌</span> ${m}</li>`;
        });
        mistakesHtml += `</ul>`;
    }
    
    let vocabHtml = `<p style="color: var(--text-secondary);">No new vocabulary suggested in this message.</p>`;
    if (newVocab.length > 0) {
        vocabHtml = `<div style="display: flex; flex-direction: column; gap: 10px;">`;
        newVocab.forEach(v => {
            vocabHtml += `
                <div style="padding: 10px; background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-glass); border-radius: 8px;">
                    <strong style="color: var(--color-success);">${v.word}</strong>
                    <p style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${v.meaning}</p>
                    <p style="font-size: 11px; font-style: italic; color: var(--text-primary); margin-top: 4px;">"${v.example}"</p>
                </div>
            `;
        });
        vocabHtml += `</div>`;
    }
    
    content.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 20px; margin-top: 20px;">
            <div class="feedback-section">
                <h4><i class="fa-solid fa-star" style="color: var(--color-warning);"></i> What you did well</h4>
                <p>${feedback.good_points || 'Clearly stated details.'}</p>
            </div>
            
            <div class="feedback-section">
                <h4><i class="fa-solid fa-circle-xmark" style="color: var(--color-danger);"></i> Identified Mistakes</h4>
                ${mistakesHtml}
            </div>
            
            <div class="feedback-section">
                <h4><i class="fa-solid fa-circle-check" style="color: var(--color-success);"></i> Better Version</h4>
                <div class="better-phrase-box">${feedback.better_version || data.reply}</div>
            </div>
            
            <div class="feedback-section">
                <h4><i class="fa-solid fa-circle-info" style="color: var(--color-primary);"></i> Explanation</h4>
                <p>${feedback.explanation || 'Perfect syntax structures used.'}</p>
            </div>
            
            <div class="feedback-section">
                <h4><i class="fa-solid fa-book-open"></i> Recommended Vocabulary</h4>
                ${vocabHtml}
            </div>
            
            <div class="feedback-section">
                <h4><i class="fa-solid fa-trophy" style="color: var(--color-warning);"></i> Speaking Challenge</h4>
                <p>${data.next_speaking_challenge || 'Try expanding details on standard daily topics.'}</p>
            </div>
        </div>
    `;
    
    drawer.classList.add("open");
}

// Global hook to view feedback for pre-rendered DB messages
window.viewChatFeedback = function(msgId) {
    const scriptEl = document.getElementById(`feedback-data-${msgId}`);
    if (scriptEl) {
        try {
            const data = JSON.parse(scriptEl.textContent);
            renderFeedbackOverlay(data);
        } catch(e) {
            console.error("Error reading preloaded JSON feedback: ", e);
        }
    } else {
        alert("Feedback details are unavailable for this message.");
    }
};

// Dictation Speech-to-Text Recognition Module (Web Speech API)
function initSpeechRecognition() {
    const micBtn = document.getElementById("micBtn");
    const chatInput = document.getElementById("chatInput");
    if (!micBtn || !chatInput) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech recognition is not supported in this browser.");
        micBtn.title = "Voice recognition unsupported in this browser.";
        return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    let isRecording = false;
    
    micBtn.addEventListener("click", () => {
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
    
    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add("recording");
        chatInput.placeholder = "Listening to your voice...";
    };
    
    recognition.onerror = (e) => {
        console.error("Speech Recognition Error: ", e);
        cleanupSpeechState();
    };
    
    recognition.onend = () => {
        cleanupSpeechState();
    };
    
    recognition.onresult = (e) => {
        const transcriptText = e.results[0][0].transcript;
        chatInput.value = transcriptText;
        // Submit voice responses automatically
        submitUserMessage();
    };
    
    function cleanupSpeechState() {
        isRecording = false;
        micBtn.classList.remove("recording");
        chatInput.placeholder = "Type your response here...";
    }
}
