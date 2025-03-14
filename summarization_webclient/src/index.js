

const baseOktaURL = "https://milliman.okta.com";
const appClientID = "0oa1uj3zlj5hatOW91d8";

// Bootstrap the AuthJS Client
const authClient = new OktaAuth({
  // Required Fields for OIDC client
  url: baseOktaURL,
  clientId: appClientID,
  redirectUri: `${process.env.SSO_REDIRECT_BASE_URL}/login/callback`,
  issuer: baseOktaURL, // oidc
  scopes: ['openid', 'profile', 'email']
});

if (window.location.pathname === '/login/callback') {
  if (authClient.isLoginRedirect()) {
    authClient.token.parseFromUrl()
      .then(data => {
        console.log('Tokens:', data.tokens);
        const { idToken } = data.tokens;
        sessionStorage.setItem('ID_TOKEN', JSON.stringify(idToken));
        window.location.replace("/");
      });
  } else {
    window.location.replace("/");
  }
} else if (window.location.pathname === '/signout/callback') {
  sessionStorage.removeItem('ID_TOKEN');
  window.location.replace("/");
} else {
  const existingTokenJson = sessionStorage.getItem('ID_TOKEN');
  if (existingTokenJson) {
    const existingTokenParsed = JSON.parse(existingTokenJson);
    if ((existingTokenParsed.expiresAt * 1000) <= new Date().getTime()) {
      authClient.token.getWithRedirect({
        responseType: ['id_token']
      });
    }
  }
}

function login() {
  authClient.token.getWithRedirect({
    responseType: ['id_token']
  });
}

function logout() {
  const token = getToken();
  if (!token) {
    window.location.href = "/signout/callback";
  } else {
    window.location.href = `${baseOktaURL}/oauth2/v1/logout?id_token_hint=${token.idToken}&post_logout_redirect_uri=${encodeURI(`${process.env.SSO_REDIRECT_BASE_URL}/signout/callback`)}`
  }
}

/* -------------------------------------------------------------------------- */
/*                            Conversation List Logic                          */
/* -------------------------------------------------------------------------- */
const conversationList = document.getElementById('conversation-list');

function getToken() {
  const idTokenJson = sessionStorage.getItem('ID_TOKEN');
  if (!idTokenJson) {
    return null;
  }

  const idTokenParsed = JSON.parse(idTokenJson);
  if ((idTokenParsed.expiresAt * 1000) <= new Date().getTime()) {
    authClient.token.getWithRedirect({
      responseType: ['id_token']
    });
  }

  return idTokenParsed;
}

