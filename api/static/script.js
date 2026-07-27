document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const sendBtn = document.getElementById('send-btn');
    const stopBtn = document.getElementById('stop-btn');

    // Configure marked.js
    marked.setOptions({ breaks: true, gfm: true });

    // ── State ──
    let currentAbortController = null;
    let currentRequestId = null;
    let isStreaming = false;

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function addMessage(content, sender, isMarkdown = false) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', `${sender}-message`, 'slide-in');

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar');
        avatarDiv.innerHTML = sender === 'user'
            ? '<i class="fa-solid fa-user"></i>'
            : '<i class="fa-solid fa-robot"></i>';

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
        msgDiv.id = 'streaming-msg';

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

    function addTypingIndicator() {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', 'bot-message', 'slide-in');
        msgDiv.id = 'typing-indicator-msg';

        const avatarDiv = document.createElement('div');
        avatarDiv.classList.add('avatar');
        avatarDiv.innerHTML = '<i class="fa-solid fa-robot"></i>';

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        contentDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        chatBox.appendChild(msgDiv);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator-msg');
        if (el) el.remove();
    }

    // ── Tool status indicator ──
    function addToolStatus(toolName) {
        // Remove any existing tool status
        removeToolStatus();
        const statusDiv = document.createElement('div');
        statusDiv.classList.add('tool-status');
        statusDiv.id = 'tool-status-indicator';
        statusDiv.innerHTML = `<div class="spinner"></div><span>${toolName}...</span>`;
        chatBox.appendChild(statusDiv);
        scrollToBottom();
    }

    function removeToolStatus() {
        const el = document.getElementById('tool-status-indicator');
        if (el) {
            el.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => el.remove(), 300);
        }
    }

    // ── UI state management ──
    function setStreamingState(streaming) {
        isStreaming = streaming;
        userInput.disabled = streaming;
        sendBtn.style.display = streaming ? 'none' : 'flex';
        stopBtn.style.display = streaming ? 'flex' : 'none';
        if (!streaming) {
            sendBtn.disabled = false;
        }
    }

    // ── SSE Parser ──
    function parseSSEEvent(rawEvent) {
        const dataLines = rawEvent.split('\n')
            .filter(line => line.startsWith('data:'))
            .map(line => line.slice(5).trim());
        if (!dataLines.length) return null;
        try {
            return JSON.parse(dataLines.join('\n'));
        } catch { return null; }
    }

    // ── Markdown render with debounce ──
    let renderTimeout = null;
    function renderMarkdownDebounced(contentDiv, fullText) {
        // Add streaming cursor class
        contentDiv.classList.add('streaming-cursor');
        if (renderTimeout) clearTimeout(renderTimeout);
        renderTimeout = setTimeout(() => {
            contentDiv.innerHTML = marked.parse(fullText);
            contentDiv.classList.add('streaming-cursor');
            scrollToBottom();
        }, 80);
    }

    function finalizeMarkdown(contentDiv, fullText) {
        if (renderTimeout) clearTimeout(renderTimeout);
        contentDiv.classList.remove('streaming-cursor');
        contentDiv.innerHTML = marked.parse(fullText);
        scrollToBottom();
    }

    // ── Stop/Cancel handler ──
    function handleStop() {
        if (currentAbortController) {
            currentAbortController.abort();
        }
        // Also call cancel endpoint
        if (currentRequestId) {
            fetch('/chat/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ request_id: currentRequestId })
            }).catch(() => {}); // fire-and-forget
        }
    }

    stopBtn.addEventListener('click', handleStop);

    // ── Main submit handler ──
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const text = userInput.value.trim();
        if (!text || isStreaming) return;

        // 1. Add user message
        addMessage(text, 'user');
        userInput.value = '';

        // 2. Set streaming state
        setStreamingState(true);
        addTypingIndicator();

        // 3. Setup abort controller
        currentAbortController = new AbortController();
        currentRequestId = null;

        let contentDiv = null;
        let fullResponse = '';
        let wasCancelled = false;

        try {
            const response = await fetch('/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text }),
                signal: currentAbortController.signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Server error' }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            if (!response.body) throw new Error('Streaming not supported');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';

                for (const rawEvent of events) {
                    const event = parseSSEEvent(rawEvent);
                    if (!event) continue;

                    switch (event.type) {
                        case 'stream_start':
                            currentRequestId = event.request_id;
                            break;

                        case 'tool_start':
                            removeTypingIndicator();
                            addToolStatus(event.tool || 'Processing');
                            break;

                        case 'tool_end':
                            removeToolStatus();
                            break;

                        case 'token':
                            if (!contentDiv) {
                                removeTypingIndicator();
                                removeToolStatus();
                                contentDiv = createBotMessageContainer();
                            }
                            fullResponse += event.content;
                            renderMarkdownDebounced(contentDiv, fullResponse);
                            break;

                        case 'error':
                            removeTypingIndicator();
                            removeToolStatus();
                            throw new Error(event.message || 'An error occurred');

                        case 'done':
                            if (event.reason === 'cancelled') {
                                wasCancelled = true;
                            }
                            break;
                    }
                }
            }

            // Finalize
            removeTypingIndicator();
            removeToolStatus();

            if (contentDiv && fullResponse) {
                finalizeMarkdown(contentDiv, fullResponse);
            } else if (!contentDiv && !wasCancelled) {
                // No tokens received — fall back to non-streaming
                addMessage('No response received. Please try again.', 'bot', true);
            }

        } catch (error) {
            removeTypingIndicator();
            removeToolStatus();

            if (error.name === 'AbortError') {
                wasCancelled = true;
            } else {
                console.error('Chat Error:', error);
                if (contentDiv && fullResponse) {
                    finalizeMarkdown(contentDiv, fullResponse);
                }
                addMessage(`❌ **Error:** ${error.message}`, 'bot', true);
            }
        } finally {
            // Add stopped indicator if cancelled with partial content
            if (wasCancelled && contentDiv && fullResponse) {
                finalizeMarkdown(contentDiv, fullResponse);
                const stoppedDiv = document.createElement('div');
                stoppedDiv.classList.add('stopped-indicator');
                stoppedDiv.innerHTML = '<i class="fa-solid fa-stop"></i> Response stopped';
                contentDiv.appendChild(stoppedDiv);
            }

            // Clean up streaming message ID
            const streamMsg = document.getElementById('streaming-msg');
            if (streamMsg) streamMsg.removeAttribute('id');

            // Reset state
            currentAbortController = null;
            currentRequestId = null;
            setStreamingState(false);
            userInput.focus();
        }
    });
});
