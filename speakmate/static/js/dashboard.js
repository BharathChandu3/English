/* SpeakMate AI Dashboard Scripts */

document.addEventListener("DOMContentLoaded", () => {
    loadProgressChart();
});

function loadProgressChart() {
    const ctx = document.getElementById("progressLineChart");
    if (!ctx) return;
    
    fetch("/api/progress/history")
        .then(res => res.json())
        .then(data => {
            const chartLabels = data.labels && data.labels.length ? data.labels : ["Today"];
            const grammarDataset = data.grammar && data.grammar.length ? data.grammar : [50];
            const vocabDataset = data.vocab && data.vocab.length ? data.vocab : [50];
            const speakingDataset = data.speaking && data.speaking.length ? data.speaking : [50];
            const confidenceDataset = data.confidence && data.confidence.length ? data.confidence : [50];
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartLabels,
                    datasets: [
                        {
                            label: 'Grammar',
                            data: grammarDataset,
                            borderColor: '#818cf8',
                            backgroundColor: 'rgba(129, 140, 248, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            fill: true
                        },
                        {
                            label: 'Vocabulary',
                            data: vocabDataset,
                            borderColor: '#34d399',
                            backgroundColor: 'rgba(52, 211, 153, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            fill: true
                        },
                        {
                            label: 'Speaking',
                            data: speakingDataset,
                            borderColor: '#fb7185',
                            backgroundColor: 'rgba(251, 113, 133, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            fill: true
                        },
                        {
                            label: 'Confidence',
                            data: confidenceDataset,
                            borderColor: '#fbbf24',
                            backgroundColor: 'rgba(251, 191, 36, 0.1)',
                            borderWidth: 3,
                            tension: 0.3,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#9ca3af',
                                font: {
                                    family: 'Plus Jakarta Sans',
                                    size: 12
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#9ca3af',
                                font: {
                                    family: 'Plus Jakarta Sans',
                                    size: 11
                                }
                            }
                        },
                        y: {
                            min: 0,
                            max: 100,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#9ca3af',
                                font: {
                                    family: 'Plus Jakarta Sans',
                                    size: 11
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(err => {
            console.error("Error drawing progress line chart: ", err);
        });
}
