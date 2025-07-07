class ChatApp {
    constructor() {
        this.currentConversationId = null;
        this.isLoading = false;
        this.currentMode = null;
        this.pendingTaskData = null;
        this.refreshInterval = null; // 刷新对话列表的定时器
        this.initializeElements();
        this.bindEvents();
        this.loadConversations();
        this.startAutoRefresh(); // 启动自动刷新
    }

    // 初始化DOM元素
    initializeElements() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.conversationHistory = document.getElementById('conversation-history');
        this.loading = document.getElementById('loading');
        this.modeStatus = document.getElementById('mode-status');
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

        // 点击外部关闭所有菜单
        document.addEventListener('click', (e) => {
            // 如果点击的不是菜单相关元素，关闭所有菜单
            if (!e.target.closest('.conversation-menu')) {
                document.querySelectorAll('.conversation-dropdown.show').forEach(menu => {
                    menu.classList.remove('show');
                });
            }
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

        // 清空输入框并立即显示用户消息（带当前时间戳）
        this.chatInput.value = '';
        const currentTime = new Date().toISOString();
        this.addMessage(message, 'user', false, currentTime);
        this.updateSendButtonState();

        // 添加跳动点提示AI正在思考
        this.addTypingIndicator();
        
        
        // 设置加载状态但不显示全局loading
        this.isLoading = true;

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
            
            // 立即刷新对话列表（显示新对话和加载动画）
            this.loadConversations();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // 更新当前对话ID
            this.currentConversationId = data.conversation_id;
            
            // 更新模式状态
            this.updateModeStatus(data.mode);
            
            // 移除跳动点并显示AI回复
            this.removeTypingIndicator();
            
            // 处理不同模式的响应
            if (data.mode === 'taskPlanning' && data.status === 'waiting_confirmation') {
                this.handleTaskPlanningResponse(data);
            } else {
                const currentTime = new Date().toISOString();
                this.addMessage(data.response, 'bot', false, currentTime);
            }
            
            // 再次刷新对话列表（确保对话ID正确并显示最新状态）
            this.loadConversations();

        } catch (error) {
            console.error('发送消息失败:', error);
            const currentTime = new Date().toISOString();
            this.addMessage('抱歉，发送消息时出现错误，请稍后再试。', 'bot', true, currentTime);
        } finally {
            // 移除跳动点并恢复状态
            this.removeTypingIndicator();
            this.isLoading = false;
            this.updateSendButtonState();
        }
    }

    // 添加消息到聊天界面
    addMessage(content, type, isError = false, timestamp = null) {
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
        
        // 如果有时间戳，添加时间戳显示
        if (timestamp) {
            const timestampDiv = document.createElement('div');
            timestampDiv.className = 'message-timestamp';
            timestampDiv.textContent = this.formatMessageTimestamp(timestamp);
            messageDiv.appendChild(timestampDiv);
        }
        
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
            // 如果当前有对话且有消息，先保存当前对话
            if (this.currentConversationId && this.hasMessages()) {
                await this.saveCurrentConversation();
            }

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
            
            // 重置模式状态为默认状态
            this.updateModeStatus(null);
            
            
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
            
            // 处理加载中的总结，显示跳动点动画
            let titleHtml = conv.title;
            if (conv.title === '...') {
                titleHtml = '<span class="loading-dots">生成中<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span></span>';
            }
            
            convDiv.innerHTML = `
                <div class="conversation-content">
                    <div class="conversation-title">${titleHtml}</div>
                    <div class="conversation-time">${this.formatConversationTime(conv.conversation_time)}</div>
                </div>
                <div class="conversation-menu">
                    <button class="conversation-menu-btn" data-conversation-id="${conv.id}">⋯</button>
                    <div class="conversation-dropdown" id="menu-${conv.id}">
                        <button class="conversation-dropdown-item delete delete-btn" data-conversation-id="${conv.id}">
                            <span class="icon">🗑️</span>删除
                        </button>
                    </div>
                </div>
            `;
            
            // 为对话内容区域添加点击事件
            const contentArea = convDiv.querySelector('.conversation-content');
            contentArea.addEventListener('click', () => this.loadConversation(conv.id));
            
            // 为菜单按钮添加事件监听器
            const menuBtn = convDiv.querySelector('.conversation-menu-btn');
            menuBtn.addEventListener('click', (e) => this.toggleConversationMenu(e, conv.id));
            
            // 为删除按钮添加事件监听器
            const deleteBtn = convDiv.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', (e) => this.deleteConversation(e, conv.id));
            
            this.conversationHistory.appendChild(convDiv);
        });
    }
    
    // 启动自动刷新对话列表
    startAutoRefresh() {
        // 每3秒刷新一次对话列表，用于更新异步生成的总结
        this.refreshInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/conversations/refresh');
                if (response.ok) {
                    const conversations = await response.json();
                    this.renderConversations(conversations);
                }
            } catch (error) {
                console.error('自动刷新对话列表失败:', error);
            }
        }, 3000);
    }
    
    // 停止自动刷新
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
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

            const data = await response.json();
            
            // 更新当前对话ID
            this.currentConversationId = conversationId;
            
            // 更新模式状态
            this.updateModeStatus(data.mode);
            
            // 清空并重新渲染消息
            this.clearMessages();
            
            const messages = data.messages || data; // 兼容新旧格式
            messages.forEach(message => {
                if (message.role === 'user') {
                    this.addMessage(message.content, 'user', false, message.timestamp);
                } else if (message.role === 'assistant') {
                    this.addMessage(message.content, 'bot', false, message.timestamp);
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

    // 添加打字指示器（跳动点）
    addTypingIndicator() {
        // 如果已存在打字指示器，则不重复添加
        if (document.querySelector('.typing-indicator')) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing-indicator';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content typing-content';
        
        messageContent.innerHTML = `
            <div class="typing-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
        `;
        
        typingDiv.appendChild(messageContent);
        this.chatMessages.appendChild(typingDiv);
        
        // 滚动到底部
        this.scrollToBottom();
    }

    // 移除打字指示器
    removeTypingIndicator() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // 检查当前是否有消息（除了欢迎消息）
    hasMessages() {
        const messages = this.chatMessages.querySelectorAll('.message');
        // 排除欢迎消息，检查是否有用户或AI的对话消息
        const conversationMessages = Array.from(messages).filter(msg => 
            !msg.closest('.welcome-message') && !msg.classList.contains('typing-indicator')
        );
        return conversationMessages.length > 0;
    }

    // 保存当前对话
    async saveCurrentConversation() {
        if (!this.currentConversationId) return;
        
        try {
            // 收集当前对话的所有消息
            const messages = this.collectCurrentMessages();
            
            const response = await fetch('/api/conversation/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conversation_id: this.currentConversationId,
                    messages: messages
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }

        } catch (error) {
            console.error('保存对话失败:', error);
        }
    }

    // 收集当前对话的消息
    collectCurrentMessages() {
        const messages = [];
        const messageElements = this.chatMessages.querySelectorAll('.message');
        
        messageElements.forEach(msgElement => {
            // 跳过欢迎消息和打字指示器
            if (msgElement.closest('.welcome-message') || 
                msgElement.classList.contains('typing-indicator')) {
                return;
            }
            
            const content = msgElement.querySelector('.message-content').textContent.trim();
            const role = msgElement.classList.contains('user-message') ? 'user' : 'assistant';
            
            if (content) {
                messages.push({
                    role: role,
                    content: content
                });
            }
        });
        
        return messages;
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

    // 格式化消息时间戳显示
    formatMessageTimestamp(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();
        const hours = date.getHours();
        const minutes = date.getMinutes();
        const seconds = date.getSeconds();
        
        return `${year}年${month}月${day}日${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    // 格式化对话历史时间显示
    formatConversationTime(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();
        const hours = date.getHours();
        const minutes = date.getMinutes();
        const seconds = date.getSeconds();
        
        return `${year}年${month}月${day}日${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    // 更新模式状态显示
    updateModeStatus(mode) {
        this.currentMode = mode;
        const statusElement = this.modeStatus;
        
        // 清除之前的类
        statusElement.className = '';
        
        if (mode === 'chatBot') {
            statusElement.innerHTML = '<span class="mode-icon">💬</span> 聊天模式';
            statusElement.className = 'mode-status mode-chatbot';
        } else if (mode === 'taskPlanning') {
            statusElement.innerHTML = '<span class="mode-icon">📋</span> 任务规划';
            statusElement.className = 'mode-status mode-planning';
        } else {
            statusElement.innerHTML = '<span class="mode-icon">🤖</span> 智能助手';
            statusElement.className = 'mode-status mode-default';
        }
    }


    // 处理任务规划模式的响应
    handleTaskPlanningResponse(data) {
        // 显示任务分解结果
        const currentTime = new Date().toISOString();
        this.addMessage(data.response, 'bot', false, currentTime);
        
        // 保存任务数据以备后续使用
        this.pendingTaskData = {
            conversation_id: data.conversation_id,
            original_question: data.original_question,
            decomposed_tasks: data.decomposed_tasks
        };
        
        // 添加确认按钮
        this.addTaskConfirmationButtons();
    }

    // 添加任务确认按钮
    addTaskConfirmationButtons() {
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'task-confirmation-buttons';
        buttonContainer.innerHTML = `
            <div style="margin: 10px 0;">
                <textarea id="task-editor" style="width: 100%; height: 100px; margin-bottom: 10px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" placeholder="你可以编辑任务步骤..."></textarea>
                <button onclick="chatApp.confirmTasks()" style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 8px;">确认并执行</button>
                <button onclick="chatApp.cancelTasks()" style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">取消</button>
            </div>
        `;
        
        // 将任务步骤填入编辑器
        const taskEditor = buttonContainer.querySelector('#task-editor');
        if (this.pendingTaskData && this.pendingTaskData.decomposed_tasks) {
            taskEditor.value = this.pendingTaskData.decomposed_tasks;
        }
        
        this.chatMessages.appendChild(buttonContainer);
        this.scrollToBottom();
    }

    // 确认任务
    async confirmTasks() {
        if (!this.pendingTaskData) return;
        
        const taskEditor = document.getElementById('task-editor');
        const confirmedTasks = taskEditor.value.trim().split('\n').filter(task => task.trim());
        
        try {
            this.removeTaskButtons();
            this.addTypingIndicator();
            
            
            const response = await fetch('/api/confirm-tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conversation_id: this.pendingTaskData.conversation_id,
                    original_question: this.pendingTaskData.original_question,
                    tasks: confirmedTasks
                })
            });
            
            const data = await response.json();
            
            this.removeTypingIndicator();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            const currentTime = new Date().toISOString();
            this.addMessage(data.response, 'bot', false, currentTime);
            this.pendingTaskData = null;
            
        } catch (error) {
            console.error('确认任务失败:', error);
            this.removeTypingIndicator();
            const currentTime = new Date().toISOString();
            this.addMessage('确认任务时出现错误，请稍后再试。', 'bot', true, currentTime);
        }
    }

    // 取消任务
    cancelTasks() {
        this.removeTaskButtons();
        this.pendingTaskData = null;
        const currentTime = new Date().toISOString();
        this.addMessage('已取消任务规划。', 'bot', false, currentTime);
    }

    // 移除任务按钮
    removeTaskButtons() {
        const buttons = document.querySelector('.task-confirmation-buttons');
        if (buttons) {
            buttons.remove();
        }
    }

    // 切换对话菜单显示状态
    toggleConversationMenu(event, conversationId) {
        event.stopPropagation();
        
        // 关闭其他所有菜单
        document.querySelectorAll('.conversation-dropdown.show').forEach(menu => {
            if (menu.id !== `menu-${conversationId}`) {
                menu.classList.remove('show');
            }
        });
        
        // 切换当前菜单
        const menu = document.getElementById(`menu-${conversationId}`);
        if (menu) {
            menu.classList.toggle('show');
        }
    }


    // 删除对话
    async deleteConversation(event, conversationId) {
        event.stopPropagation();
        
        // 关闭菜单
        const menu = document.getElementById(`menu-${conversationId}`);
        if (menu) {
            menu.classList.remove('show');
        }
        
        if (!confirm('确定要删除这个对话吗？删除后无法恢复。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/conversation/${conversationId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            
            // 如果删除的是当前对话，清空聊天区域
            if (conversationId === this.currentConversationId) {
                this.currentConversationId = null;
                this.clearMessages();
                this.showWelcomeMessage();
                this.updateModeStatus(null);
            }
            
            // 刷新对话列表
            this.loadConversations();
            
        } catch (error) {
            console.error('删除失败:', error);
            alert('删除失败，请稍后再试');
        }
    }
}

// 页面加载完成后初始化应用
let chatApp;
document.addEventListener('DOMContentLoaded', () => {
    chatApp = new ChatApp();
});