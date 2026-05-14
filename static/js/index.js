let currentChatSessionId = null;

const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarClose = document.getElementById('sidebarClose');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const newChatButton = document.getElementById('newChatButton');
const chatSessionsList = document.getElementById('chatSessionsList');
const chatContainer = document.getElementById('chat-container');
const chatMessages = document.getElementById('chatMessages');
const chatTitle = document.getElementById('chatTitle');
const messageInput = document.getElementById('messageInput');
const modelSelectorContainer = document.getElementById('modelSelectorContainer');
const sendButton = document.getElementById('sendButton');
const themeToggle = document.getElementById('theme-toggle');
const overlayHighlight = document.getElementById('overlay-highlight');
const highlightHole = document.getElementById('highlight-hole');
const modelInstructionTooltip = document.getElementById('model-instruction-tooltip');
const closeInstructionTooltip = document.getElementById('close-instruction-tooltip');

// New elements
const scrollToBottomBtn = document.getElementById('scroll-to-bottom');
const sendSound = document.getElementById('send-sound');
const receiveSound = document.getElementById('receive-sound');
const modelDescTooltip = document.getElementById('model-description-tooltip');
const welcomeGreeting = document.getElementById('welcome-greeting');



const suggestionContainer = document.getElementById('suggestion-container');

function toggleSuggestions(show) {
    if (suggestionContainer) {
        suggestionContainer.style.display = show ? 'block' : 'none';
    }
}

// --- NEW UX FEATURES ---

// 2.2 Sound Effects
function playSendSound() {
    sendSound.currentTime = 0;
    sendSound.play().catch(e => console.error("Error playing send sound:", e));
}

function playReceiveSound() {
    receiveSound.currentTime = 0;
    receiveSound.play().catch(e => console.error("Error playing receive sound:", e));
}



// 3.2 Model Description Tooltip
document.querySelectorAll('.model-button').forEach(button => {
    button.addEventListener('mouseenter', (e) => {
        const description = e.target.dataset.description;
        if (description) {
            modelDescTooltip.textContent = description;
            const rect = e.target.getBoundingClientRect();
            modelDescTooltip.style.left = `${rect.left + rect.width / 2}px`;
            modelDescTooltip.style.top = `${rect.bottom + 10}px`;
            modelDescTooltip.style.transform = 'translateX(-50%) translateY(0)';
            modelDescTooltip.style.opacity = '1';
        }
    });
    button.addEventListener('mouseleave', () => {
        modelDescTooltip.style.opacity = '0';
        modelDescTooltip.style.transform = 'translateX(-50%) translateY(10px)';
    });
});

// 4.2 Scroll to Bottom Button
chatContainer.addEventListener('scroll', () => {
    // Show button if scrolled up more than 300px from the bottom
    if (chatContainer.scrollHeight - chatContainer.scrollTop > chatContainer.clientHeight + 300) {
        scrollToBottomBtn.classList.add('visible');
    } else {
        scrollToBottomBtn.classList.remove('visible');
    }
});
scrollToBottomBtn.addEventListener('click', () => {
    chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
});

// 4.3 Unload Confirmation
window.addEventListener('beforeunload', (e) => {
    if (messageInput.value.trim().length > 0) {
        e.preventDefault();
        e.returnValue = ''; // Required for Chrome
        return ''; // For other browsers
    }
});

// --- END NEW UX FEATURES ---




// --- Alert Logic ---
function showAlert(message, type = 'success') {
    const alertContainer = document.getElementById('alert-container');
    const alertColors = { success: { bg: 'bg-green-500', icon: 'fa-check-circle' }, error: { bg: 'bg-red-500', icon: 'fa-exclamation-circle' }, warning: { bg: 'bg-yellow-500', icon: 'fa-exclamation-triangle' }, info: { bg: 'bg-blue-500', icon: 'fa-info-circle' } };
    const alertDiv = document.createElement('div');
    alertDiv.className = `flex items-center p-4 mb-4 text-white ${alertColors[type].bg} rounded-lg shadow-lg animate-fade-in-right`;
    alertDiv.innerHTML = `<i class="fas ${alertColors[type].icon} mr-3"></i><span>${message}</span>`;
    alertContainer.appendChild(alertDiv);
    alertContainer.classList.remove('hidden');
    setTimeout(() => {
        alertDiv.classList.add('animate-fade-out-right');
        setTimeout(() => { alertDiv.remove(); if (alertContainer.childElementCount === 0) alertContainer.classList.add('hidden'); }, 500);
    }, 5000);
}

