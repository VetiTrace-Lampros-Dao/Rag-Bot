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

    function createBotMessageContainer() {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', 'bot-message', 'slide-in');

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar');
        avatarDiv.innerHTML = '<i class="fa-solid fa-robot"></i>';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        chatBox.appendChild(msgDiv);
        scrollToBottom();

        return contentDiv;
    }

    function parseSSEEvent(rawEvent) {
        const lines = rawEvent.split('\n');
        const dataLines = lines
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trim());

        if (!dataLines.length) return null;

        try {
            return JSON.parse(dataLines.join('\n'));
        } catch (error) {
            return null;
        }
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
            const response = await fetch('/chat?stream=true', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Server error occurred');
            }

            removeTypingIndicator();

            // 4. Render streaming bot response
            const contentDiv = createBotMessageContainer();
            const textNode = document.createElement('p');
            contentDiv.appendChild(textNode);

            if (!response.body) {
                throw new Error('Streaming is not supported by the browser');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fullResponse = '';
            let streamError = null;

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';

                for (const rawEvent of events) {
                    const event = parseSSEEvent(rawEvent);
                    if (!event) continue;

                    if (event.type === 'chunk' && event.content) {
                        fullResponse += event.content;
                        textNode.textContent = fullResponse;
                        scrollToBottom();
                    } else if (event.type === 'error') {
                        streamError = event.message || 'Streaming failed';
                    }
                }
            }

            if (streamError) {
                throw new Error(streamError);
            }

            if (!fullResponse.trim()) {
                throw new Error('Empty response from server');
            }

            contentDiv.innerHTML = marked.parse(fullResponse);
            scrollToBottom();

        } catch (error) {
            console.error('Chat Error:', error);
            removeTypingIndicator();
            addMessage(`❌ **Error:** ${error.message}`, 'bot', true);
        } finally {
            // 5. Re-enable input
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });
});
