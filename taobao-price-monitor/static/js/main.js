document.addEventListener('DOMContentLoaded', function () {
    const chartCanvas = document.getElementById('priceChart');
    let priceChart = null; // To hold the chart instance

    document.querySelectorAll('.view-chart-btn').forEach(button => {
        button.addEventListener('click', function () {
            const productId = this.dataset.productId;
            const productName = this.dataset.productName;
            
            fetch(`/api/price_history/${productId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                        return;
                    }

                    const chartData = {
                        labels: data.labels,
                        datasets: [{
                            label: `Price History for ${productName}`,
                            data: data.data,
                            fill: false,
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    };

                    // If a chart instance already exists, destroy it first
                    if (priceChart) {
                        priceChart.destroy();
                    }

                    // Create a new chart
                    priceChart = new Chart(chartCanvas, {
                        type: 'line',
                        data: chartData,
                        options: {
                            scales: {
                                y: {
                                    beginAtZero: false
                                }
                            }
                        }
                    });
                })
                .catch(error => console.error('Error fetching price history:', error));
        });
    });
});
