// Configure marked.js to sanitize HTML to prevent XSS attacks
        marked.setOptions({
            sanitize: false // Allow HTML to be rendered for tables
        });
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const suggestionButtonsContainer = document.getElementById('suggestionButtons');

        const popup = document.getElementById('chatPopup');
        const openPopupButton = document.getElementById('openChatPopup');
        const closePopupButton = document.getElementById('closeChatPopup');
        const popupChatMessages = document.getElementById('popupChatMessages');
        const popupMessageInput = document.getElementById('popupMessageInput');
        const popupSendButton = document.getElementById('popupSendButton');
        const popupSuggestionButtons = document.getElementById('popupSuggestionButtons');
        const backToTopBtn = document.getElementById('backToTopBtn');

        let chatHistory = [];

        // --- Profanity Filter and Custom Alert Logic (Global Scope) ---
        const profanityList = [
            'ควย', 'สัส', 'เหี้ย', 'เย็ด', 'แม่ง', 'มึง', 'กู', 'ชิบหาย', 'หี', 'แตด', 
            'ไอ้สัตว์', 'อีสัตว์', 'ไอสัส', 'อีสัส', 'ไอ้เหี้ย', 'อีเหี้ย', 'ไอ้ควย', 'อีควย',
            // Variations
            'สัด', 'สาด', 'เฮี้ย', 'here', 'kuay', 'suck', 'fuck', 'f-u-c-k', 's-h-i-t', 'shit'
        ];

        const normalizeText = (text) => {
            return text.toLowerCase().replace(/[^a-zก-๙0-9]/g, '');
        };

        const containsProfanity = (text) => {
            const normalizedText = normalizeText(text);
            return profanityList.some(word => normalizedText.includes(normalizeText(word)));
        };

        const showCustomAlert = (title, message, type) => {
            const customAlertModal = document.getElementById('custom-alert-modal');
            const alertIcon = document.getElementById('custom-alert-icon');
            const alertTitle = document.getElementById('custom-alert-title');
            const alertMessage = document.getElementById('custom-alert-message');
            
            if(!customAlertModal || !alertIcon || !alertTitle || !alertMessage) return;

            alertTitle.textContent = title;
            alertMessage.textContent = message;

            if (type === 'success') {
                alertIcon.innerHTML = '<i class="fas fa-check-circle text-green-500"></i>';
            } else if (type === 'error') {
                alertIcon.innerHTML = '<i class="fas fa-times-circle text-red-500"></i>';
            } else {
                alertIcon.innerHTML = '<i class="fas fa-info-circle text-blue-500"></i>';
            }

            customAlertModal.classList.remove('hidden');
        };

        function addMessage(content, sender, stream = false) {
            const createMessageWrapper = () => {
                const messageWrapper = document.createElement('div');
                messageWrapper.className = 'message-fade-in flex items-start gap-3';
                if (sender === 'user') {
                    messageWrapper.classList.add('justify-end');
                    messageWrapper.innerHTML = `<div class="p-3 rounded-xl rounded-br-lg shadow-md max-w-xl prose prose-sm prose-invert" style="background-color: var(--chat-bg-user); color: var(--chat-text-user);">${marked.parse(content)}</div>`;
                } else {
                    messageWrapper.innerHTML = `
                        <div class="flex flex-col items-start w-full">
                            <div class="ai-message-content p-3 rounded-xl rounded-bl-lg max-w-xl relative" style="background-color: transparent; color: var(--chat-text-bot);">
                                <!-- Content will be inserted here -->
                            </div>
                        </div>`;
                    const textContentDiv = messageWrapper.querySelector('.ai-message-content'); // Select the parent div
                    if (stream) {
                        // Use the new status animation right away
                        textContentDiv.innerHTML = `
                            <div class="loading-container">
                                <div class="loading-spinner"></div>
                                <div class="loading-text">กำลังค้นหา...</div>
                            </div>`;
                    } else {
                        textContentDiv.innerHTML = marked.parse(content);
                    }
                }
                return messageWrapper;
            };

            const mainMsg = createMessageWrapper();
            chatMessages.appendChild(mainMsg);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            const popupMsg = mainMsg.cloneNode(true);
            popupChatMessages.appendChild(popupMsg);
            popupChatMessages.scrollTop = popupChatMessages.scrollHeight;

            if (sender === 'bot') {
                return {
                    main: mainMsg.querySelector('.ai-message-content'),
                    popup: popupMsg.querySelector('.ai-message-content')
                };
            }
            return { main: mainMsg, popup: popupMsg };
        }

        function typeBotResponse(element, text, container, onComplete) {
            if (!element) return;

            element.innerHTML = '<p><span class="typed-text"></span><span class="typing-cursor">|</span></p>';
            const typedTextSpan = element.querySelector('.typed-text');
            const cursorSpan = element.querySelector('.typing-cursor');

            let charIndex = 0;
            const typeCharacter = () => {
                if (charIndex < text.length) {
                    typedTextSpan.textContent += text.charAt(charIndex);
                    charIndex++;
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                    setTimeout(typeCharacter, 30);
                } else {
                    if (cursorSpan) {
                        cursorSpan.style.display = 'none';
                    }
                    if (onComplete) {
                        onComplete();
                    }
                }
            };
            setTimeout(typeCharacter, 100);
        }

        async function sendMessage() {
            const message = messageInput.value.trim() || popupMessageInput.value.trim();
            if (!message) return;

            // --- Profanity Check ---
            if (containsProfanity(message)) {
                showCustomAlert('ข้อผิดพลาด', 'กรุณาใช้คำสุภาพและหลีกเลี่ยงคำหยาบคาย', 'error');
                return; // Stop the function
            }
            // --- End Profanity Check ---

            chatHistory.push({ role: 'user', content: message });

            suggestionButtonsContainer.style.display = 'none';
            popupSuggestionButtons.style.display = 'none';

            addMessage(message, 'user');
            
            messageInput.value = '';
            popupMessageInput.value = '';
            messageInput.disabled = true;
            sendButton.disabled = true;
            popupMessageInput.disabled = true;
            popupSendButton.disabled = true;

            const botMessageDivs = addMessage('', 'bot', true);

            try {
                const response = await fetch("/api/chat_with_tools", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        question: message,
                        history: chatHistory
                    })
                });

                if (!response.ok) {
                    const errText = await response.text();
                    throw new Error(errText || `HTTP error! status: ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullResponse = '';
                let inStatusMode = false;
                let statusElement = null;
                let popupStatusElement = null;

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    let chunkText = decoder.decode(value, { stream: true });

                    if (chunkText.includes("__STATUS_START__")) {
                        inStatusMode = true;
                        // Clear the initial 3-dot loader
                        botMessageDivs.main.innerHTML = '<div class="status-update-container"></div>';
                        botMessageDivs.popup.innerHTML = '<div class="status-update-container"></div>';
                        statusElement = botMessageDivs.main.querySelector('.status-update-container');
                        popupStatusElement = botMessageDivs.popup.querySelector('.status-update-container');
                        chunkText = chunkText.replace("__STATUS_START__", "");
                    }

                    if (chunkText.includes("__CLEAR__")) {
                        inStatusMode = false;
                        if (statusElement) {
                            statusElement.remove();
                            statusElement = null;
                        }
                        if (popupStatusElement) {
                            popupStatusElement.remove();
                            popupStatusElement = null;
                        }
                        fullResponse = "";
                        botMessageDivs.main.innerHTML = "";
                        botMessageDivs.popup.innerHTML = "";
                        chunkText = chunkText.replace(/__CLEAR__/g, "");
                    }

                    if (chunkText) {
                        if (inStatusMode && statusElement) {
                            const lines = chunkText.split('\n').filter(line => line.trim() !== '');
                            if(lines.length > 0) {
                                const statusHTML = `
                                    <div class="loading-container">
                                        <div class="loading-spinner"></div>
                                        <div class="loading-text">${lines.join('<br>')}</div>
                                    </div>
                                `;
                                statusElement.innerHTML = statusHTML;
                                popupStatusElement.innerHTML = statusHTML;
                            }
                        } else {
                             if (statusElement) { // If we were in status mode, clear it now
                                statusElement.remove();
                                statusElement = null;
                                popupStatusElement.remove();
                                popupStatusElement = null;
                            }
                            if (chunkText.startsWith('data:')) {
                                const jsonString = chunkText.substring(5);
                                try {
                                    const jsonData = JSON.parse(jsonString);
                                    if (jsonData.type === 'promo_card') {
                                        const promoCardHTML = renderPromoCard(jsonData.data);
                                        botMessageDivs.main.innerHTML = promoCardHTML;
                                        botMessageDivs.popup.innerHTML = promoCardHTML;
                                        // Since this is a special card, we don't want to append more text
                                        fullResponse = ''; // Clear the response
                                        break; // Exit the loop
                                    }
                                } catch (e) {
                                    // Not a valid JSON, so treat it as regular text
                                    fullResponse += chunkText;
                                    botMessageDivs.main.innerHTML = marked.parse(fullResponse);
                                    botMessageDivs.popup.innerHTML = marked.parse(fullResponse);
                                }
                            } else {
                                fullResponse += chunkText;
                                botMessageDivs.main.innerHTML = marked.parse(fullResponse);
                                botMessageDivs.popup.innerHTML = marked.parse(fullResponse);
                            }
                        }
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        popupChatMessages.scrollTop = popupChatMessages.scrollHeight;
                    }
                }

                if (fullResponse) {
                    chatHistory.push({ role: 'assistant', content: fullResponse.trim() });
                }

            } catch (error) {
                const errorMessage = `<p class="text-red-500">ขออภัย, เกิดข้อผิดพลาด: ${error.message}</p>`;
                botMessageDivs.main.innerHTML = errorMessage;
                botMessageDivs.popup.innerHTML = errorMessage;
                chatHistory.pop(); // Remove the user message that caused the error
            } finally {
                messageInput.disabled = false;
                sendButton.disabled = false;
                popupMessageInput.disabled = false;
                popupSendButton.disabled = false;
                messageInput.focus();
            }
        }

        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        popupSendButton.addEventListener('click', sendMessage);
        popupMessageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // --- Initial Load and Animations ---
        const typeWelcomeMessage = () => {
            const welcomeText = "สวัสดีครับ! สนใจโปรโมชั่นอินเทอร์เน็ตแบบไหนดีครับ? บ้าน, มือถือ หรือเน็ตสำหรับเล่นเกม?";
            const botMessageDivs = addMessage("", 'bot');

            const typeInElement = (element, container) => {
                if (!element) return;

                element.innerHTML = '<p><span class="typed-text"></span><span class="typing-cursor">|</span></p>';
                const typedTextSpan = element.querySelector('.typed-text');
                const cursorSpan = element.querySelector('.typing-cursor');

                let charIndex = 0;
                const typeCharacter = () => {
                    if (charIndex < welcomeText.length) {
                        typedTextSpan.textContent += welcomeText.charAt(charIndex);
                        charIndex++;
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                        }
                        setTimeout(typeCharacter, 50); // Typing speed (ms)
                    } else {
                        if (cursorSpan) {
                            cursorSpan.style.display = 'none'; // Hide cursor when done
                        }
                    }
                };
                setTimeout(typeCharacter, 500); // Initial delay before typing starts
            };
            
            typeInElement(botMessageDivs.main, chatMessages);
            typeInElement(botMessageDivs.popup, popupChatMessages);
        };

        document.addEventListener('DOMContentLoaded', () => {
            // --- Scroll-based Animations ---
            const scrollObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        if (entry.target.id === 'chatbot' && !window.welcomeMessagePlayed) {
                            typeWelcomeMessage();
                            window.welcomeMessagePlayed = true;
                        }
                        // Trigger SVG drawing animation
                        if (entry.target.classList.contains('drawing-icon')) {
                            entry.target.classList.add('is-drawing');
                        }
                    } else {
                        entry.target.classList.remove('is-visible');
                        // Reset SVG drawing animation
                        if (entry.target.classList.contains('drawing-icon')) {
                            entry.target.classList.remove('is-drawing');
                        }
                    }
                });
            }, { 
                threshold: 0.2
            });

            const elementsToAnimate = document.querySelectorAll('.scroll-animate-left, .scroll-animate-up, .scroll-animate-right, .scroll-animate-down, .scroll-animate-zoom-in, .drawing-icon');
            elementsToAnimate.forEach(el => scrollObserver.observe(el));

            const chatbotSection = document.getElementById('chatbot');
            if (chatbotSection) {
                scrollObserver.observe(chatbotSection);
            }

            // --- Back to Top Button ---
            window.addEventListener("scroll", () => {
                if (window.scrollY > 100) {
                    backToTopBtn.classList.add("show");
                } else {
                    backToTopBtn.classList.remove("show");
                }
            });

            backToTopBtn.addEventListener("click", () => {
                const duration = 800; // Scroll duration in milliseconds
                const start = window.scrollY;
                const distance = -start;
                let startTime = null;

                function animation(currentTime) {
                    if (startTime === null) startTime = currentTime;
                    const timeElapsed = currentTime - startTime;
                    
                    // Easing function (ease-in-out-quad)
                    const t = timeElapsed / duration;
                    const easedT = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
                    const run = start + distance * easedT;

                    window.scrollTo(0, run);

                    if (timeElapsed < duration) {
                        requestAnimationFrame(animation);
                    }
                }

                requestAnimationFrame(animation);
            });

            // --- Fetch FAQs ---
            const fetchFAQs = async () => {
                try {
                    const response = await fetch('/chat/faq');
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    const faqs = await response.json();
                    const faqContainer = document.getElementById('faq-container');
                    if (faqContainer && faqs.length > 0) {
                        faqContainer.innerHTML = faqs.map(faq => `
                            <div class="bg-white dark:bg-gray-700 p-4 rounded-lg shadow-md cursor-pointer feature-card" onclick="setChatQuestion('${faq}')">
                                <p class="font-semibold text-nt-blue dark:text-white">${faq}</p>
                            </div>
                        `).join('');
                    } else if (faqContainer) {
                        document.getElementById('faq-section').style.display = 'none';
                    }
                } catch (error) {
                    console.error("Could not fetch FAQs:", error);
                    const faqSection = document.getElementById('faq-section');
                    if (faqSection) {
                        faqSection.style.display = 'none';
                    }
                }
            };

            const fetchReviewSummary = async () => {
                const testimonialsContainer = document.getElementById('testimonials-container');
                const satisfactionSummary = document.getElementById('satisfaction-summary');
                const percentageElement = document.getElementById('satisfaction-percentage');
                const totalCountElement = document.getElementById('feedback-total-count');

                if (!testimonialsContainer || !satisfactionSummary || !percentageElement || !totalCountElement) return;

                try {
                    const response = await fetch('/api/review-summary');
                    if (!response.ok) throw new Error('Failed to fetch review summary');
                    const summary = await response.json();

                    // Update satisfaction stats
                    if (summary.total_feedback_count > 0) {
                        percentageElement.textContent = `${summary.satisfaction_percentage}%`;
                        totalCountElement.textContent = `(จาก ${summary.total_feedback_count} ฟีดแบ็ก)`;
                        satisfactionSummary.style.display = 'block';
                    }

                    // Update testimonials
                    testimonialsContainer.innerHTML = ''; // Clear loading/previous state
                    if (summary.latest_reviews.length === 0) {
                        testimonialsContainer.innerHTML = `<div class="text-center text-gray-500 dark:text-gray-400 col-span-full">ยังไม่มีรีวิวในขณะนี้</div>`;
                    } else {
                        summary.latest_reviews.forEach(review => {
                            const reviewCard = document.createElement('div');
                            reviewCard.className = 'bg-white dark:bg-gray-700 p-6 rounded-lg shadow-md feature-card';
                            reviewCard.innerHTML = `
                                <p class="text-gray-600 dark:text-gray-300 mb-4">"${review.comment}"</p>
                                <p class="text-right font-semibold text-nt-blue dark:text-yellow-300">${review.username}</p>
                            `;
                            testimonialsContainer.appendChild(reviewCard);
                        });
                    }
                } catch (error) {
                    console.error('Could not fetch review summary:', error);
                    testimonialsContainer.innerHTML = `<div class="text-center text-red-500 col-span-full">เกิดข้อผิดพลาดในการโหลดรีวิว</div>`;
                }
            };

            const customAlertModal = document.getElementById('custom-alert-modal');
            const customAlertCloseBtn = document.getElementById('custom-alert-close-btn');

            if(customAlertCloseBtn) customAlertCloseBtn.addEventListener('click', () => customAlertModal.classList.add('hidden'));
            if(customAlertModal) customAlertModal.addEventListener('click', (e) => {
                if (e.target === customAlertModal) {
                    customAlertModal.classList.add('hidden');
                }
            });

            const handleReviewSubmit = async (event) => {
                event.preventDefault();
                const commentTextarea = document.getElementById('review-comment');
                const comment = commentTextarea.value.trim();

                if (!comment) {
                    showCustomAlert('ข้อผิดพลาด', 'กรุณากรอกความคิดเห็นของคุณ', 'error');
                    return;
                }

                if (containsProfanity(comment)) {
                    showCustomAlert('ข้อผิดพลาด', 'กรุณาใช้คำสุภาพและหลีกเลี่ยงคำหยาบคาย', 'error');
                    return;
                }

                try {
                    const response = await fetch('/api/reviews', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ comment: comment })
                    });

                    if (response.status === 401) {
                        throw new Error('คุณต้องเข้าสู่ระบบก่อนส่งความคิดเห็น');
                    }

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to submit review');
                    }

                    commentTextarea.value = '';
                    document.getElementById('review-modal').classList.add('hidden');
                    showCustomAlert('สำเร็จ!', 'รีวิวของคุณถูกส่งเรียบร้อยแล้ว ขอบคุณสำหรับความคิดเห็นครับ', 'success');
                    fetchReviewSummary();

                } catch (error) {
                    console.error('Review submission error:', error);
                    showCustomAlert('เกิดข้อผิดพลาด', error.message, 'error');
                }
            };

            fetchFAQs();
            fetchReviewSummary();

            // --- Modal Listeners ---
            const reviewModal = document.getElementById('review-modal');
            const openBtn = document.getElementById('open-review-modal-btn');
            const closeBtn = document.getElementById('close-review-modal-btn');
            const reviewForm = document.getElementById('review-form');

            if(openBtn) {
                openBtn.addEventListener('click', () => reviewModal.classList.remove('hidden'));
            }
            if(closeBtn) {
                closeBtn.addEventListener('click', () => reviewModal.classList.add('hidden'));
            }
            if(reviewModal) {
                reviewModal.addEventListener('click', (e) => {
                    if (e.target === reviewModal) {
                        reviewModal.classList.add('hidden');
                    }
                });
            }
            if (reviewForm) {
                reviewForm.addEventListener('submit', handleReviewSubmit);
            }

            // --- Hamburger Menu Toggle ---
            const menuToggle = document.getElementById('mobile-menu-button');
            const menu = document.getElementById('mobile-menu');
            menuToggle.addEventListener('click', () => {
                menuToggle.classList.toggle('active');
                if (menu.style.maxHeight) {
                    menu.style.maxHeight = null;
                } else {
                    menu.style.maxHeight = menu.scrollHeight + "px";
                }
            });

            // --- Feedback Modal Logic ---
            const feedbackModal = document.getElementById('feedback-modal');
            const openFeedbackBtn = document.getElementById('open-feedback-modal-btn');
            const closeFeedbackBtn = document.getElementById('close-feedback-modal-btn');
            const feedbackForm = document.getElementById('feedback-form');

            if(openFeedbackBtn) {
                openFeedbackBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    feedbackModal.classList.remove('hidden');
                });
            }
            if(closeFeedbackBtn) {
                closeFeedbackBtn.addEventListener('click', () => feedbackModal.classList.add('hidden'));
            }
            if(feedbackModal) {
                feedbackModal.addEventListener('click', (e) => {
                    if (e.target === feedbackModal) {
                        feedbackModal.classList.add('hidden');
                    }
                });
            }

            if(feedbackForm) {
                feedbackForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = new FormData(feedbackForm);
                    const data = {
                        feedback_type: formData.get('feedback_type'),
                        message: formData.get('message'),
                        page_url: window.location.href
                    };

                    if (!data.message.trim()) {
                        showCustomAlert('ข้อผิดพลาด', 'กรุณากรอกข้อความของท่าน', 'error');
                        return;
                    }

                    try {
                        const response = await fetch('/api/feedback', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });

                        if (!response.ok) {
                            throw new Error('Failed to submit feedback.');
                        }

                        feedbackForm.reset();
                        feedbackModal.classList.add('hidden');
                        showCustomAlert('ขอบคุณครับ', 'เราได้รับข้อมูลของท่านเรียบร้อยแล้ว', 'success');

                    } catch (error) {
                        console.error('Feedback submission error:', error);
                        showCustomAlert('เกิดข้อผิดพลาด', 'ไม่สามารถส่งข้อมูลได้ กรุณาลองใหม่อีกครั้ง', 'error');
                    }
                });
            }

            document.getElementById('suggestion1').addEventListener('click', () => sendMessageFromSuggestion('แนะนำแพ็กเกจอินเทอร์เน็ตหน่อย'));
            document.getElementById('suggestion2').addEventListener('click', () => sendMessageFromSuggestion('แพ็กเกจสำหรับเล่นเกมมีอะไรบ้าง'));
            document.getElementById('suggestion3').addEventListener('click', () => sendMessageFromSuggestion('อยากได้เน็ตบ้านพร้อมกล่องทีวี'));
            document.getElementById('suggestion4').addEventListener('click', () => sendMessageFromSuggestion('โปรโมชั่นล่าสุดมีอะไรบ้าง'));

            openPopupButton.addEventListener('click', () => {
                popup.classList.remove('hidden');
            });

            closePopupButton.addEventListener('click', () => {
                popup.classList.add('hidden');
            });
        });

        function renderPromoCard(data) {
            const features = data.features.map(feature => `<li><i class="fas fa-check-circle"></i>${feature}</li>`).join('');
            return `
                <div class="promo-card">
                    <img src="${data.image_url}" alt="${data.name}">
                    <h3>${data.name}</h3>
                    <div class="price">${data.price}</div>
                    <ul class="features">
                        ${features}
                    </ul>
                </div>
            `;
        }

        function sendMessageFromSuggestion(question) {
            messageInput.value = question;
            popupMessageInput.value = question;
            sendMessage();
        }

        // Function to set question in chatbox
        function setChatQuestion(question) {
            const messageInput = document.getElementById('messageInput');
            messageInput.value = question;
            messageInput.focus();
            document.getElementById('chatbot').scrollIntoView({ behavior: 'smooth' });
        }

        // Particle Canvas
        const canvas = document.getElementById('particle-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = canvas.parentElement.offsetHeight;

        let particlesArray;

        const mouse = {
            x: null,
            y: null,
            radius: (canvas.height/100) * (canvas.width/100)
        }

        window.addEventListener('mousemove',
            function(event) {
                let rect = canvas.getBoundingClientRect();
                mouse.x = event.clientX - rect.left;
                mouse.y = event.clientY - rect.top;
            }
        );

        class Particle {
            constructor(x, y, directionX, directionY, size, color) {
                this.x = x;
                this.y = y;
                this.directionX = directionX;
                this.directionY = directionY;
                this.size = size;
                this.color = color;
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2, false);
                ctx.fillStyle = this.color;
                ctx.fill();
            }
            update() {
                if (this.x > canvas.width || this.x < 0) {
                    this.directionX = -this.directionX;
                }
                if (this.y > canvas.height || this.y < 0) {
                    this.directionY = -this.directionY;
                }

                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let distance = Math.sqrt(dx*dx + dy*dy);
                if (distance < mouse.radius + this.size){
                    if(mouse.x < this.x && this.x < canvas.width - this.size * 10) {
                        this.x += 5;
                    }
                    if(mouse.x > this.x && this.x > this.size * 10) {
                        this.x -= 5;
                    }
                    if(mouse.y < this.y && this.y < canvas.height - this.size * 10) {
                        this.y += 5;
                    }
                    if(mouse.y > this.y && this.y > this.size * 10) {
                        this.y -= 5;
                    }
                }
                this.x += this.directionX;
                this.y += this.directionY;
                this.draw();
            }
        }

        function init() {
            particlesArray = [];
            let numberOfParticles = (canvas.height * canvas.width) / 9000;
            let colors = document.documentElement.classList.contains('dark') 
                ? ['#4a90e2', '#ffc800', '#f5f5f5'] 
                : ['#003b7a', '#4a90e2', '#ffc800'];
            for (let i = 0; i < numberOfParticles; i++) {
                let size = (Math.random() * 2) + 1;
                let x = (Math.random() * ((canvas.width - size * 2) - (size * 2)) + size * 2);
                let y = (Math.random() * ((canvas.height - size * 2) - (size * 2)) + size * 2);
                let directionX = (Math.random() * .4) - 0.2;
                let directionY = (Math.random() * .4) - 0.2;
                let color = colors[Math.floor(Math.random() * colors.length)];

                particlesArray.push(new Particle(x, y, directionX, directionY, size, color));
            }
        }

        function connect(){
            let opacityValue = 1;
            for (let a = 0; a < particlesArray.length; a++) {
                for (let b = a; b < particlesArray.length; b++) {
                    let distance = ((particlesArray[a].x - particlesArray[b].x) * (particlesArray[a].x - particlesArray[b].x))
                    + ((particlesArray[a].y - particlesArray[b].y) * (particlesArray[a].y - particlesArray[b].y));

                    if (distance < (canvas.width/7) * (canvas.height/7)) {
                        opacityValue = 1 - (distance/20000);
                        let strokeStyle = document.documentElement.classList.contains('dark') ? 'rgba(74,144,226,' + opacityValue + ')' : 'rgba(0,59,122,' + opacityValue + ')';
                        ctx.strokeStyle = strokeStyle;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(particlesArray[a].x, particlesArray[a].y);
                        ctx.lineTo(particlesArray[b].x, particlesArray[b].y);
                        ctx.stroke();
                    }
                }
            }
        }

        function animate() {
            requestAnimationFrame(animate);
            ctx.clearRect(0,0,canvas.width, canvas.height);

            for (let i = 0; i < particlesArray.length; i++) {
                particlesArray[i].update();
            }
            connect();
        }

        window.addEventListener('resize',
            function(){
                canvas.width = window.innerWidth;
                canvas.height = canvas.parentElement.offsetHeight;
                mouse.radius = (canvas.height/100) * (canvas.width/100);
                init();
            }
        )

        window.addEventListener('mouseout',
            function(){
                mouse.x = undefined;
                mouse.y = undefined;
            }
        )

        function createStars() {
            const starsContainer = document.getElementById('stars');
            if (!starsContainer) return;
            const starCount = 300; // Increased star count for a fuller sky
            for (let i = 0; i < starCount; i++) {
                const star = document.createElement('div');
                star.classList.add('star', 'floating-animation'); // Added floating-animation
                const size = Math.random() * 3 + 1; // Random size between 1px and 4px
                star.style.width = `${size}px`;
                star.style.height = `${size}px`;
                star.style.top = `${Math.random() * 100}%`;
                star.style.left = `${Math.random() * 100}%`;
                star.style.animationDelay = `${Math.random() * 4}s`; // Random delay for twinkling (0 to 4s)
                starsContainer.appendChild(star);
            }
        }

        init();
        animate();
        createStars();

        // --- Theme Toggle ---
        const themeToggleBtn = document.getElementById('theme-toggle');
        const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
        const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');

        // Change the icons inside the button based on previous settings
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            themeToggleLightIcon.classList.remove('hidden');
            themeToggleDarkIcon.classList.add('hidden');
        } else {
            themeToggleDarkIcon.classList.remove('hidden');
            themeToggleLightIcon.classList.add('hidden');
        }

        themeToggleBtn.addEventListener('click', function() {

            // toggle icons inside button
            themeToggleDarkIcon.classList.toggle('hidden');
            themeToggleLightIcon.classList.toggle('hidden');

            // if set via local storage previously
            if (localStorage.getItem('color-theme')) {
                if (localStorage.getItem('color-theme') === 'light') {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                }

            // if NOT set via local storage previously
            } else {
                if (document.documentElement.classList.contains('dark')) {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                } else {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                }
            }
            // re-initialize particles with new colors
            init();
            // Toggle starry sky
            const stars = document.getElementById('stars');
            if (document.documentElement.classList.contains('dark')) {
                stars.style.display = 'block';
            } else {
                stars.style.display = 'none';
            }
        });

        // --- Cookie Consent Logic ---
        document.addEventListener('DOMContentLoaded', () => {
            const banner = document.getElementById('cookie-consent-banner');
            const acceptBtn = document.getElementById('accept-cookie-consent');

            if (!localStorage.getItem('cookie_consent_accepted')) {
                // Use a timeout to ensure the page has rendered before sliding up the banner
                setTimeout(() => {
                    banner.classList.remove('hidden');
                    banner.classList.remove('translate-y-full');
                }, 500);
            }

            acceptBtn.addEventListener('click', () => {
                localStorage.setItem('cookie_consent_accepted', 'true');
                banner.classList.add('translate-y-full');
                // Optional: hide the banner after the transition completes
                setTimeout(() => {
                    banner.classList.add('hidden');
                }, 500);
            });
        });