// --- Sidebar Logic ---
function handleSidebarToggle() {
    if (window.innerWidth < 1024) {
        sidebar.classList.toggle('sidebar-open');
        sidebarOverlay.classList.toggle('hidden');
    } else {
        sidebar.classList.toggle('sidebar-hidden-desktop');
    }
}

function closeSidebar() {
    if (window.innerWidth < 1024) {
        sidebar.classList.remove('sidebar-open');
        sidebarOverlay.classList.add('hidden');
    }
}

sidebarToggle.addEventListener('click', handleSidebarToggle);
sidebarClose.addEventListener('click', closeSidebar);
sidebarOverlay.addEventListener('click', closeSidebar);

window.addEventListener('resize', () => {
    if (window.innerWidth >= 1024) {
        sidebar.classList.remove('sidebar-open');
        sidebarOverlay.classList.add('hidden');
    } else {
        sidebar.classList.remove('sidebar-hidden-desktop');
    }
});

// --- Enhanced Theme Toggle Logic ---
themeToggle.addEventListener('click', () => {
    document.body.classList.add('theme-switching');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');

    setTimeout(() => {
        document.documentElement.classList.toggle('dark');
        localStorage.theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        const isDarkAfter = document.documentElement.classList.contains('dark');

        if (isDarkAfter) {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        } else {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }

        showThemeChangeAlert(isDarkAfter ? 'เปลี่ยนเป็น Dark Mode' : 'เปลี่ยนเป็น Light Mode');

        setTimeout(() => {
            document.body.classList.remove('theme-switching');
        }, 800);
    }, 100);
});

function showThemeChangeAlert(message) {
    const alertContainer = document.getElementById('alert-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `flex items-center p-4 mb-4 text-white bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg shadow-lg animate-fade-in-right`;
    alertDiv.innerHTML = `<div class="flex items-center"><div class="w-8 h-8 rounded-full bg-white bg-opacity-20 flex items-center justify-center mr-3"><i class="fas fa-palette text-sm"></i></div><span class="font-medium">${message}</span></div>`;
    alertContainer.appendChild(alertDiv);
    alertContainer.classList.remove('hidden');
    setTimeout(() => {
        alertDiv.classList.add('animate-fade-out-right');
        setTimeout(() => {
            alertDiv.remove();
            if (alertContainer.childElementCount === 0) {
                alertContainer.classList.add('hidden');
            }
        }, 500);
    }, 2000);
}

function initializeTheme() {
    document.body.classList.add('theme-switching');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');
    const isDark = localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);

    if (isDark) {
        document.documentElement.classList.add('dark');
        if (sunIcon && moonIcon) {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
    } else {
        document.documentElement.classList.remove('dark');
        if (sunIcon && moonIcon) {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }
    }

    setTimeout(() => {
        document.body.classList.remove('theme-switching');
    }, 400);
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!('theme' in localStorage)) {
        document.body.classList.add('theme-switching');
        const sunIcon = document.getElementById('sun-icon');
        const moonIcon = document.getElementById('moon-icon');
        setTimeout(() => {
            if (e.matches) {
                document.documentElement.classList.add('dark');
                if (sunIcon && moonIcon) {
                    sunIcon.classList.add('hidden');
                    moonIcon.classList.remove('hidden');
                }
            } else {
                document.documentElement.classList.remove('dark');
                if (sunIcon && moonIcon) {
                    sunIcon.classList.remove('hidden');
                    moonIcon.classList.add('hidden');
                }
            }
            setTimeout(() => {
                document.body.classList.remove('theme-switching');
            }, 800);
        }, 100);
    }
});

// --- Core Chat Functions ---
function clearChatMessages() {
    chatMessages.innerHTML = '';
}

function setActiveSession(sessionId) {
    document.querySelectorAll('#chatSessionsList li').forEach(item => item.classList.remove('active-session'));
    const activeItem = document.querySelector(`#chatSessionsList [data-session-id="${sessionId}"]`);
    if (activeItem) { activeItem.classList.add('active-session'); chatTitle.textContent = activeItem.querySelector('span').textContent; }
}

async function loadChatMessages(sessionId) {
    clearChatMessages();
    currentChatSessionId = sessionId;
    setActiveSession(sessionId);

    if (window.innerWidth < 1024) {
        closeSidebar();
    }

    try {
        const response = await fetch(`/chat/sessions/${sessionId}/messages`);
        if (!response.ok) throw new Error('Failed to load messages');
        const messages = await response.json();
        if (messages.length === 0 || (messages.length === 1 && messages[0].sender === 'bot')) {
            toggleSuggestions(true);
        } else {
            toggleSuggestions(false);
        }
        messages.forEach(msg => addMessage(msg.content, msg.sender, false, msg.id, msg.feedback));
    } catch (error) {
        console.error('Error loading messages:', error);
        addMessage('เกิดข้อผิดพลาดในการโหลดข้อความ', 'bot', false);
    }
}

