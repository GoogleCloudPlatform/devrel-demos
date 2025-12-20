document.getElementById('submit-btn').addEventListener('click', async () => {
    const nameInput = document.getElementById('name-input');
    const greetingDisplay = document.getElementById('greeting-display');
    const name = nameInput.value.trim();

    let url = '/greetings';
    if (name) {
        url += `?name=${encodeURIComponent(name)}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();
        // The API returns { "message": "..." }
        // The UI requirement is "Hello, ...!"
        // The API returns "Hello World" or "Hello {name}"
        // We can just use the message directly or format it if needed.
        // Based on the image "Hello, ...!", if the API returns "Hello World", we might want to display it as is.
        // But let's strictly follow the visual "Hello, ...!" style if possible.
        // The API returns "Hello {name}".
        // The display expects "Hello, {name}!"
        
        // Let's assume the API message is the source of truth for the text, 
        // but to match the design strictly:
        // If input is empty -> "Hello World" (API) -> "Hello, World!" (UI preference?)
        // The prompt says: returns "hello" plus the name. 
        // Image shows "Hello, ...!" 
        
        // We'll use the API response but format it to match the visual cue if it lacks punctuation
        greetingDisplay.textContent = data.message + "!"; 
        
    } catch (error) {
        console.error('Error fetching greeting:', error);
        greetingDisplay.textContent = 'Error connecting to server';
    }
});
