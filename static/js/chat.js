// Chat functionality

class ChatManager {
  constructor() {
    this.chatWindow = null;
    this.chatButton = null;
    this.chatMessages = null;
    this.chatInput = null;
    this.sendButton = null;
    this.closeButton = null;
    this.isOpen = false;
  }

  init() {
    // Get DOM elements
    this.chatWindow = document.getElementById('chatWindow');
    this.chatButton = document.getElementById('chatButton');
    this.chatMessages = document.getElementById('chatMessages');
    this.chatInput = document.getElementById('chatInput');
    this.sendButton = document.getElementById('sendChatBtn');
    this.closeButton = document.getElementById('closeChatBtn');

    // Set up event listeners
    this.chatButton.addEventListener('click', () => this.toggleChat());
    this.closeButton.addEventListener('click', () => this.closeChat());
    this.sendButton.addEventListener('click', () => this.sendMessage());
    this.chatInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.sendMessage();
      }
    });
  }

  toggleChat() {
    if (this.isOpen) {
      this.closeChat();
    } else {
      this.openChat();
    }
  }

  openChat() {
    this.chatWindow.classList.add('open');
    this.isOpen = true;
    this.chatInput.focus();
  }

  closeChat() {
    this.chatWindow.classList.remove('open');
    this.isOpen = false;
  }

  async sendMessage() {
    const message = this.chatInput.value.trim();
    
    if (!message) {
      return;
    }

    // Add user message to chat
    this.addMessage(message, 'user');
    
    // Clear input
    this.chatInput.value = '';

    // Send to backend
    try {
      const response = await fetch(`${CONFIG.apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Message sent successfully:', data);
        
        // Add confirmation message
        this.addMessage('Message received! (Check backend console)', 'bot');
      } else {
        console.error('Failed to send message:', response.status);
        this.addMessage('Failed to send message. Please try again.', 'bot');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      this.addMessage('Error connecting to server.', 'bot');
    }
  }

  addMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    
    messageDiv.appendChild(contentDiv);
    this.chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }
}

// Initialize chat when DOM is ready
const chatManager = new ChatManager();

document.addEventListener('DOMContentLoaded', () => {
  chatManager.init();
});