async function loadChatSessions() {
    try {
        const response = await fetch('/chat/sessions');
        if (!response.ok) throw new Error('Failed to fetch sessions');
        const sessions = await response.json();
        chatSessionsList.innerHTML = '';
        if (sessions.length > 0) {
            sessions.forEach(session => {
                const listItem = document.createElement('li');
                listItem.className = 'group relative rounded-md';
                listItem.dataset.sessionId = session.id;

                listItem.innerHTML = `
                            <a href="#" class="flex items-center justify-between p-2 space-x-3 rounded-md text-gray-300 hover:bg-gray-700 transition-colors">
                                <div class="flex items-center space-x-3 truncate">
                                   
                                    <span class="truncate">${session.title || `Chat ${session.id}`}</span>
                                </div>
                            </a>
                            <button class="absolute right-1 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-700/50 transition-all opacity-0 group-hover:opacity-100 chat-action-button">
                                <i class="fas fa-ellipsis-v"></i>
                            </button>
                            <div class="chat-action-menu">
                                <button class="rename-button"><i class="fas fa-pencil-alt"></i>Rename</button>
                                <button class="delete-button"><i class="fas fa-trash"></i>Delete</button>
                            </div>
                        `;

                const mainLink = listItem.querySelector('a');
                const actionButton = listItem.querySelector('.chat-action-button');
                const actionMenu = listItem.querySelector('.chat-action-menu');
                const renameButton = listItem.querySelector('.rename-button');
                const deleteButton = listItem.querySelector('.delete-button');

                mainLink.onclick = (e) => { e.preventDefault(); loadChatMessages(session.id); };
                actionButton.onclick = (e) => {
                    e.stopPropagation();
                    document.querySelectorAll('.chat-action-menu.show').forEach(menu => {
                        if (menu !== actionMenu) menu.classList.remove('show');
                    });
                    actionMenu.classList.toggle('show');
                };
                renameButton.onclick = (e) => { e.stopPropagation(); actionMenu.classList.remove('show'); enableTitleEditing(listItem, session.id); };
                deleteButton.onclick = (e) => { e.stopPropagation(); actionMenu.classList.remove('show'); deleteChatSession(session.id); };

                chatSessionsList.appendChild(listItem);
            });

            if (currentChatSessionId === null || !sessions.some(s => s.id === currentChatSessionId)) {
                loadChatMessages(sessions[0].id);
            } else {
                setActiveSession(currentChatSessionId);
            }
        } else {
            startNewChat();
        }
    } catch (error) {
        console.error('Error loading chat sessions:', error);
    }
}

async function startNewChat() {
    clearChatMessages();
    try {
        const response = await fetch('/chat/sessions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: "New Chat" }) });
        if (!response.ok) throw new Error('Failed to create session');
        const newSession = await response.json();
        currentChatSessionId = null;
        await loadChatSessions();
        showAlert('New chat created!', 'success');
    } catch (error) {
        console.error('Error creating new chat session:', error);
        showAlert('Failed to create new chat.', 'error');
    }
}

newChatButton.addEventListener('click', startNewChat);

function enableTitleEditing(listItem, sessionId) {
    const span = listItem.querySelector('span');
    const currentTitle = span.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentTitle;
    input.className = 'bg-gray-800 text-white w-full';

    span.parentNode.replaceChild(input, span);
    input.focus();

    const save = async () => {
        const newTitle = input.value.trim();
        if (newTitle && newTitle !== currentTitle) {
            await saveChatSessionTitle(sessionId, newTitle);
        }
        loadChatSessions();
    };

    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') input.blur();
        else if (e.key === 'Escape') loadChatSessions();
    });
}

async function saveChatSessionTitle(sessionId, newTitle) {
    try {
        await fetch(`/chat/sessions/${sessionId}/rename`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_title: newTitle })
        });
        showAlert('Chat renamed successfully!', 'success');
    } catch (error) {
        console.error('Error renaming chat session:', error);
        showAlert('Failed to rename chat.', 'error');
    }
}

