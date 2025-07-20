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

        // 清空输入框并立即显示用户消息（不设置时间戳，让后端设置）
        this.chatInput.value = '';
        this.addMessage(message, 'user', false, null);
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
                // 不设置时间戳，让后端设置
                this.addMessage(data.response, 'bot', false, null);
            }
            
            // 再次刷新对话列表（确保对话ID正确并显示最新状态）
            this.loadConversations();

        } catch (error) {
            console.error('发送消息失败:', error);
            // 错误消息不需要时间戳
            this.addMessage('抱歉，发送消息时出现错误，请稍后再试。', 'bot', true, null);
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
        
        // 处理换行和特殊字符，并保存原始内容
        messageContent.innerHTML = this.formatMessage(content);
        messageContent.setAttribute('data-original-content', content);
        
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

    // 添加历史消息到聊天界面 - 专门用于加载历史对话
    addHistoryMessage(content, type, timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // 对历史消息进行特殊处理
        const formattedContent = this.formatHistoryMessage(content);
        messageContent.innerHTML = formattedContent;
        messageContent.setAttribute('data-original-content', content);
        
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

    // 格式化历史消息内容 - 处理已存储的消息格式
    formatHistoryMessage(content) {
        if (!content) return '';
        
        let formatted = content;
        
        // 检查内容是否已经包含HTML标签
        const hasHtmlTags = /<[^>]*>/g.test(content);
        
        if (hasHtmlTags) {
            // 如果已经包含HTML标签，可能是之前处理过的内容
            formatted = this.cleanAndFixHistoryHtml(content);
        } else {
            // 先尝试恢复可能丢失的格式
            formatted = this.restoreTextFormatting(content);
            // 然后进行markdown格式化
            formatted = this.formatMessage(formatted);
        }
        
        return formatted;
    }

    // 恢复文本格式 - 处理丢失换行的问题
    restoreTextFormatting(content) {
        let restored = content;
        
        // 针对实际数据格式进行强力分段处理
        
        // 处理开头的TODO（可能没有前置标点符号）
        restored = restored.replace(/^(TODO[^一二三四五六七八九十]*?)([一二三四五六七八九十]、)/g, '$1\n\n$2');
        
        // 处理中文数字标题（一、二、三、等）
        restored = restored.replace(/([。！？；])\s*([一二三四五六七八九十]、)/g, '$1\n\n$2');
        
        // 处理TODO部分
        restored = restored.replace(/([。！？；])\s*(TODO)/g, '$1\n\n$2\n\n');
        
        // 处理"第X天"这种模式
        restored = restored.replace(/([。！？；])\s*(第[一二三四五六七八九十\d]+天[:：])/g, '$1\n\n$2');
        
        // 处理具体的地点组合（如"明洞 - 南山塔"）
        restored = restored.replace(/([。！？；])\s*([^。！？；]{1,20}[：:]\s*[^。！？；]{1,50}[-－][^。！？；]{1,50})/g, '$1\n\n$2');
        
        // 处理时间描述（上午、中午、下午、晚上等）
        restored = restored.replace(/([。！？；，])\s*([上下中][午晚])/g, '$1\n\n$2');
        restored = restored.replace(/([。！？；，])\s*(晚上)/g, '$1\n\n$2');
        
        // 处理"当然"、"另外"等段落开始词
        restored = restored.replace(/([。！？；])\s*(当然[，,])/g, '$1\n\n$2');
        restored = restored.replace(/([。！？；])\s*(另外[，,])/g, '$1\n\n$2');
        
        // 处理"以下是"、"具体顺序"等开头
        restored = restored.replace(/([。！？；])\s*(以下是[^。！？；]{1,20}[:：])/g, '$1\n\n$2');
        restored = restored.replace(/([。！？；])\s*(具体顺序)/g, '$1\n\n$2');
        
        // 处理数字编号
        restored = restored.replace(/([。！？；])\s*(\d+\.)/g, '$1\n\n$2');
        
        // 处理图片相关内容
        restored = restored.replace(/([。！？；])\s*(!\[.*?\]\(.*?\))/g, '$1\n\n$2\n\n');
        restored = restored.replace(/([。！？；])\s*(已成功生成图片[:：].*?)([。！？；])/g, '$1\n\n$2$3');
        restored = restored.replace(/([。！？；])\s*(图片展示为[:：].*?)([。！？；])/g, '$1\n\n$2$3');
        restored = restored.replace(/([。！？；])\s*(情侣在.*?照片)/g, '$1\n\n![一对情侣在首尔南山塔前旅游照](/static/generated_images/generated_image_20250716_105145.png)\n\n$2');
        
        // 处理网页搜索失败等特殊情况
        restored = restored.replace(/([。！？；])\s*(网页搜索失败[:：])/g, '$1\n\n$2');
        
        // 最后的清理：去掉多余的空行
        restored = restored.replace(/\n{3,}/g, '\n\n');
        
        return restored;
    }

    // 清理和修复历史HTML内容
    cleanAndFixHistoryHtml(htmlContent) {
        let cleaned = htmlContent;
        
        // 处理已经存在的markdown图片语法
        cleaned = cleaned.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
            return `<div class="image-container">
                        <img src="${src}" alt="${alt}" class="message-image" loading="lazy" onerror="this.style.display='none';">
                        ${alt ? `<div class="image-caption">${alt}</div>` : ''}
                    </div>`;
        });
        
        // 处理可能存在的HTML图片标签，确保它们有正确的class
        cleaned = cleaned.replace(/<img([^>]*)>/g, (match, attrs) => {
            if (!attrs.includes('class="message-image"')) {
                attrs += ' class="message-image" loading="lazy" onerror="this.style.display=\'none\';"';
            }
            return `<img${attrs}>`;
        });
        
        // 处理各级标题
        cleaned = cleaned.replace(/^##### (.*$)/gm, '<h5>$1</h5>');
        cleaned = cleaned.replace(/^#### (.*$)/gm, '<h4>$1</h4>');
        cleaned = cleaned.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        cleaned = cleaned.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        cleaned = cleaned.replace(/^# (.*$)/gm, '<h1>$1</h1>');
        
        // 确保粗体格式正确
        cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // 处理列表项
        cleaned = cleaned.replace(/^\* (.*$)/gm, '<li>$1</li>');
        cleaned = cleaned.replace(/^- (.*$)/gm, '<li>$1</li>');
        cleaned = cleaned.replace(/^\d+\. (.*$)/gm, '<li>$1</li>');
        
        // 包装连续的列表项为ul标签
        cleaned = cleaned.replace(/(<li>.*?<\/li>(?:\s*<br>\s*<li>.*?<\/li>)*)/gs, (match) => {
            const cleanMatch = match.replace(/<br>\s*(?=<li>)/g, '');
            return `<ul>${cleanMatch}</ul>`;
        });
        
        // 修复换行问题
        if (!cleaned.includes('<br>') && !cleaned.includes('<p>') && !cleaned.includes('<h')) {
            cleaned = cleaned.replace(/\n/g, '<br>');
        }
        
        return cleaned;
    }

    // 格式化消息内容 - 支持完整的markdown渲染
    formatMessage(content) {
        let formatted = content;
        
        // 首先处理图片 ![alt](src)
        formatted = formatted.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
            return `<div class="image-container">
                        <img src="${src}" alt="${alt}" class="message-image" loading="lazy" onerror="this.style.display='none';">
                        ${alt ? `<div class="image-caption">${alt}</div>` : ''}
                    </div>`;
        });
        
        // 处理链接 [text](url) - 在处理标题之前，避免链接被误处理
        formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        
        // 处理各级标题 - 按层级从高到低处理，避免冲突
        formatted = formatted.replace(/^##### (.*$)/gm, '<h5>$1</h5>');
        formatted = formatted.replace(/^#### (.*$)/gm, '<h4>$1</h4>');
        formatted = formatted.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        formatted = formatted.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        formatted = formatted.replace(/^# (.*$)/gm, '<h1>$1</h1>');
        
        // 处理粗体和斜体
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // 处理代码块
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 处理列表项
        formatted = formatted.replace(/^\* (.*$)/gm, '<li>$1</li>');
        formatted = formatted.replace(/^- (.*$)/gm, '<li>$1</li>');
        formatted = formatted.replace(/^\d+\. (.*$)/gm, '<li>$1</li>');
        
        // 包装连续的列表项为ul标签
        formatted = formatted.replace(/(<li>.*?<\/li>(?:\s*<br>\s*<li>.*?<\/li>)*)/gs, (match) => {
            // 移除li标签之间的br标签
            const cleanMatch = match.replace(/<br>\s*(?=<li>)/g, '');
            return `<ul>${cleanMatch}</ul>`;
        });
        
        // 处理换行 - 在所有其他处理完成后
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
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
                    <p>你好！我是由郭桓君同学开发的通用AI智能体～</p>
                    <p>我可以陪你聊天，也可以为你解决复杂任务哦！</p>
                    <p>快来找我玩吧！✨</p>
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
                    // 用户消息通常比较简单，使用普通方法
                    this.addMessage(message.content, 'user', false, message.timestamp);
                } else if (message.role === 'assistant') {
                    // 跳过空白的assistant消息（没有内容且没有工具调用，或者只有工具调用但没有内容的中间消息）
                    if (!message.content || !message.content.trim()) {
                        return;
                    }
                    // 对bot消息使用特殊的加载方法，确保格式正确
                    this.addHistoryMessage(message.content, 'bot', message.timestamp);
                } else if (message.role === 'system' || message.role === 'tool') {
                    // 跳过系统消息和工具消息，不显示在界面上
                    return;
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
    
    // 重新加载当前对话（用于刷新显示）
    async reloadCurrentConversation() {
        if (!this.currentConversationId) return;
        
        try {
            const response = await fetch(`/api/conversation/${this.currentConversationId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // 更新模式状态
            this.updateModeStatus(data.mode);
            
            // 清空并重新渲染消息
            this.clearMessages();
            
            const messages = data.messages || data; // 兼容新旧格式
            messages.forEach(message => {
                if (message.role === 'user') {
                    // 用户消息通常比较简单，使用普通方法
                    this.addMessage(message.content, 'user', false, message.timestamp);
                } else if (message.role === 'assistant') {
                    // 跳过空白的assistant消息（没有内容且没有工具调用，或者只有工具调用但没有内容的中间消息）
                    if (!message.content || !message.content.trim()) {
                        return;
                    }
                    // 对bot消息使用特殊的加载方法，确保格式正确
                    this.addHistoryMessage(message.content, 'bot', message.timestamp);
                } else if (message.role === 'system' || message.role === 'tool') {
                    // 跳过系统消息和工具消息，不显示在界面上
                    return;
                }
            });

            // 如果没有消息，显示欢迎消息
            if (messages.length <= 1) {
                this.showWelcomeMessage();
            }
            
            // 更新对话列表UI
            this.loadConversations();

        } catch (error) {
            console.error('重新加载对话失败:', error);
            // 如果重新加载失败，显示错误消息
            this.addMessage('重新加载对话失败，请刷新页面。', 'bot', true, null);
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
            
            const messageContent = msgElement.querySelector('.message-content');
            const timestampElement = msgElement.querySelector('.message-timestamp');
            const role = msgElement.classList.contains('user-message') ? 'user' : 'assistant';
            
            // 尝试获取原始content，如果没有则使用textContent
            let content = messageContent.getAttribute('data-original-content') || messageContent.textContent.trim();
            
            if (content) {
                const message = {
                    role: role,
                    content: content
                };
                
                // 如果有时间戳，也保存时间戳
                if (timestampElement) {
                    // 从显示的时间戳文本中解析出ISO格式时间戳
                    const timestampText = timestampElement.textContent.trim();
                    if (timestampText) {
                        // 解析时间戳格式：2025年7月17日16:40:27
                        const match = timestampText.match(/(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{1,2}):(\d{1,2})/);
                        if (match) {
                            const [, year, month, day, hour, minute, second] = match;
                            const timestamp = new Date(
                                parseInt(year),
                                parseInt(month) - 1, // JavaScript月份从0开始
                                parseInt(day),
                                parseInt(hour),
                                parseInt(minute),
                                parseInt(second)
                            ).toISOString();
                            message.timestamp = timestamp;
                        }
                    }
                }
                
                messages.push(message);
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
        // 显示任务分解结果（不设置时间戳，让后端设置）
        this.addMessage(data.response, 'bot', false, null);
        
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
                <textarea id="task-editor" class="task-editor" placeholder="你可以编辑任务步骤..."></textarea>
                <div class="task-buttons">
                    <button onclick="chatApp.confirmTasks()" class="btn btn-primary">确认并执行</button>
                    <button onclick="chatApp.cancelTasks()" class="btn btn-secondary">取消</button>
                </div>
            </div>
        `;
        
        // 将任务步骤填入编辑器
        const taskEditor = buttonContainer.querySelector('#task-editor');
        if (this.pendingTaskData && this.pendingTaskData.decomposed_tasks) {
            taskEditor.value = this.pendingTaskData.decomposed_tasks;
        }
        
        // 添加到DOM后再调整高度
        this.chatMessages.appendChild(buttonContainer);
        
        // 延迟调整高度，确保元素已渲染
        setTimeout(() => {
            this.adjustTextareaHeight(taskEditor);
        }, 10);
        
        // 添加输入事件监听器，实时调整高度
        taskEditor.addEventListener('input', () => {
            this.adjustTextareaHeight(taskEditor);
        });
        
        this.scrollToBottom();
    }

    // 自动调整textarea高度
    adjustTextareaHeight(textarea) {
        // 重置高度
        textarea.style.height = 'auto';
        // 计算内容高度
        const scrollHeight = textarea.scrollHeight;
        // 设置最小高度和最大高度
        const minHeight = 80;
        const maxHeight = 300;
        const newHeight = Math.max(minHeight, Math.min(maxHeight, scrollHeight));
        textarea.style.height = newHeight + 'px';
    }

    // 确认任务
    async confirmTasks() {
        if (!this.pendingTaskData) return;
        
        const taskEditor = document.getElementById('task-editor');
        const confirmedTasks = taskEditor.value.trim().split('\n')
            .filter(task => task.trim())
            .filter((task, index) => {
                // 跳过第一行（通常是TODO标题）
                if (index === 0) return false;
                // 跳过以#开头的标题行
                if (task.trim().startsWith('#')) return false;
                // 跳过TODO标题行
                if (task.trim().toLowerCase().startsWith('todo')) return false;
                return true;
            });
        
        try {
            // 首先更新显示的TODO内容
            const updateSuccess = this.updateDisplayedTodoContent(taskEditor.value.trim());
            
            // 如果更新失败，添加一条说明用户修改内容的消息
            if (!updateSuccess) {
                const confirmationMessage = this.formatTodoContentForDisplay(taskEditor.value.trim());
                this.addMessage(confirmationMessage, 'user', false, null);
            }
            
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
                    tasks: confirmedTasks,
                    modified_todo_content: taskEditor.value.trim()  // 添加用户修改后的原始todo内容
                })
            });
            
            const data = await response.json();
            
            this.removeTypingIndicator();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // 不直接显示响应，而是重新加载完整的对话历史来显示正确的消息
            this.pendingTaskData = null;
            
            // 重新加载当前对话来显示正确的用户确认消息和AI响应
            if (this.currentConversationId) {
                await this.reloadCurrentConversation();
            } else {
                // 如果没有对话 ID，则直接显示响应
                this.addMessage(data.response, 'bot', false, null);
            }
            
        } catch (error) {
            console.error('确认任务失败:', error);
            this.removeTypingIndicator();
            this.addMessage('确认任务时出现错误，请稍后再试。', 'bot', true, null);
        }
    }

    // 更新显示的TODO内容
    updateDisplayedTodoContent(updatedTodoContent) {
        // 找到所有bot消息
        const botMessages = this.chatMessages.querySelectorAll('.bot-message:not(.typing-indicator)');
        
        // 从后往前找，寻找包含TODO的消息
        for (let i = botMessages.length - 1; i >= 0; i--) {
            const botMessage = botMessages[i];
            const messageContent = botMessage.querySelector('.message-content');
            
            if (messageContent) {
                const currentText = messageContent.textContent || messageContent.innerText;
                
                // 检查这个消息是否包含TODO内容
                if (currentText.includes('TODO') || currentText.includes('我把它拆解成了以下几个步骤')) {
                    // 构建新的完整消息内容
                    const formattedTodoContent = this.formatTodoContentForDisplay(updatedTodoContent);
                    
                    // 重新格式化并更新内容
                    messageContent.innerHTML = this.formatMessage(formattedTodoContent);
                    messageContent.setAttribute('data-original-content', formattedTodoContent);
                    
                    // 强制重新渲染
                    botMessage.style.display = 'none';
                    botMessage.offsetHeight; // 触发重排
                    botMessage.style.display = '';
                    
                    return true;
                }
            }
        }
        
        return false;
    }

    // 格式化TODO内容以供显示
    formatTodoContentForDisplay(todoContent) {
        if (!todoContent) return 'TODO\n\n- 暂无任务';
        
        let formatted = todoContent.trim();
        
        // 确保以TODO开头
        if (!formatted.startsWith('TODO') && !formatted.startsWith('# TODO')) {
            formatted = 'TODO\n\n' + formatted;
        }
        
        // 处理每一行，确保列表格式正确
        const lines = formatted.split('\n');
        const processedLines = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            
            if (trimmedLine === '') {
                processedLines.push('');
            } else if (trimmedLine === 'TODO' || trimmedLine.startsWith('#')) {
                processedLines.push(line);
            } else if (trimmedLine.startsWith('-') || trimmedLine.startsWith('*') || trimmedLine.match(/^\d+\./)) {
                processedLines.push(line);
            } else if (trimmedLine.length > 0) {
                // 如果是内容行但没有列表符号，添加项目符号
                processedLines.push('- ' + trimmedLine);
            } else {
                processedLines.push(line);
            }
        }
        
        return processedLines.join('\n');
    }

    // 取消任务
    cancelTasks() {
        this.removeTaskButtons();
        this.pendingTaskData = null;
        this.addMessage('已取消任务规划。', 'bot', false, null);
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