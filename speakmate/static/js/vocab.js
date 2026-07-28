/* SpeakMate AI Vocabulary JS Handler */

let activeWordData = null;

document.addEventListener("DOMContentLoaded", () => {
    initFlashcard();
    initWordbankActions();
    loadDailyWord();
});

// Flip card toggle click handler
function initFlashcard() {
    const card = document.getElementById("vocabFlashcard");
    if (card) {
        card.addEventListener("click", () => {
            card.classList.toggle("flipped");
        });
    }
}

// Actions buttons
function initWordbankActions() {
    const refreshBtn = document.getElementById("refreshWordBtn");
    const saveBtn = document.getElementById("saveWordBtn");
    
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            loadDailyWord();
        });
    }
    
    if (saveBtn) {
        saveBtn.addEventListener("click", () => {
            saveActiveWord();
        });
    }
}

function loadDailyWord() {
    const card = document.getElementById("vocabFlashcard");
    if (card) card.classList.remove("flipped");
    
    const refreshBtn = document.getElementById("refreshWordBtn");
    const origText = refreshBtn ? refreshBtn.innerHTML : "";
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Loading...`;
    }
    
    // Pick random category to keep word selections diverse
    const categories = ["Business", "Travel", "Technology", "Academic", "Meetings", "General"];
    const randomCategory = categories[Math.floor(Math.random() * categories.length)];
    
    fetch(`/api/vocab/daily?category=${randomCategory}`)
        .then(res => res.json())
        .then(data => {
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = origText;
            }
            
            activeWordData = data;
            
            // Populating UI cards
            document.getElementById("flashWord").innerText = data.word;
            document.getElementById("flashCategory").innerText = randomCategory + " Vocabulary";
            document.getElementById("flashMeaning").innerText = data.meaning;
            
            const syns = data.synonyms || [];
            const ants = data.antonyms || [];
            document.getElementById("flashSynonyms").innerText = syns.length ? syns.join(", ") : "None";
            document.getElementById("flashAntonyms").innerText = ants.length ? ants.join(", ") : "None";
            
            // Generate flashcard quiz MCQs
            renderVocabQuiz(data.quiz);
        })
        .catch(err => {
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = origText;
            }
            console.error("Vocabulary Loading Error: ", err);
        });
}

function saveActiveWord() {
    if (!activeWordData) return;
    
    const saveBtn = document.getElementById("saveWordBtn");
    const origText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...`;
    
    fetch("/api/vocab/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            word: activeWordData.word,
            meaning: activeWordData.meaning,
            synonyms: activeWordData.synonyms || [],
            antonyms: activeWordData.antonyms || [],
            examples: activeWordData.examples || []
        })
    })
    .then(res => res.json())
    .then(res => {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<i class="fa-solid fa-check"></i> Saved`;
        setTimeout(() => {
            saveBtn.innerHTML = origText;
        }, 1500);
        
        // Dynamically insert element in sidebar word bank
        prependSavedWordToUI(activeWordData);
    })
    .catch(err => {
        saveBtn.disabled = false;
        saveBtn.innerHTML = origText;
        console.error("Error saving vocab word: ", err);
    });
}

function prependSavedWordToUI(wordData) {
    const list = document.getElementById("savedWordsList");
    const noWordsMsg = document.getElementById("noWordsMsg");
    if (!list) return;
    
    if (noWordsMsg) noWordsMsg.style.display = "none";
    
    // Check if word already exists in list to avoid duplicates
    const existing = list.querySelectorAll("h4");
    for (let el of existing) {
        if (el.innerText.trim() === wordData.word.trim()) {
            return;
        }
    }
    
    const item = document.createElement("div");
    item.className = "glass-card";
    item.style.padding = "14px";
    item.style.position = "relative";
    
    item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <h4 style="font-size: 16px; font-weight: 700; color: var(--color-primary);">${wordData.word}</h4>
            <button class="theme-toggle-btn" style="color: var(--color-danger); padding: 4px;" onclick="removeWord('${wordData.word}', this.parentElement.parentElement)" title="Remove word">
                <i class="fa-solid fa-trash-can"></i>
            </button>
        </div>
        <p style="font-size: 13px; color: var(--text-primary); margin-top: 6px;">${wordData.meaning}</p>
        ${wordData.synonyms ? `<p style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;"><strong>Syn:</strong> ${wordData.synonyms.join(', ')}</p>` : ''}
    `;
    
    list.insertBefore(item, list.firstChild);
}

window.removeWord = function(word, element) {
    if (!confirm(`Are you sure you want to remove '${word}' from your word bank?`)) return;
    
    fetch("/api/vocab/unsave", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word: word })
    })
    .then(res => res.json())
    .then(data => {
        element.remove();
        
        // If empty
        const list = document.getElementById("savedWordsList");
        if (list && list.children.length === 0) {
            const noWordsMsg = document.getElementById("noWordsMsg");
            if (noWordsMsg) noWordsMsg.style.display = "block";
        }
    })
    .catch(err => {
        console.error("Error removing vocabulary word: ", err);
    });
};

// Vocabulary Quiz Mechanics
function renderVocabQuiz(quiz) {
    const qTitle = document.getElementById("vocabQuizQuestion");
    const optionsContainer = document.getElementById("vocabQuizOptions");
    const explBox = document.getElementById("vocabQuizExplanation");
    
    if (!qTitle || !quiz) return;
    
    qTitle.innerText = quiz.question;
    optionsContainer.innerHTML = "";
    explBox.style.display = "none";
    
    quiz.options.forEach((opt, idx) => {
        const btn = document.createElement("button");
        btn.className = "option-btn";
        btn.innerHTML = `<span>${opt}</span> <i class="fa-regular fa-circle"></i>`;
        
        btn.addEventListener("click", () => {
            // Lock other options
            const allBtns = optionsContainer.querySelectorAll(".option-btn");
            allBtns.forEach(b => b.disabled = true);
            
            // Check correct
            if (idx === quiz.correct_index) {
                btn.className = "option-btn correct";
                btn.querySelector("i").className = "fa-solid fa-circle-check";
                submitVocabQuizScore(true);
            } else {
                btn.className = "option-btn wrong";
                btn.querySelector("i").className = "fa-solid fa-circle-xmark";
                
                // Highlight correct choice
                allBtns[quiz.correct_index].className = "option-btn correct";
                allBtns[quiz.correct_index].querySelector("i").className = "fa-solid fa-circle-check";
                submitVocabQuizScore(false);
            }
            
            // Display explanations tips
            explBox.innerText = quiz.explanation;
            explBox.style.display = "block";
        });
        
        optionsContainer.appendChild(btn);
    });
}

function submitVocabQuizScore(success) {
    fetch("/api/vocab/submit_quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ success: success })
    })
    .catch(err => console.error("Error logging vocab score: ", err));
}