async function deleteChatSession(sessionId) {
    const modal = document.getElementById('custom-delete-modal');
    const confirmBtn = document.getElementById('confirm-delete-btn');
    const cancelBtn = document.getElementById('cancel-delete-btn');

    modal.classList.remove('hidden');

    const confirmHandler = async () => {
        try {
            await fetch(`/chat/sessions/${sessionId}`, { method: 'DELETE' });
            if (currentChatSessionId === sessionId) {
                currentChatSessionId = null;
                clearChatMessages();
                chatTitle.textContent = 'เลือกแชทเพื่อเริ่มต้น';
            }
            loadChatSessions();
            showAlert('Chat deleted successfully!', 'success');
        } catch (error) {
            console.error('Error deleting chat session:', error);
            showAlert('Failed to delete chat.', 'error');
        } finally {
            modal.classList.add('hidden');
            confirmBtn.removeEventListener('click', confirmHandler);
            cancelBtn.removeEventListener('click', cancelHandler);
        }
    };

    const cancelHandler = () => {
        modal.classList.add('hidden');
        confirmBtn.removeEventListener('click', confirmHandler);
        cancelBtn.removeEventListener('click', cancelHandler);
    };

    confirmBtn.addEventListener('click', confirmHandler);
    cancelBtn.addEventListener('click', cancelHandler);
}

