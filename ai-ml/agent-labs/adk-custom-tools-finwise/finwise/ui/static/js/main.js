document.addEventListener('DOMContentLoaded', () => {
    const startChatBtn = document.getElementById('start-chat-btn');
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatScreen = document.getElementById('chat-screen');
    const chatMessages = document.getElementById('chat-messages');

    startChatBtn.addEventListener('click', () => {
        welcomeScreen.style.display = 'none';
        chatScreen.style.display = 'flex';
        runFinwiseAgent();
    });

    function displayUserMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message user-message';
        messageElement.innerText = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function displayBotMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message bot-message';
        messageElement.innerText = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showLoadingIndicator() {
        const loadingElement = document.createElement('div');
        loadingElement.className = 'loading-indicator';
        loadingElement.innerHTML = `<div class="dot"></div><div class="dot"></div><div class="dot"></div>`;
        chatMessages.appendChild(loadingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return loadingElement;
    }

    function removeLoadingIndicator(indicator) {
        chatMessages.removeChild(indicator);
    }

    async function runFinwiseAgent() {
        const userPrompt = "Analyze my portfolio's performance over the last year and plot its growth against the S&P 500. My portfolio consists of 50% GOOG, 30% AAPL, and 20% MSFT. Then, using my aggressive risk profile, recommend an optimized allocation for these stocks. Once you have a recommendation, what's the current price of the top new stock in that list? If I approve, buy 10 shares of it.";
        
        displayUserMessage(userPrompt);
        const loadingIndicator = showLoadingIndicator();

        try {
            const encodedPrompt = encodeURIComponent(userPrompt);
            const response = await fetch(`/run-agent?prompt=${encodedPrompt}`, {
                method: 'GET'
            });

            removeLoadingIndicator(loadingIndicator);

            if (!response.ok) {
                const errorData = await response.json();
                displayBotMessage(`Error: ${errorData.detail || 'An unknown error occurred.'}`);
                return;
            }

            const data = await response.json();
            displayBotMessage(data.response);

        } catch (error) {
            removeLoadingIndicator(loadingIndicator);
            displayBotMessage('An error occurred while communicating with the agent.');
            console.error('Fetch error:', error);
        }
    }
});
