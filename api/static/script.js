document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const sendBtn = document.getElementById('send-btn');

    // Configure marked.js to sanitize and format nicely
    marked.setOptions({
        breaks: true, // Convert \n to <br>
        gfm: true     // GitHub Flavored Markdown
    });

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function addMessage(content, sender, isMarkdown = false) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', `${sender}-message`, 'slide-in');

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar');
        
        if (sender === 'user') {
            avatarDiv.innerHTML = '<i class="fa-solid fa-user"></i>';
        } else {
            avatarDiv.innerHTML = '<i class="fa-solid fa-robot"></i>';
        }

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        
        if (isMarkdown && sender === 'bot') {
            contentDiv.innerHTML = marked.parse(content);
        } else {
            const p = document.createElement('p');
            p.textContent = content;
            contentDiv.appendChild(p);
        }

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        
        chatBox.appendChild(msgDiv);
        scrollToBottom();
    }

    function addTypingIndicator() {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', 'bot-message', 'slide-in');
        msgDiv.id = 'typing-indicator-msg';

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar');
        avatarDiv.innerHTML = '<i class="fa-solid fa-robot"></i>';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        
        chatBox.appendChild(msgDiv);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator-msg');
        if (indicator) {
            indicator.remove();
        }
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const text = userInput.value.trim();
        if (!text) return;

        // 1. Add user message
        addMessage(text, 'user');
        userInput.value = '';
        
        // 2. Disable input & show typing
        userInput.disabled = true;
        sendBtn.disabled = true;
        addTypingIndicator();

        try {
            // 3. Call backend API
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            
            removeTypingIndicator();

            if (!response.ok) {
                throw new Error(data.detail || 'Server error occurred');
            }

            // 4. Render bot response as Markdown
            addMessage(data.response, 'bot', true);

        } catch (error) {
            console.error('Chat Error:', error);
            removeTypingIndicator();
            addMessage(`❌ **Error:** ${error.message}. Please ensure the backend is running and the API is accessible.`, 'bot', true);
        } finally {
            // 5. Re-enable input
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });
});