function addMessage(content, sender, stream = false, messageId = null, feedback = null) {
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-fade-in flex items-start gap-3';
    if (messageId) {
        messageWrapper.dataset.messageId = messageId;
    }
    let returnElement;
    if (sender === 'user') {
        messageWrapper.innerHTML = `<div class="ml-auto p-3 rounded-xl rounded-br-lg shadow-md max-w-3xl prose prose-sm prose-invert" style="background-color: var(--chat-bg-user); color: var(--chat-text-user);">${marked.parse(content)}</div>`;
        returnElement = messageWrapper;
        playSendSound();
    } else {
        messageWrapper.innerHTML = `
                    <div class="flex flex-col items-center w-full">
                        <div class="ai-message-content p-3 rounded-xl rounded-bl-lg max-w-3xl relative mx-auto" style="background-color: transparent; box-shadow: none;">
                            <div class="message-text-content prose prose-sm dark:prose-invert" style="color: var(--chat-text-bot);"></div>
                            <div class="message-toolbar mt-2 flex items-center gap-2">
                                 <button class="copy-button p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors" title="Copy to clipboard">
                                    <i class="far fa-clipboard text-gray-500 dark:text-gray-400"></i>
                                </button>
                                <button class="regenerate-button p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors" title="Regenerate response">
                                    <i class="fas fa-sync-alt text-gray-500 dark:text-gray-400"></i>
                                </button>
                                <button class="read-aloud-button p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors" title="Read aloud">
                                    <i class="fas fa-volume-up text-gray-500 dark:text-gray-400"></i>
                                </button>
                                <div class="feedback-buttons flex items-center gap-1">
                                    <button class="like-button p-1.5 rounded-md hover:bg-green-100 dark:hover:bg-green-900 transition-colors" title="Like response">
                                        <i class="far fa-thumbs-up text-gray-500 dark:text-gray-400"></i>
                                    </button>
                                    <button class="dislike-button p-1.5 rounded-md hover:bg-red-100 dark:hover:bg-red-900 transition-colors" title="Dislike response">
                                        <i class="far fa-thumbs-down text-gray-500 dark:text-gray-400"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="message-suggestions-container mt-4 text-left"></div>
                        </div>
                    </div>`;
        const textContentDiv = messageWrapper.querySelector('.message-text-content');
        const copyButton = messageWrapper.querySelector('.copy-button');
        const regenerateButton = messageWrapper.querySelector('.regenerate-button');
        const readAloudButton = messageWrapper.querySelector('.read-aloud-button');
        const likeButton = messageWrapper.querySelector('.like-button');
        const dislikeButton = messageWrapper.querySelector('.dislike-button');

        copyButton.addEventListener('click', () => {
            navigator.clipboard.writeText(textContentDiv.dataset.rawContent);
            showAlert('Copied to clipboard!', 'success');
        });

        regenerateButton.addEventListener('click', async () => {
            const lastUserMessage = await getLastUserMessage();
            if (lastUserMessage) {
                messageInput.value = lastUserMessage.content;
                sendMessage(true);
            } else {
                showAlert('Could not find the last message to regenerate.', 'error');
            }
        });

        const speak = (textToSpeak) => {
            if (!window.speechSynthesis || !textToSpeak) {
                showAlert('การอ่านออกเสียงไม่ถูกรองรับบนเบราว์เซอร์นี้', 'error');
                return;
            }

            // Stop any previous speech
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(textToSpeak);
            utterance.lang = 'th-TH';

            const trySpeak = () => {
                let voices = window.speechSynthesis.getVoices();
                if (voices.length === 0) {
                    // If voices are not loaded, set up a one-time event listener
                    window.speechSynthesis.onvoiceschanged = () => {
                        window.speechSynthesis.onvoiceschanged = null; // Clean up
                        trySpeak();
                    };
                    return;
                }

                let selectedVoice =
                    // Specifically look for the 'Pattara' voice which is female
                    voices.find(v => v.name === 'Microsoft Pattara - Thai (Thailand)') ||
                    // Fallback to the first available Thai voice
                    voices.find(v => v.lang === 'th-TH');

                if (selectedVoice) {
                    utterance.voice = selectedVoice;
                }

                utterance.onerror = (event) => {
                    console.error("Speech Synthesis Error", event.error);
                    showAlert('เกิดข้อผิดพลาดในการอ่านออกเสียง', 'error');
                };

                window.speechSynthesis.speak(utterance);
            };

            trySpeak();
        };

        readAloudButton.addEventListener('click', () => speak(textContentDiv.dataset.rawContent));
        textContentDiv.dataset.rawContent = content;

        if (feedback) {
            if (feedback === 'like') {
                likeButton.classList.add('selected');
                dislikeButton.style.display = 'none';
                likeButton.disabled = true;
            } else if (feedback === 'dislike') {
                dislikeButton.classList.add('selected');
                likeButton.style.display = 'none';
                dislikeButton.disabled = true;
            }
        }

        function handleFeedback(feedbackType) {
            if (feedbackType === 'like') {
                likeButton.classList.add('selected');
                dislikeButton.style.display = 'none';
                likeButton.disabled = true;
            } else {
                dislikeButton.classList.add('selected');
                likeButton.style.display = 'none';
                dislikeButton.disabled = true;
            }
            sendFeedback(messageWrapper.dataset.messageId, feedbackType);
            showAlert(feedbackType === 'like' ? 'ขอบคุณสำหรับความคิดเห็น!' : 'ขอบคุณสำหรับความคิดเห็น! เราจะนำไปปรับปรุงต่อไป', feedbackType === 'like' ? 'success' : 'info');
        }

        likeButton.addEventListener('click', () => handleFeedback('like'));
        dislikeButton.addEventListener('click', () => handleFeedback('dislike'));

        if (stream) {
            messageWrapper.classList.add('align-left-content'); // Align left for loading/status
            textContentDiv.innerHTML = `<div class="typing-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>`;
        } else {
            textContentDiv.innerHTML = marked.parse(content);
        }
        returnElement = messageWrapper;
    }
    chatMessages.appendChild(messageWrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return returnElement;
}

// --- Profanity Filter Logic ---
const profanityList = [
    'ควย', 'สัส', 'เหี้ย', 'เย็ด', 'แม่ง', 'มึง', 'กู', 'ชิบหาย', 'หี', 'แตด',
    'ไอ้สัตว์', 'อีสัตว์', 'ไอสัส', 'อีสัส', 'ไอ้เหี้ย', 'อีเหี้ย', 'ไอ้ควย', 'อีควย',
    'สัด', 'สาด', 'เฮี้ย', 'here', 'kuay', 'suck', 'fuck', 'f-u-c-k', 's-h-i-t', 'shit'
];

const normalizeText = (text) => {
    return text.toLowerCase().replace(/[^a-zก-๙0-9]/g, '');
};

const containsProfanity = (text) => {
    const normalizedText = normalizeText(text);
    return profanityList.some(word => normalizedText.includes(normalizeText(word)));
};

async function fetchAndRenderFollowUps(sessionId, messageWrapper) {
    if (!sessionId) return;

    try {
        const response = await fetch("/api/generate_follow_up", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId })
        });

        if (!response.ok) {
            throw new Error(`Failed to fetch follow-up questions: ${response.statusText}`);
        }

        const questions = await response.json();

        if (questions && questions.length > 0) {
            renderFollowUpQuestions(questions, messageWrapper);
        }
    } catch (error) {
        console.error("Error fetching follow-up questions:", error);
        // Don't show an alert to the user, as this is a non-critical feature.
    }
}

