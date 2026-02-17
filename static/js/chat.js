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

    // Show typing indicator
    const typingId = this.addTypingIndicator();

    // Collect current truck positions from the map/simulation
    const truckPositions = this.getCurrentTruckPositions();

    // Send to backend
    try {
      const response = await fetch(`${CONFIG.apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: message,
          truck_positions: truckPositions
        })
      });

      // Remove typing indicator
      this.removeTypingIndicator(typingId);

      if (response.ok) {
        const data = await response.json();
        console.log('Agent response:', data);
        
        // Add agent response
        const agentName = data.agent || 'Agent';
        const agentResponse = data.response || 'No response';
        
        // Format response with agent name
        this.addMessage(agentResponse, 'bot', agentName);
        
        // If there's data, show it in a collapsible section
        if (data.data) {
          this.addDataMessage(data.data);
        }
      } else {
        console.error('Failed to send message:', response.status);
        this.addMessage('Failed to send message. Please try again.', 'bot', 'Error');
      }
    } catch (error) {
      this.removeTypingIndicator(typingId);
      console.error('Error sending message:', error);
      this.addMessage('Error connecting to server. Make sure the backend is running.', 'bot', 'Error');
    }
  }

  getCurrentTruckPositions() {
    /**
     * Obtiene las posiciones actuales de los camiones desde la simulación del frontend
     */
    if (window.simulation && typeof window.simulation.getCurrentPositions === 'function') {
      const positions = window.simulation.getCurrentPositions();
      console.log('📍 Sending truck positions to backend:', positions);
      return positions;
    }
    
    console.log('⚠️ No simulation data available');
    return {};
  }

  addMessage(text, type, agentName = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    
    // Add agent name badge if provided
    if (agentName && type === 'bot') {
      const badgeDiv = document.createElement('div');
      badgeDiv.className = 'agent-badge';
      badgeDiv.textContent = agentName;
      messageDiv.appendChild(badgeDiv);
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Format text with line breaks
    contentDiv.innerHTML = text.replace(/\n/g, '<br>');
    
    messageDiv.appendChild(contentDiv);
    this.chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  addDataMessage(data) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message data-message';
    
    const headerDiv = document.createElement('div');
    headerDiv.className = 'data-header';
    headerDiv.textContent = '📊 Data';
    headerDiv.style.cursor = 'pointer';
    headerDiv.style.fontWeight = 'bold';
    headerDiv.style.marginBottom = '5px';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'data-content';
    contentDiv.style.display = 'none';
    contentDiv.style.fontSize = '12px';
    contentDiv.style.backgroundColor = '#f5f5f5';
    contentDiv.style.padding = '10px';
    contentDiv.style.borderRadius = '4px';
    contentDiv.style.maxHeight = '200px';
    contentDiv.style.overflow = 'auto';
    
    // Format JSON data
    contentDiv.textContent = JSON.stringify(data, null, 2);
    
    // Toggle visibility on click
    headerDiv.addEventListener('click', () => {
      contentDiv.style.display = contentDiv.style.display === 'none' ? 'block' : 'none';
    });
    
    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(contentDiv);
    this.chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  addTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message bot-message typing-indicator';
    messageDiv.id = 'typing-' + Date.now();
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    
    messageDiv.appendChild(contentDiv);
    this.chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    
    return messageDiv.id;
  }

  removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
      indicator.remove();
    }
  }
}

// Initialize chat when DOM is ready
const chatManager = new ChatManager();

document.addEventListener('DOMContentLoaded', () => {
  chatManager.init();
});