async function fetchConversationHistory() {
  try {
    const token = getToken();
    if (!token) {
      return;
    }

    const response = await fetch(`${process.env.API_BASE_URL}/conversations/list`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token.idToken}`
      }
    });
    if (!response.ok) throw new Error('Failed to load conversations');

    let conversations = await response.json();

    // Sort by updated, then created (both descending)
    conversations.sort((a, b) =>
      new Date(b.updated) - new Date(a.updated) || new Date(b.created) - new Date(a.created)
    );

    displayConversations(conversations);
    highlightActiveConversation(); // highlight conversation if it matches the current ID
  } catch (error) {
    console.error('Error fetching conversations:', error);
    conversationList.innerHTML = '<p class="text-red-500">Failed to load conversation history.</p>';
  }
}

function displayConversations(conversations) {
  if (conversations.length === 0) {
    conversationList.innerHTML = '<p class="text-gray-500">No previous conversations found.</p>';
    return;
  }

  conversationList.innerHTML = '';
  conversations.forEach(conv => {
    const elapsedTime = formatElapsedTime(new Date(conv.updated));
    const item = document.createElement('div');
    item.className = 'p-3 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors cursor-pointer';
    item.dataset.conversationId = conv.id; // for highlighting

    item.innerHTML = `
          <strong>${conv.name}</strong> (${conv.regulation})<br>
          <span class="text-gray-600">Updated: ${elapsedTime} ago</span> |
          <span class="text-gray-600">${conv.sequenceCount} messages</span>
        `;
    item.addEventListener('click', () => loadConversation(conv.id));
    conversationList.appendChild(item);
  });
}

function highlightActiveConversation() {
  const items = conversationList.querySelectorAll('[data-conversation-id]');
  items.forEach(item => {
    if (item.dataset.conversationId === currentConversationId) {
      item.classList.add('active-conversation');
    } else {
      item.classList.remove('active-conversation');
    }
  });
}

function formatElapsedTime(updatedDate) {
  const now = new Date();
  const diffMs = now - updatedDate;
  const diffMin = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMin < 60) {
    if (diffMin < 0) {
      return '0 min';
    }
    return `${diffMin} min`;
  }
  if (diffHours < 24) return `${diffHours} hours`;
  return `${diffDays} days`;
}

/* -------------------------------------------------------------------------- */
/*                            Chat / Message Logic                             */
/* -------------------------------------------------------------------------- */
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const newChatButton = document.getElementById('new-chat-button');
const typingTemplate = document.getElementById('typing-template');
const closeButton = document.getElementById('close-regulation-modal');
const signoutButton = document.getElementById('signout-button');
const signinButton = document.getElementById('login-button');

let currentConversationId = null;
const userId = getUserId();

marked.setOptions({
  breaks: true,
  gfm: true,
  pedantic: false,
  headerIds: false
});

function addMessage(content, isUser = false, isInContext = true) {
  const messageDiv = document.createElement('div');
  messageDiv.className = isUser
    ? 'bg-blue-50 p-4 rounded'
    : 'bg-gray-50 p-4 rounded message-content';

  if (!isInContext) {
    messageDiv.classList.add('faded-message');
  }

  if (isUser) {
    messageDiv.textContent = content;
  } else {
    // Ensure numbered lists are displayed properly
    const processedContent = content?.replace(/^\d+\./gm, '\n$&') || '';
    const htmlContent = marked.parse(processedContent);
    const sanitizedHtml = DOMPurify.sanitize(htmlContent);
    messageDiv.innerHTML = sanitizedHtml;
  }

  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
  const typingIndicator = typingTemplate.content.cloneNode(true);
  chatMessages.appendChild(typingIndicator);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return chatMessages.lastElementChild;
}

function removeTypingIndicator(indicator) {
  if (indicator && indicator.parentNode) {
    indicator.remove();
  }
}

function getUserId() {
  return localStorage.getItem("userId");
}

function removeUserId() {
  localStorage.removeItem("userId");
}

function clearChatWindow() {
  // remove all messages except the welcome
  while (chatMessages.children.length > 1) {
    chatMessages.removeChild(chatMessages.lastChild);
  }
}

function newChat() {
  // remove all messages except the welcome
  clearChatWindow();
  currentConversationId = null;
  userInput.value = '';
  userInput.focus();
}

function handleOnNewChat() {
  newChat();
  highlightActiveConversation();
}

async function sendMessage(message) {
  userInput.disabled = true;
  sendButton.disabled = true;
  newChatButton.disabled = true;

  const typingIndicator = showTypingIndicator();
  const selectedRegulation = getSelectedRegulation();

  console.log("Sending message with selected regulation:", selectedRegulation);

  try {
    const token = getToken();
    if (!token) {
      return;
    }

    const response = await fetch(`${process.env.API_BASE_URL}/summarize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token.idToken}`
      },
      body: JSON.stringify({
        conversationId: currentConversationId,
        query: message,
        regulation: selectedRegulation.partitionKey
      })
    });
    if (!response.ok) {
      throw new Error('API request failed');
    }
    const data = await response.json();

    removeTypingIndicator(typingIndicator);
    currentConversationId = data.conversationId;

    addMessage(data.result, false, true);

    // Reload conversation list to keep updated
    await fetchConversationHistory();
    highlightActiveConversation();

    // Gray out out of context messages immediately after sending a new message
    updateGrayedOutMessages();

  } catch (error) {
    removeTypingIndicator(typingIndicator);
    addMessage('Sorry, there was an error processing your request. Please try again.');
    console.error('Error:', error);
  } finally {
    userInput.disabled = false;
    sendButton.disabled = false;
    newChatButton.disabled = false;
    userInput.focus();
  }
}

/* -------------------------------------------------------------------------- */
/*                        Loading Existing Conversation                        */
/* -------------------------------------------------------------------------- */
async function loadConversation(conversationId) {
  try {
    console.log(`Fetching conversation for conversationId: ${conversationId}`);

    const token = getToken();
    if (!token) {
      return;
    }

    // Fetch conversation details
    const response = await fetch(`${process.env.API_BASE_URL}/conversations/load`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token.idToken}`
      },
      body: JSON.stringify({ conversationId })
    });

    if (!response.ok) {
      throw new Error('Failed to load conversation');
    }

    const messages = await response.json();
    console.log('Retrieved conversation:', messages);

    // Fetch regulations only once
    console.log('Fetching regulations...');

    const regulationsResponse = await fetch(`${process.env.API_BASE_URL}/regulations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token.idToken}`
      }
    });

    if (!regulationsResponse.ok) {
      throw new Error('Failed to load regulations from the server.');
    }

    const regulations = await regulationsResponse.json();
    console.log('Retrieved regulations:', regulations);

    // Validate the conversation’s regulation
    const selectedRegulation = regulations.find(reg => reg.partitionKey === messages.regulation);

    // Clear the chat area
    clearChatWindow();

    if (!selectedRegulation) {
      console.error(`Invalid regulation '${messages.regulation}' for conversation '${conversationId}'. Regulation not found.`);

      const errorDiv = document.createElement('div');
      errorDiv.className = 'bg-red-100 text-red-700 p-4 rounded my-2';
      errorDiv.innerHTML = 'Unable to load the conversation because the selected regulation is no longer available.';

      // Display error message in the chat area
      chatMessages.appendChild(errorDiv);
      return; // Stop further execution
    }

    console.log(`Valid regulation found: ${selectedRegulation.title} (${selectedRegulation.partitionKey})`);

    // Update the UI with the correct regulation
    setSelectedRegulation(selectedRegulation);

    // Check if the conversation contains a log
    if (messages.log && messages.log.length > 0) {
      messages.log.sort((a, b) => a.sequence - b.sequence);

      const contextLimit = 7;
      const totalMessages = messages.log.length;
      const inContextStartIndex = totalMessages > contextLimit ? totalMessages - contextLimit : 0;

      messages.log.forEach((msg, index) => {
        const isInContext = index >= inContextStartIndex;
        addMessage(msg.promptRaw, true, isInContext);
        addMessage(msg.response, false, isInContext);
      });
    } else {
      addMessage('No messages found in this conversation.', false);
    }

    updateGrayedOutMessages();
    // Update current conversation ID
    currentConversationId = conversationId;
    highlightActiveConversation();

    // Scroll chat to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    userInput.focus();
  } catch (error) {
    console.error('Error loading conversation:', error);

    chatMessages.innerHTML = `
          <div class="bg-red-100 text-red-700 p-4 rounded my-2">
            Unable to load the conversation. Please try again later.
          </div>
        `;
  }
}