async function sendMessage(isRegenerating = false, keepLeftAligned = false) {
    const message = messageInput.value.trim();

    // --- Profanity Check ---
    if (containsProfanity(message)) {
        showAlert('กรุณาใช้คำสุภาพและหลีกเลี่ยงคำหยาบคาย', 'error');
        return; // Stop the function
    }
    // --- End Profanity Check ---

    toggleSuggestions(false);

    if (!message || !currentChatSessionId) {
        showAlert('Cannot send empty message or no chat selected.', 'warning');
        return;
    }

    if (!isRegenerating) {
        addMessage(message, 'user');
    }
    messageInput.value = '';
    messageInput.disabled = true;
    sendButton.disabled = true;
    messageInput.style.height = 'auto';

    if (isRegenerating) {
        const botMessages = chatMessages.querySelectorAll('.flex.items-start.gap-3:not(.justify-end)');
        if (botMessages.length > 0) {
            botMessages[botMessages.length - 1].remove();
        }
    }

    const botMessageWrapper = addMessage('', 'bot', true);
    const botMessageDiv = botMessageWrapper.querySelector('.message-text-content');
    const toolbar = botMessageWrapper.querySelector('.message-toolbar');
    if (toolbar) toolbar.style.display = 'none';

    let finalSessionId = currentChatSessionId;

    try {
        playReceiveSound();
        const response = await fetch("/api/chat_with_tools", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: message, session_id: currentChatSessionId })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
            throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let messageId = null;

        // --- STREAMING LOGIC STATE ---
        let buffer = '';
        let inTable = false;
        let tableElement = null;
        let tableHeaderParsed = false;
        let tableBodyElement = null;
        let nonTableContentElement = null;
        let inStatusMode = false;
        let statusElement = null;

        const ensureNonTableContentElement = () => {
            if (!nonTableContentElement) {
                nonTableContentElement = document.createElement('div');
                nonTableContentElement.className = 'prose prose-sm dark:prose-invert';
                botMessageDiv.appendChild(nonTableContentElement);
            }
            return nonTableContentElement;
        };

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split('\n');
            buffer = lines.pop(); // Keep the last (potentially incomplete) line in the buffer

            for (const line of lines) {
                if (!line.trim() && !inStatusMode) continue;

                // --- Handle Special Commands ---
                if (line.includes("__STATUS_START__")) {
                    inStatusMode = true;
                    // Ensure left alignment for status
                    if (!botMessageWrapper.classList.contains('align-left-content')) {
                        botMessageWrapper.classList.add('align-left-content');
                    }
                    if (!statusElement) {
                        const typingIndicator = botMessageDiv.querySelector('.typing-indicator');
                        if (typingIndicator) {
                            typingIndicator.style.display = 'none'; // Hide the typing indicator
                        }
                        statusElement = document.createElement('div');
                        statusElement.className = 'status-update-container block text-left';
                        botMessageDiv.appendChild(statusElement); // Append, don't overwrite
                    }
                    continue; // Move to next line
                }

                if (line.includes("__CLEAR__")) {
                    inStatusMode = false;
                    // Switch to center alignment for content
                    botMessageWrapper.classList.remove('align-left-content');

                    if (statusElement) {
                        statusElement.remove();
                        statusElement = null;
                    }
                    // Check if typing indicator was hidden and show it again
                    const typingIndicator = botMessageDiv.querySelector('.typing-indicator');
                    if (typingIndicator && typingIndicator.style.display === 'none') {
                        typingIndicator.style.display = ''; // Show it again
                    }
                    botMessageDiv.innerHTML = ''; // Clear for new content
                    fullResponse = '';
                    inTable = false;
                    tableElement = null;
                    nonTableContentElement = null;
                    continue; // Move to next line
                }

                const idMatch = line.match(/__message_id__:(\d+)/);
                if (idMatch) {
                    messageId = idMatch[1];
                    continue; // Move to next line
                }

                // --- Handle Content ---
                if (inStatusMode && statusElement) {
                    if (line.trim()) { // Only update if line has content
                        statusElement.innerHTML = `
                                    <div class="loading-container">
                                        <div class="loading-spinner"></div>
                                        <div class="loading-text">${line}</div>
                                    </div>
                                `;
                    }
                    continue;
                }

                // Remove typing indicator if it exists and we are receiving content
                const typingIndicator = botMessageDiv.querySelector('.typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }

                // Ensure content is centered (remove left align if it's still there)
                botMessageWrapper.classList.remove('align-left-content');

                fullResponse += line + '\n';

                const isTableLine = line.includes('|');

                if (isTableLine && !inTable) {
                    inTable = true;
                    tableHeaderParsed = false;
                    if (nonTableContentElement) nonTableContentElement.innerHTML = marked.parse(nonTableContentElement.innerText);

                    const tableContainer = document.createElement('div');
                    tableContainer.className = 'table-container';
                    botMessageDiv.appendChild(tableContainer);

                    tableElement = document.createElement('table');
                    tableElement.className = 'streaming-table';
                    tableContainer.appendChild(tableElement);

                    const thead = document.createElement('thead');
                    tableElement.appendChild(thead);
                    const headerRow = document.createElement('tr');
                    thead.appendChild(headerRow);

                    const headers = line.split('|').map(h => h.trim()).filter(h => h);
                    headers.forEach(headerText => {
                        const th = document.createElement('th');
                        th.textContent = headerText;
                        headerRow.appendChild(th);
                    });

                    tableBodyElement = document.createElement('tbody');
                    tableElement.appendChild(tableBodyElement);

                } else if (isTableLine && inTable) {
                    if (!tableHeaderParsed && line.includes('---')) {
                        tableHeaderParsed = true;
                        continue;
                    }
                    if (!tableHeaderParsed) continue; // Still part of header

                    const row = document.createElement('tr');
                    const cells = line.split('|').map(c => c.trim()).slice(1, -1); // Get content between |

                    if (!tableBodyElement) {
                        tableBodyElement = document.createElement('tbody');
                        tableElement.appendChild(tableBodyElement);
                    }

                    cells.forEach(cellText => {
                        const td = document.createElement('td');
                        td.innerHTML = marked.parseInline(cellText);
                        row.appendChild(td);
                    });
                    tableBodyElement.appendChild(row);

                } else if (!isTableLine && line.trim()) {
                    if (inTable) {
                        inTable = false;
                        tableElement = null;
                        tableBodyElement = null;
                        nonTableContentElement = null;
                        // Clear previous content to prevent duplication (Text + Manual Table vs Full Render)
                        botMessageDiv.innerHTML = '';
                    }
                    const container = ensureNonTableContentElement();
                    container.innerHTML = marked.parse(fullResponse) + '<span class="typing-cursor"></span>';
                }

                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }

        // Final cleanup: Remove cursor
        if (nonTableContentElement) {
            nonTableContentElement.innerHTML = marked.parse(fullResponse);
        }


        botMessageDiv.dataset.rawContent = fullResponse;

        if (messageId) {
            botMessageWrapper.dataset.messageId = messageId;
        }

        if (toolbar) toolbar.style.display = 'flex';
        chatContainer.scrollTop = chatContainer.scrollHeight;

    } catch (error) {
        const errorMessage = `ขออภัย, เกิดข้อผิดพลาด: ${error.message}`;
        botMessageDiv.innerHTML = `<p class="text-red-500">${errorMessage}</p>`;
        botMessageDiv.dataset.rawContent = errorMessage;
        if (toolbar) toolbar.style.display = 'flex';
        console.error('API Error:', error);
        showAlert('An error occurred while sending the message.', 'error');
    } finally {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
        if (botMessageWrapper && !keepLeftAligned) {
            botMessageWrapper.classList.remove('align-left-content');
        }
        fetchAndRenderFollowUps(finalSessionId, botMessageWrapper);
    }
}

