/* SpeakMate AI Grammar Quiz & Explanations controller */

let currentGrammarQuiz = [];
let currentQuestionIndex = 0;
let grammarQuizScore = 0;
let activeGrammarTopic = "Tenses";

document.addEventListener("DOMContentLoaded", () => {
    // Initial auto-load first topic
    const firstBtn = document.querySelector(".grammar-topic-btn");
    if (firstBtn) {
        firstBtn.click();
    }
});

window.loadGrammarTopic = function(topic, buttonEl) {
    activeGrammarTopic = topic;
    
    // Highlight selected module
    const btns = document.querySelectorAll(".grammar-topic-btn");
    btns.forEach(b => b.classList.remove("active-topic"));
    if (buttonEl) buttonEl.classList.add("active-topic");
    
    // UI Loadings
    document.getElementById("grammarQuizPlaceholder").style.display = "none";
    document.getElementById("grammarQuizContent").style.display = "none";
    
    const explanationCard = document.getElementById("grammarExplanationCard");
    explanationCard.style.display = "block";
    
    document.getElementById("grammarTopicTitle").innerText = topic;
    document.getElementById("grammarExplanationContent").innerHTML = `
        <div style="text-align: center; padding: 30px;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 24px; color: var(--color-primary);"></i>
            <p style="margin-top: 10px; color: var(--text-secondary);">Generating comprehensive lesson details...</p>
        </div>
    `;
    document.getElementById("grammarExamplesList").innerHTML = "";
    
    fetch(`/api/grammar/lesson?topic=${topic}`)
        .then(res => res.json())
        .then(data => {
            // Render explanation
            document.getElementById("grammarExplanationContent").innerText = data.explanation;
            
            let examplesHtml = "";
            (data.examples || []).forEach(ex => {
                examplesHtml += `<li>${ex}</li>`;
            });
            document.getElementById("grammarExamplesList").innerHTML = examplesHtml || "<li>No examples loaded.</li>";
            
            // Set Quiz State
            currentGrammarQuiz = data.quiz || [];
            currentQuestionIndex = 0;
            grammarQuizScore = 0;
            
            // Show quiz container
            document.getElementById("grammarQuizContent").style.display = "flex";
            renderGrammarQuestion();
        })
        .catch(err => {
            document.getElementById("grammarExplanationContent").innerText = "Failed to load explanation text from AI server.";
            console.error("Grammar Lesson Load Error: ", err);
        });
};

function renderGrammarQuestion() {
    const qIndicator = document.getElementById("grammarQuestionIndicator");
    const qScore = document.getElementById("grammarQuizScore");
    const qText = document.getElementById("grammarQuestionText");
    const optionsContainer = document.getElementById("grammarOptionsContainer");
    const fbBox = document.getElementById("grammarQuizFeedback");
    const nextBtn = document.getElementById("grammarNextQuestionBtn");
    
    if (currentGrammarQuiz.length === 0) return;
    
    const quiz = currentGrammarQuiz[currentQuestionIndex];
    
    // Reset views
    qIndicator.innerText = `Question ${currentQuestionIndex + 1} of ${currentGrammarQuiz.length}`;
    qScore.innerText = `Score: ${grammarQuizScore}/${currentQuestionIndex}`;
    qText.innerText = quiz.question;
    optionsContainer.innerHTML = "";
    fbBox.style.display = "none";
    nextBtn.style.display = "none";
    
    quiz.options.forEach((opt, idx) => {
        const btn = document.createElement("button");
        btn.className = "option-btn";
        btn.innerHTML = `<span>${opt}</span> <i class="fa-regular fa-circle"></i>`;
        
        btn.addEventListener("click", () => {
            // Lock inputs
            const allBtns = optionsContainer.querySelectorAll(".option-btn");
            allBtns.forEach(b => b.disabled = true);
            
            if (idx === quiz.correct_index) {
                btn.className = "option-btn correct";
                btn.querySelector("i").className = "fa-solid fa-circle-check";
                grammarQuizScore++;
                qScore.innerText = `Score: ${grammarQuizScore}/${currentQuestionIndex + 1}`;
            } else {
                btn.className = "option-btn wrong";
                btn.querySelector("i").className = "fa-solid fa-circle-xmark";
                
                // Highlight correct
                allBtns[quiz.correct_index].className = "option-btn correct";
                allBtns[quiz.correct_index].querySelector("i").className = "fa-solid fa-circle-check";
            }
            
            // Show Feedback Explanation
            fbBox.innerHTML = `<strong>Explanation:</strong> ${quiz.explanation}`;
            fbBox.style.display = "block";
            
            // Show Next Button
            nextBtn.style.display = "block";
        });
        
        optionsContainer.appendChild(btn);
    });
}

// Wire up next button click listener
document.getElementById("grammarNextQuestionBtn").addEventListener("click", () => {
    currentQuestionIndex++;
    
    if (currentQuestionIndex < currentGrammarQuiz.length) {
        renderGrammarQuestion();
    } else {
        // Complete Quiz and submit scores
        finishGrammarQuiz();
    }
});

function finishGrammarQuiz() {
    const totalQuestions = currentGrammarQuiz.length;
    const pctScore = Math.round((grammarQuizScore / totalQuestions) * 100);
    
    const optionsContainer = document.getElementById("grammarOptionsContainer");
    const qText = document.getElementById("grammarQuestionText");
    const qIndicator = document.getElementById("grammarQuestionIndicator");
    const nextBtn = document.getElementById("grammarNextQuestionBtn");
    const fbBox = document.getElementById("grammarQuizFeedback");
    
    qIndicator.innerText = "Quiz Completed";
    qText.innerText = `You finished the quiz on '${activeGrammarTopic}'!`;
    nextBtn.style.display = "none";
    fbBox.style.display = "none";
    
    optionsContainer.innerHTML = `
        <div style="text-align: center; padding: 20px;">
            <i class="fa-solid fa-trophy" style="font-size: 40px; color: var(--color-warning); margin-bottom: 12px;"></i>
            <h3 style="font-size: 18px; font-weight: 700;">Final Score: ${pctScore}%</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 6px;">
                Grammar mastery rating successfully uploaded to dashboard.
            </p>
        </div>
    `;
    
    // Post scores to API
    fetch("/api/grammar/submit_quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            topic: activeGrammarTopic,
            score: pctScore
        })
    })
    .then(res => res.json())
    .then(data => {
        // Update local score labels in cards if dashboard is open
        const scoreVal = document.getElementById("grammarScoreVal");
        if (scoreVal) scoreVal.innerText = `${pctScore}%`;
    })
    .catch(err => console.error("Error submitting grammar score: ", err));
}