function checkSelectedRegulation() {
  const selectedRegulation = getSelectedRegulation();
  closeButton.classList.toggle('hidden', selectedRegulation ? false : true);

  if (!selectedRegulation) {
    showRegulationModal();
    return false;
  }

  displaySelectedRegulation(selectedRegulation);
  enableChat();
  return true;
}

async function loadRegulations() {
  const loadingIndicator = document.getElementById('regulation-loading');
  const regulationList = document.getElementById('regulation-list');

  loadingIndicator.classList.remove('hidden');
  regulationList.classList.add('hidden');

  try {
    const token = getToken();
    if (!token) {
      return;
    }

    const response = await fetch(`${process.env.API_BASE_URL}/regulations`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token.idToken}`
      }
    });
    if (!response.ok) {
      throw new Error('Failed to load regulations');
    }
    const regs = await response.json();
    displayRegulationsList(regs);
  } catch (error) {
    console.error('Error loading regulations:', error);
  } finally {
    loadingIndicator.classList.add('hidden');
    regulationList.classList.remove('hidden');
  }
}

function findRegulationGroup(groupedRegulations, groupName){
  let matchingGroup = null;

  for (const group of groupedRegulations) {
    if (group.type !== 'group') {
      continue;
    } 

    if (group.name === groupName) {
      return group;
    }

    return findRegulationGroup(group, leafName);
  }

  return matchingGroup;
}

function getOrCreateGroupedRegulationNode(groupedRegulations, hierarchy, currentLevel) {
  if (currentLevel === undefined) {
    currentLevel = 0;
  }

  for (const group of groupedRegulations.children) {
    if (hierarchy[currentLevel] === group.name) {
      if (currentLevel === hierarchy.length - 1) {
        return group;
      }

      return getOrCreateGroupedRegulationNode(group, hierarchy, currentLevel+1);
    }
  }

  const node = {
    type: 'group',
    name: hierarchy[currentLevel],
    children: []
  };

  groupedRegulations.children.push(node);

  if (currentLevel === hierarchy.length - 1) {
    return node;
  }

  return getOrCreateGroupedRegulationNode(node, hierarchy, currentLevel+1);
}

function groupRegulations(regulations) {
  const groupedRegulations = {
    type: 'group',
    name: '<root>',
    children: []
  };

  for (const regulation of regulations) {  
    if (!regulation.hierarchies || regulation.hierarchies.length === 0) {
      const rootNode = getOrCreateGroupedRegulationNode(groupedRegulations, ['<root>']);
      rootNode.children.push({
        type: 'regulation',
        name: regulation.title,
        content: regulation
      });
    } else {
      for (const hierarchy of regulation.hierarchies) {
          const node = getOrCreateGroupedRegulationNode(groupedRegulations, hierarchy.split('/'));
          node.children.push({
            type: 'regulation',
            name: regulation.title,
            content: regulation
          });
      }
    }
  }  

  return groupedRegulations;
}


const upChevronIcon = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" />
</svg>
`;

const downChevronIcon = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
</svg>`

function setupCollapsibleButtons(groupings, parentNode) {
  for (const group of groupings) {
    const uuid = crypto.randomUUID();
    if (group.type === 'regulation') {      
      const button = document.createElement('button');
      button.className = 'w-full p-2 text-left hover:bg-gray-100 rounded';
      button.textContent = group.name;
      button.onclick = () => handleOnModalSelectedRegulation(group.content);
      parentNode.appendChild(button);
    } else if (group.type === 'group') {
      const section = document.createElement('div');
      section.id = `section-container-${uuid}`;
      section.className = "collapsible-section";

      parentNode.appendChild(section);      
  
      const sectionBody = document.createElement('div');
      sectionBody.id = `section-body-${uuid}`;
      sectionBody.className = "collapsible-section-body";
      sectionBody.style.display = 'none';
    
      const sectionHeader = document.createElement('div');
      sectionHeader.id = `section-header-${uuid}`;
      sectionHeader.className = "collapsible-section-header";

      sectionHeader.innerHTML = `<span>${downChevronIcon}</span><span>${group.name}</span>`;
      sectionHeader.onclick = () => {
        if (sectionBody.style.display === 'none') {
          sectionBody.style.display = 'block';
          sectionHeader.innerHTML = `<span>${upChevronIcon}</span><span>${group.name}</span>`;
        } else {
          sectionBody.style.display = 'none';
          sectionHeader.innerHTML = `<span>${downChevronIcon}</span><span>${group.name}</span>`;
        }
      };

      section.appendChild(sectionHeader);
      section.appendChild(sectionBody);
        
      setupCollapsibleButtons(group.children, sectionBody)
    }
  }  
}

function displayRegulationsList(regulations) {
  const groupings = groupRegulations(regulations);
  console.log('groupings', groupings);
  const container = document.getElementById('regulation-list');
  container.innerHTML = '';

  setupCollapsibleButtons(groupings.children, container);

  // regulations.forEach(reg => {
  //   const button = document.createElement('button');
  //   button.className = 'w-full p-2 text-left hover:bg-gray-100 rounded';
  //   button.textContent = reg.title;
  //   button.onclick = () => handleOnModalSelectedRegulation(reg);
  //   container.appendChild(button);
  // });
}

function setSelectedRegulation(regulation) {
  if (!regulation) {
    console.error('setSelectedRegulation called with null/undefined regulation.');
    return;
  }
  console.log(`Setting selected regulation: ${regulation.title} (${regulation.partitionKey})`);
  localStorage.setItem('selectedRegulation', JSON.stringify(regulation));
  displaySelectedRegulation(regulation);
}

function handleOnModalSelectedRegulation(regulation) {
  setSelectedRegulation(regulation);

  // Handle additional UI behaviors
  hideRegulationModal();
  enableChat();
  newChat();
  highlightActiveConversation();
}

function getSelectedRegulation() {
  const regulationString = localStorage.getItem('selectedRegulation');
  return regulationString && JSON.parse(regulationString);
}

function displaySelectedRegulation(regulation) {
  const display = document.getElementById('selected-regulation');
  const changeButton = document.getElementById('change-regulation');
  display.textContent = `Selected: ${regulation.title}`;
  changeButton.style.display = 'block';
}

document.getElementById('change-regulation').addEventListener('click', showRegulationModal);

function showRegulationModal() {
  const modal = document.getElementById('regulation-modal');
  modal.classList.remove('hidden');
  loadRegulations();
}

function hideRegulationModal() {
  const modal = document.getElementById('regulation-modal');
  modal.classList.add('hidden');
}

function enableChat() {
  userInput.disabled = false;
  sendButton.disabled = false;
  userInput.focus();
}

function disableChat() {
  userInput.disabled = true;
  sendButton.disabled = true;
}

function updateGrayedOutMessages() {
  const allMessages = document.querySelectorAll("#chat-messages > div");
  const contextLimit = 7;
  const separatorMessageId = "out-of-scope-separator";

  console.log("Updating grayed-out messages...");

  const existingSeparator = document.getElementById(separatorMessageId);
  if (existingSeparator) {
    console.log("Removing existing separator...");
    existingSeparator.remove();
  }

  /* multiply by 2 to get message as well as response */
  if (allMessages.length <= contextLimit * 2) {
    console.log("Not enough messages to apply graying out.");
    return;
  }

  const startGrayIndex = allMessages.length - (contextLimit * 2);
  let lastGrayedOutIndex = null;

  allMessages.forEach((msg, index) => {
    if (index < startGrayIndex) {
      msg.classList.add("faded-message");
      lastGrayedOutIndex = index;
    } else {
      msg.classList.remove("faded-message");
    }
  });

  if (lastGrayedOutIndex !== null && lastGrayedOutIndex < allMessages.length - 1) {
    const separator = document.createElement("div");
    separator.id = separatorMessageId;
    separator.className = "separator-message";
    separator.textContent =
      "The previous messages are considered out of scope to the current conversation but will be retained.";

    console.log(`Adding separator after message index: ${lastGrayedOutIndex}`);
    allMessages[lastGrayedOutIndex].after(separator);
  } else {
    console.warn("No valid place found to insert the separator.");
  }
}

function setWelcomeText(idToken) {
  const welcome = document.createElement("div");
  welcome.id = "welcome-text";
  welcome.className = "";
  welcome.textContent = `Welcome, ${idToken.claims.name}`;

  document.getElementById("welcome-container").appendChild(welcome)
}

async function migrateConversationsIfNeeded() {
  if (userId) {
    const token = getToken();
    const response = await fetch(`${process.env.API_BASE_URL}/conversations/migrate`, {
      method: 'POST',
      body: JSON.stringify({ userId }),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token.idToken}`
      }
    });

    if (response.ok) {
      removeUserId();
    }
  }
}

async function init() {
  // we only want to initialize if we aren't on a callback URL
  if (window.location.pathname === "/login/callback" ||
    window.location.pathname === "/signout/callback"
  ) {
    return;
  }

  const idToken = getToken();
  const initialLogin = document.getElementById("initial-login");
  if (!idToken) {
    initialLogin.style.display = "inherit";
    return;
  }

  await migrateConversationsIfNeeded();

  setWelcomeText(idToken);

  try {
    const hasRegulation = checkSelectedRegulation();
    if (!hasRegulation) {
      disableChat();
    }
    handleOnNewChat();
  } finally {
    document.getElementById('initial-loading').remove();
  }
}

// Handle form submission
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = userInput.value.trim();
  if (!message) return;

  // Add user message
  addMessage(message, true);
  userInput.value = '';
  await sendMessage(message);
});

newChatButton.addEventListener('click', handleOnNewChat);
closeButton.addEventListener('click', hideRegulationModal);
signinButton.addEventListener('click', login);
signoutButton.addEventListener('click', logout);

// On DOM load, fetch conversation list & init chat
document.addEventListener('DOMContentLoaded', () => {  
  init().then(() => {
    fetchConversationHistory();
  });
});