async function sendFeedback(messageId, feedbackType) {
    try {
        await fetch("/chat/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message_id: messageId, feedback_type: feedbackType })
        });
    } catch (error) {
        console.error('Error sending feedback:', error);
        showAlert('Failed to send feedback.', 'error');
    }
}

async function getLastUserMessage() {
    if (!currentChatSessionId) return null;
    try {
        const response = await fetch(`/chat/sessions/${currentChatSessionId}/last_user_message`);
        if (!response.ok) throw new Error('Failed to get last user message');
        return await response.json();
    } catch (error) {
        console.error('Error getting last user message:', error);
        return null;
    }
}

async function fetchSuggestions(messageWrapper) {
    // This feature is not supported by the new tool-based chat endpoint yet.
    return;
}

function renderFollowUpQuestions(questions, messageWrapper) {
    const suggestionsContainer = messageWrapper.querySelector('.message-suggestions-container');
    if (!suggestionsContainer) return;

    suggestionsContainer.innerHTML = ''; // Clear any existing content

    const header = document.createElement('p');
    header.className = 'follow-up-header';
    header.textContent = 'คุณอาจจะอยากถามต่อว่า:';
    suggestionsContainer.appendChild(header);

    const buttonWrapper = document.createElement('div');
    buttonWrapper.className = 'follow-up-buttons-wrapper';

    questions.forEach(question => {
        if (typeof question !== 'string' || question.trim() === '') return;

        const button = document.createElement('button');
        button.className = 'follow-up-question';
        button.textContent = question;
        button.onclick = () => {
            suggestionsContainer.innerHTML = '';
            sendMessageFromSuggestion(question);
        };
        buttonWrapper.appendChild(button);
    });

    suggestionsContainer.appendChild(buttonWrapper);
}

