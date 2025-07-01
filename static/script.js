class ChatApp {
    constructor() {
        this.currentConversationId = null;
        this.isLoading = false;
        this.initializeElements();
        this.bindEvents();
        this.loadConversations();
    }

    // 初始化DOM元素
    initializeElements() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.conversationHistory = document.getElementById('conversation-history');
        this.loading = document.getElementById('loading');
    }

    // 绑定事件监听器
    bindEvents() {
        // 发送按钮点击事件
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // 输入框回车事件
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 新对话按钮点击事件
        this.newChatBtn.addEventListener('click', () => this.startNewConversation());

        // 输入框输入事件（动态调整发送按钮状态）
        this.chatInput.addEventListener('input', () => {
            this.updateSendButtonState();
        });
    }

    // 更新发送按钮状态
    updateSendButtonState() {
        const hasText = this.chatInput.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isLoading;
    }

    // 显示/隐藏加载动画
    showLoading(show = true) {
        this.isLoading = show;
        this.loading.classList.toggle('hidden', !show);
        this.updateSendButtonState();
    }

    // 发送消息
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isLoading) return;

        // 清空输入框并显示用户消息
        this.chatInput.value = '';
        this.addMessage(message, 'user');
        this.updateSendButtonState();

        // 显示加载状态
        this.showLoading(true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.currentConversationId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // 更新当前对话ID
            this.currentConversationId = data.conversation_id;
            
            // 显示AI回复
            this.addMessage(data.response, 'bot');
            
            // 重新加载对话列表
            this.loadConversations();

        } catch (error) {
            console.error('发送消息失败:', error);
            this.addMessage('抱歉，发送消息时出现错误，请稍后再试。', 'bot', true);
        } finally {
            this.showLoading(false);
        }
    }

    // 添加消息到聊天界面
    addMessage(content, type, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (isError) {
            messageContent.style.background = '#ffe6e6';
            messageContent.style.color = '#d63031';
            messageContent.style.border = '1px solid #fab1a0';
        }
        
        // 处理换行和特殊字符
        messageContent.innerHTML = this.formatMessage(content);
        
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        
        // 滚动到底部
        this.scrollToBottom();
    }

    // 格式化消息内容
    formatMessage(content) {
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    // 滚动到聊天底部
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    // 开始新对话
    async startNewConversation() {
        try {
            const response = await fetch('/api/conversation/new', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // 重置当前对话
            this.currentConversationId = data.conversation_id;
            this.clearMessages();
            this.showWelcomeMessage();
            
            // 重新加载对话列表
            this.loadConversations();

        } catch (error) {
            console.error('创建新对话失败:', error);
            alert('创建新对话失败，请稍后再试。');
        }
    }

    // 清空聊天消息
    clearMessages() {
        this.chatMessages.innerHTML = '';
    }

    // 显示欢迎消息
    showWelcomeMessage() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'welcome-message';
        welcomeDiv.innerHTML = `
            <div class="message bot-message">
                <div class="message-content">
                    <p>你好！我是由郭桓君同学开发的AI智能体～</p>
                    <p>我是一个活泼可爱的小助手，可以帮你查询天气和时间哦！</p>
                    <p>快来和我聊天吧！✨</p>
                </div>
            </div>
        `;
        this.chatMessages.appendChild(welcomeDiv);
    }

    // 加载对话历史列表
    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const conversations = await response.json();
            this.renderConversations(conversations);

        } catch (error) {
            console.error('加载对话历史失败:', error);
        }
    }

    // 渲染对话历史列表
    renderConversations(conversations) {
        this.conversationHistory.innerHTML = '';
        
        if (conversations.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'conversation-item';
            emptyDiv.style.textAlign = 'center';
            emptyDiv.style.opacity = '0.6';
            emptyDiv.innerHTML = '<div class="conversation-title">暂无对话历史</div>';
            this.conversationHistory.appendChild(emptyDiv);
            return;
        }

        conversations.forEach(conv => {
            const convDiv = document.createElement('div');
            convDiv.className = 'conversation-item';
            if (conv.id === this.currentConversationId) {
                convDiv.classList.add('active');
            }
            
            convDiv.innerHTML = `
                <div class="conversation-title">${conv.title}</div>
                <div class="conversation-time">${this.formatTime(conv.last_message_time)}</div>
            `;
            
            convDiv.addEventListener('click', () => this.loadConversation(conv.id));
            this.conversationHistory.appendChild(convDiv);
        });
    }

    // 加载特定对话
    async loadConversation(conversationId) {
        if (conversationId === this.currentConversationId) return;

        try {
            this.showLoading(true);
            
            const response = await fetch(`/api/conversation/${conversationId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const messages = await response.json();
            
            // 更新当前对话ID
            this.currentConversationId = conversationId;
            
            // 清空并重新渲染消息
            this.clearMessages();
            
            messages.forEach(message => {
                if (message.role === 'user') {
                    this.addMessage(message.content, 'user');
                } else if (message.role === 'assistant') {
                    this.addMessage(message.content, 'bot');
                }
            });

            // 如果没有消息，显示欢迎消息
            if (messages.length <= 1) {
                this.showWelcomeMessage();
            }
            
            // 更新对话列表UI
            this.loadConversations();

        } catch (error) {
            console.error('加载对话失败:', error);
            alert('加载对话失败，请稍后再试。');
        } finally {
            this.showLoading(false);
        }
    }

    // 格式化时间显示
    formatTime(timestamp) {
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diffTime = now - date;
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
            return date.toLocaleTimeString('zh-CN', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        } else if (diffDays === 1) {
            return '昨天';
        } else if (diffDays < 7) {
            return `${diffDays}天前`;
        } else {
            return date.toLocaleDateString('zh-CN', { 
                month: 'short', 
                day: 'numeric' 
            });
        }
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});