function renderSuggestions(suggestions, messageWrapper) {
    // This feature is not supported by the new tool-based chat endpoint yet.
    return;
}

async function sendMessageFromSuggestion(suggestionText, isInitialSuggestion = false) {
    messageInput.value = suggestionText;
    await sendMessage(false, isInitialSuggestion);
}

sendButton.addEventListener('click', () => sendMessage());
messageInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    const newHeight = Math.min(messageInput.scrollHeight, 200);
    messageInput.style.height = `${newHeight}px`;
    messageInput.style.overflowY = newHeight >= 200 ? 'scroll' : 'hidden';
    sendButton.disabled = messageInput.value.trim() === '';
});

sendButton.disabled = true;




document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    loadChatSessions();
    messageInput.focus();

    // --- Inline Chat Title Editing ---
    chatTitle.addEventListener('click', () => {
        if (!currentChatSessionId || chatTitle.querySelector('input')) return;

        const originalTitle = chatTitle.textContent;
        const input = document.createElement('input');
        input.type = 'text';
        input.value = originalTitle;
        input.className = 'bg-transparent text-xl font-semibold w-full focus:outline-none p-0 m-0 border-b-2 border-transparent focus:border-yellow-500';
        input.style.color = 'var(--text-primary)';

        chatTitle.innerHTML = ''; // Clear the h1
        chatTitle.appendChild(input);
        input.focus();
        input.select();

        const finishEditing = async (saveChanges) => {
            const newTitle = input.value.trim();
            // Clean up event listeners
            input.removeEventListener('blur', onBlur);
            input.removeEventListener('keydown', onKeydown);

            chatTitle.innerHTML = ''; // Clear the input
            chatTitle.textContent = originalTitle; // Temporarily revert

            if (saveChanges && newTitle && newTitle !== originalTitle) {
                chatTitle.textContent = newTitle; // Optimistic update
                try {
                    await saveChatSessionTitle(currentChatSessionId, newTitle);
                    await loadChatSessions(); // Refresh sidebar and confirm title
                } catch (error) {
                    chatTitle.textContent = originalTitle; // Revert on error
                    showAlert('Failed to rename chat.', 'error');
                }
            } else {
                chatTitle.textContent = originalTitle; // Revert if no change or cancelled
            }
        };

        const onBlur = () => finishEditing(true);
        const onKeydown = (e) => {
            if (e.key === 'Enter') finishEditing(true);
            if (e.key === 'Escape') finishEditing(false);
        };

        input.addEventListener('blur', onBlur);
        input.addEventListener('keydown', onKeydown);
    });

    const feedbackButton = document.getElementById('feedback-button');
    const feedbackModal = document.getElementById('feedback-modal');
    const cancelFeedbackBtn = document.getElementById('cancel-feedback-btn');
    const closeFeedbackBtn = document.getElementById('close-feedback-modal-btn');
    const feedbackForm = document.getElementById('feedbackForm');

    function toggleFeedbackModal(show) {
        feedbackModal.classList.toggle('hidden', !show);
    }

    if (feedbackButton) feedbackButton.addEventListener('click', () => toggleFeedbackModal(true));
    if (cancelFeedbackBtn) cancelFeedbackBtn.addEventListener('click', () => toggleFeedbackModal(false));
    if (closeFeedbackBtn) closeFeedbackBtn.addEventListener('click', () => toggleFeedbackModal(false));
    if (feedbackModal) feedbackModal.addEventListener('click', (e) => { if (e.target === feedbackModal) toggleFeedbackModal(false); });

    if (feedbackForm) {
        feedbackForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(feedbackForm);
            const data = {
                feedback_type: formData.get('feedback_type'),
                message: formData.get('message'),
                page_url: window.location.href
            };

            if (!data.message.trim()) {
                showAlert('กรุณากรอกข้อความของท่าน', 'error');
                return;
            }

            try {
                const response = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to submit feedback.');
                }
                const result = await response.json();
                showAlert(result.message, 'success');
                toggleFeedbackModal(false);
                feedbackForm.reset();
            } catch (error) {
                showAlert(error.message || 'ไม่สามารถส่งข้อมูลได้ กรุณาลองใหม่อีกครั้ง', 'error');
            }
        });
    }
});

window.addEventListener('click', (e) => {
    if (!e.target.closest('.chat-action-button')) {
        document.querySelectorAll('.chat-action-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});