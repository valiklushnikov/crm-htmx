/******************************************************
 *  CHAT.JS
 ******************************************************/

// ===============================
// GLOBAL VARS
// ===============================
let wsConnections = {}; // WebSocket for private chats
let groupChatWs = null; // WebSocket group chat
let currentUser = null; // Who is open now
let unreadMessages = {}; // Unread messages
let isGroupChatActive = false; // Group chat active?

let websocketsInitialized = false;
let lastTokenRefresh = null;
let tokenRefreshInterval = null;
let pageUnloading = false;

const TOKEN_LIFETIME = 15 * 60 * 1000; // 15 min
const TOKEN_REFRESH_INTERVAL = 10 * 60 * 1000; // update every 10 min

const UNREAD_MESSAGES_KEY = "chatUnreadMessages";

let notificationSound = null;
let soundEnabled = false;

// ===============================
// FILE HANDLING VARIABLES
// ===============================
let selectedFile = null;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

// ===============================
// UTILS: STRONG EQUAL ID
// ===============================
function isCurrentChatActive(userId) {
  return String(currentUser) === String(userId);
}

// ===============================
// LOAD / DAVE UNREAD
// ===============================
function loadUnreadFromStorage() {
  try {
    const saved = localStorage.getItem(UNREAD_MESSAGES_KEY);
    unreadMessages = saved ? JSON.parse(saved) : {};
  } catch (e) {
    console.error("Unread storage corrupted — reset", e);
    unreadMessages = {};
  }
}

function saveUnreadToStorage() {
  localStorage.setItem(UNREAD_MESSAGES_KEY, JSON.stringify(unreadMessages));
}

// ===============================
// SYNC UNREAD BETWEEN TABS
// ===============================
window.addEventListener("storage", (e) => {
  if (e.key === UNREAD_MESSAGES_KEY && e.newValue) {
    try {
      unreadMessages = JSON.parse(e.newValue);

      Object.keys(unreadMessages).forEach((uid) => updateBadge(uid));
      updateTotalUnread();

      console.log("Unread synchronized from another tab");
    } catch (err) {
      console.error("Failed to sync unread from storage:", err);
    }
  }
});

// ===============================
// DEBOUNCE — FOR UPDATE BEБДЖЕЙ
// ===============================
let badgeUpdateTimers = {};

function debouncedIncrementBadge(userId) {
  if (badgeUpdateTimers[userId]) clearTimeout(badgeUpdateTimers[userId]);

  if (!unreadMessages[userId]) unreadMessages[userId] = 0;
  unreadMessages[userId]++;

  badgeUpdateTimers[userId] = setTimeout(() => {
    saveUnreadToStorage();
    updateBadge(userId);
    updateTotalUnread();
    delete badgeUpdateTimers[userId];
  }, 100);
}

// ===============================
// COMMON BADGE "ALL MESSAGES"
// WITH DEBOUNCING
// ===============================
let totalBadgeUpdateTimer = null;
let lastTotalUnread = 0;

function updateTotalUnread() {
  if (totalBadgeUpdateTimer) clearTimeout(totalBadgeUpdateTimer);

  totalBadgeUpdateTimer = setTimeout(() => {
    const total = Object.values(unreadMessages).reduce((sum, x) => sum + x, 0);

    const totalBadge = document.getElementById("chatTotalBadge");
    const toggleBtn = document.getElementById("chatToggleBtn");
    const header = document.getElementById("chatHeaderText");
    const widget = document.getElementById("chatWidget");
    const isWidgetClosed = widget && widget.classList.contains("chat-widget-collapsed");

    if (total > 0) {
      if (totalBadge) {
        totalBadge.textContent = total;
        totalBadge.style.display = "flex";
      }
      if (toggleBtn) {
        toggleBtn.classList.add("has-unread");

        if (isWidgetClosed && total > lastTotalUnread) {

          toggleBtn.style.animation = 'none';
          toggleBtn.style.boxShadow = '';
          void toggleBtn.offsetWidth;

          toggleBtn.style.animation = 'shake-notification 0.5s ease-in-out';
          toggleBtn.style.boxShadow = '0 0 20px rgba(74, 144, 226, 0.8)';

          setTimeout(() => {
            toggleBtn.style.animation = '';
            toggleBtn.style.boxShadow = '';
          }, 500);
        }
      }
      if (header && !currentUser) {
        header.textContent = `💬 ${window.CHAT_TRANSLATIONS.personal_chats} (${total})`;
      }
    } else {
      if (totalBadge) totalBadge.style.display = "none";
      if (toggleBtn) toggleBtn.classList.remove("has-unread");
      if (header && !currentUser) {
        header.textContent = `💬 ${window.CHAT_TRANSLATIONS.personal_chats}`;
      }
    }

    lastTotalUnread = total;
    totalBadgeUpdateTimer = null;
  }, 120);
}

// ===============================
// INITIALIZING UI
// ===============================
document.addEventListener("DOMContentLoaded", async () => {
    initializeChatUI();

    const sendBtn = document.getElementById("sendBtn");
    const chatInput = document.getElementById("chatInput");
    const fileAttachBtn = document.getElementById("fileAttachBtn");
    const fileInput = document.getElementById("fileInput");
    const filePreview = document.getElementById("filePreview");
    const filePreviewRemove = document.getElementById("filePreviewRemove");
    const fileSizeError = document.getElementById("fileSizeError");

    if (fileAttachBtn && fileInput) {
        fileAttachBtn.addEventListener("click", () => fileInput.click());
        
        fileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                handleFileSelect(file);
            }
        });
    }

    if (filePreviewRemove) {
        filePreviewRemove.addEventListener("click", clearFileSelection);
    }
    
    if (sendBtn) {
        sendBtn.addEventListener("click", sendMessage);
    }
    
    if (chatInput) {
        chatInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    const enableSoundOnInteraction = () => {
        console.log('👆 User interaction detected, enabling sound...');
        if (!soundEnabled) {
            enableSound();

            window.removeEventListener('click', enableSoundOnInteraction, true);
            window.removeEventListener('keydown', enableSoundOnInteraction, true);
            window.removeEventListener('scroll', enableSoundOnInteraction, true);
            window.removeEventListener('mousemove', enableSoundOnInteraction, true);
            document.removeEventListener('click', enableSoundOnInteraction, true);
            document.removeEventListener('keydown', enableSoundOnInteraction, true);
            console.log('✅ Sound enabled and all listeners removed');
        } else {
            console.log('ℹ️ Sound already enabled');
        }
    };

    window.addEventListener('click', enableSoundOnInteraction, true);
    window.addEventListener('keydown', enableSoundOnInteraction, true);
    window.addEventListener('scroll', enableSoundOnInteraction, true);
    window.addEventListener('mousemove', enableSoundOnInteraction, { once: true, capture: true });

    document.addEventListener('click', enableSoundOnInteraction, true);
    document.addEventListener('keydown', enableSoundOnInteraction, true);
    console.log('🎧 Sound activation listeners added (click, keydown, scroll, mousemove)');

    if (!window.CURRENT_USER_ID) {
        console.log("Not logged in — WebSockets skipped");
        return;
    }

    loadUnreadFromStorage();
    updateTotalUnread();
    Object.keys(unreadMessages).forEach(uid => updateBadge(uid));

    await syncUnreadCountsWithServer();

    await initializeWebSocketsWithTokenRefresh();

    startProactiveTokenRefresh();
});

// ===============================
// FILE HANDLING FUNCTIONS
// ===============================

function handleFileSelect(file) {
    // Проверка размера файла
    if (file.size > MAX_FILE_SIZE) {
        fileSizeError.classList.add("show");
        setTimeout(() => {
            fileSizeError.classList.remove("show");
        }, 3000);
        fileInput.value = "";
        return;
    }

    selectedFile = file;
    
    // Показываем предпросмотр
    document.getElementById("filePreviewName").textContent = file.name;
    document.getElementById("filePreviewSize").textContent = formatFileSize(file.size);
    filePreview.classList.add("show");
}

function clearFileSelection() {
    selectedFile = null;
    fileInput.value = "";
    filePreview.classList.remove("show");
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}



// ===============================
// CLOSING WEBSOCKET
// ===============================
window.addEventListener("beforeunload", () => {
    pageUnloading = true;

    if (tokenRefreshInterval) clearInterval(tokenRefreshInterval);

    Object.values(wsConnections).forEach(ws => {
        if (ws?.readyState === WebSocket.OPEN) ws.close(1000, "Page unload");
    });

    if (groupChatWs?.readyState === WebSocket.OPEN) {
        groupChatWs.close(1000, "Page unload");
    }
});


// ===============================
// PRESSING OUTER WIDGET
// ===============================
document.addEventListener("click", (e) => {
    const widget = document.getElementById("chatWidget");
    const win    = document.getElementById("chatWindow");
    const toggle = document.getElementById("chatToggleBtn");

    const open = widget.classList.contains("chat-widget-expanded");

    if (open && !win.contains(e.target) && !toggle.contains(e.target)) {
        widget.classList.remove("chat-widget-expanded");
        widget.classList.add("chat-widget-collapsed");
    }
});


// ===============================
// UI COMPONENTS
// ===============================
function initializeChatUI() {
    const toggleBtn = document.getElementById("chatToggleBtn");
    const closeBtn  = document.getElementById("chatCloseBtn");
    const backBtn   = document.getElementById("chatBackBtn");
    const widget    = document.getElementById("chatWidget");

    toggleBtn.addEventListener("click", () => {
        widget.classList.remove("chat-widget-collapsed");
        widget.classList.add("chat-widget-expanded");
        showUsersList();
        requestNotificationPermission();

        if (!soundEnabled) {
            enableSound();
        }
    });

    closeBtn.addEventListener("click", () => {
        widget.classList.remove("chat-widget-expanded");
        widget.classList.add("chat-widget-collapsed");

        Object.values(badgeUpdateTimers).forEach(t => clearTimeout(t));
        badgeUpdateTimers = {};

        if (totalBadgeUpdateTimer) {
            clearTimeout(totalBadgeUpdateTimer);
            totalBadgeUpdateTimer = null;
        }

        if (currentUser) clearUnreadBadge(currentUser);

        currentUser = null;
        isGroupChatActive = false;

        showUsersList();
    });

    backBtn.addEventListener("click", showUsersList);

    document.querySelectorAll(".chat-user").forEach(el => {
        el.addEventListener("click", () => {
            document.querySelectorAll(".chat-user")
                .forEach(u => u.classList.remove("active"));
            el.classList.add("active");

            const userId = el.dataset.userId;
            const name   = el.querySelector(".chat-user-name").textContent;

            if (!soundEnabled) {
                enableSound();
            }

            if (userId === "group") {
                openGroupChat();
            } else {
                openChat(userId, name);
            }
        });
    });
}


// ===============================
// TOKEN REFRESH
// ===============================
function startProactiveTokenRefresh() {
    console.log("Token auto-refresh every 10 min");

    refreshTokenAndReconnect();

    tokenRefreshInterval = setInterval(() => {
        refreshTokenAndReconnect();
    }, TOKEN_REFRESH_INTERVAL);
}


async function refreshTokenAndReconnect() {
    if (typeof refreshAccessToken !== "function") {
        console.warn("refreshAccessToken() unavailable");
        return false;
    }

    const ok = await refreshAccessToken();
    if (!ok) return false;

    lastTokenRefresh = Date.now();
    console.log("✓ Token refreshed");

    await new Promise(r => setTimeout(r, 500));

    await reconnectAllWebSockets();
    return true;
}


async function ensureTokenFresh(force = false) {
    const now = Date.now();

    if (force || !lastTokenRefresh || now - lastTokenRefresh > TOKEN_REFRESH_INTERVAL) {
        return refreshTokenAndReconnect();
    }

    return true;
}


// ===============================
// INITIALIZING ALL WEBSOCKET
// ===============================
async function initializeWebSocketsWithTokenRefresh() {
    if (websocketsInitialized) return true;

    const fresh = await ensureTokenFresh();
    if (!fresh) {
        alert("Не вдалося оновити сесію. Перезавантажте сторінку.");
        return false;
    }

    await new Promise(r => setTimeout(r, 500));

    document.querySelectorAll(".chat-user").forEach(el => {
        const userId = el.dataset.userId;
        if (userId && userId !== "group") {
            connectToUser(userId);
        }
    });

    connectGroupChat();

    websocketsInitialized = true;
    return true;
}


async function reconnectAllWebSockets() {
    console.log("Reconnecting WebSockets...");

    Object.values(wsConnections).forEach(ws => {
        if (ws?.readyState === WebSocket.OPEN) ws.close(1000, "Token refresh");
    });

    if (groupChatWs?.readyState === WebSocket.OPEN) {
        groupChatWs.close(1000, "Token refresh");
    }

    wsConnections = {};
    groupChatWs = null;

    await new Promise(r => setTimeout(r, 900));

    document.querySelectorAll(".chat-user").forEach(el => {
        const userId = el.dataset.userId;
        if (userId && userId !== "group") {
            connectToUser(userId);
        }
    });

    connectGroupChat();
}

// ===============================
// CHECK ACTIVE CHAT
// ===============================
function isCurrentChatActive(userId) {
    return String(currentUser) === String(userId);
}


// ===============================
// PRIVATE CHAT - CONNECTION
// ===============================
function connectToUser(userId) {
    const sUserId = String(userId);

    if (wsConnections[sUserId]) {
        return wsConnections[sUserId];
    }

    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const ws = new WebSocket(
        protocol + window.location.host +
        `/ws/chat/${sUserId}/?token=${encodeURIComponent(window.ACCESS_TOKEN)}`
    );

    wsConnections[sUserId] = ws;

    ws.addEventListener("open", () => {
        console.log(`WS → personal chat ${sUserId} connected`);
        subscribeHeartbeat(ws);
    });

    ws.addEventListener("close", (e) => {
        console.warn(`WS → personal ${sUserId} closed:`, e.code, e.reason);
        delete wsConnections[sUserId];

        if (!pageUnloading && e.code !== 1000) {
            console.log(`Reconnecting personal chat ${sUserId} in 1s...`);
            setTimeout(() => connectToUser(sUserId), 1000);
        }
    });

    ws.addEventListener("error", (err) => {
        console.error(`WS personal ${sUserId} error`, err);
    });

    // ===============================
    // BASIC LOGIC PRIVATE CHAT
    // ===============================
    ws.addEventListener("message", (event) => {
        let data;

        try {
            data = JSON.parse(event.data);
        } catch (e) {
            console.error("WS personal invalid JSON:", event.data);
            return;
        }

        if (data.type === "heartbeat" || data.type === "pong") return;

        const senderId = String(data.sender);
        const myId = String(window.CURRENT_USER_ID);

        const msg = data.message;
        const chatUserId = sUserId;

        console.log(
            `[Personal Chat WS] incoming msg from ${senderId} → chat ${chatUserId}`
        );

        if (isCurrentChatActive(chatUserId)) {
            console.log(`→ Rendering msg in active chat ${chatUserId}`);
            renderMessage(data, senderId);
        }

        const isFromMe = senderId === myId;
        const isActive = isCurrentChatActive(chatUserId);

        console.log(`[Personal Chat] Check notification:`, {
            senderId,
            myId,
            isFromMe,
            chatUserId,
            currentUser,
            isActive
        });

        if (!isFromMe && !isActive) {
            console.log(`→ Showing notification for user ${chatUserId}`);

            debouncedIncrementBadge(chatUserId);
            showChatNotification(chatUserId, msg);
            playNotificationSound();
        } else {
            console.log(`→ Notification skipped:`, { isFromMe, isActive });
        }
    });

    return ws;
}

// ===============================
// GROUP CHAT
// ===============================
function connectGroupChat() {
    if (groupChatWs) return groupChatWs;

    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";

    const ws = new WebSocket(
        protocol + window.location.host +
        `/ws/group-chat/?token=${encodeURIComponent(window.ACCESS_TOKEN)}`
    );

    groupChatWs = ws;

    ws.addEventListener("open", () => {
        console.log("WS → group chat connected");
        subscribeHeartbeat(ws);
    });

    ws.addEventListener("close", (e) => {
        console.warn(`WS group closed:`, e.code, e.reason);
        groupChatWs = null;

        if (!pageUnloading && e.code !== 1000) {
            console.log("Reconnecting group chat in 1s...");
            setTimeout(connectGroupChat, 1000);
        }
    });

    ws.addEventListener("error", (err) => {
        console.error("WS group error:", err);
    });

    // ===============================
    // LOGIC FOR GET MESSAGES
    // ===============================
    ws.addEventListener("message", (event) => {
        let data;

        try {
            data = JSON.parse(event.data);
        } catch (e) {
            console.error("WS group invalid JSON:", event.data);
            return;
        }

        if (data.type === "heartbeat" || data.type === "pong") return;

        const senderId   = String(data.sender);
        const senderName = data.sender_name;
        const myId       = String(window.CURRENT_USER_ID);
        const msg        = data.message;

        console.log(`[Group Chat WS] message from ${senderId}`);

        if (isGroupChatActive) {
            console.log("→ Rendering message in active group chat");

            renderGroupMessage(data, senderId, senderName);
        }

        const isFromMe = senderId === myId;

        console.log(`[Group Chat] Check notification:`, {
            senderId,
            myId,
            isFromMe,
            isGroupChatActive
        });

        if (!isFromMe && !isGroupChatActive) {
            console.log("→ Showing notification for GROUP CHAT");

            debouncedIncrementBadge("group");
            showChatNotification("group", msg, senderName);
            playNotificationSound();
        } else {
            console.log(`→ Group notification skipped:`, { isFromMe, isGroupChatActive });
        }
    });

    return ws;
}

// ===============================
// OPENING PRIVATE CHAT
// ===============================
async function openChat(userId, userName) {
    const sUserId = String(userId);
    const previous = currentUser;

    console.log(`Opening chat with ${sUserId} (previous: ${previous})`);

    currentUser = sUserId;
    isGroupChatActive = false;

    showChatView(userName);

    const body = document.getElementById("chatBody");
    body.classList.remove("group-chat-active");
    body.innerHTML = "";

    await loadMessages(sUserId);

    clearUnreadBadge(sUserId);

    // Автоскролл
    scrollChatToBottom();
}


// ===============================
// OPENING GROUP CHAT
// ===============================
async function openGroupChat() {
    const previous = currentUser;

    console.log(`Opening group chat (previous: ${previous})`);

    currentUser = "group";
    isGroupChatActive = true;

    showChatView(`👥 ${window.CHAT_TRANSLATIONS.group_chat}`);

    const body = document.getElementById("chatBody");
    body.classList.add("group-chat-active");
    body.innerHTML = "";

    await loadGroupMessages();

    clearUnreadBadge("group");

    scrollChatToBottom();
}


// ===============================
// LOAD MESSAGES FOR PRIVATE CHAT
// ===============================
async function loadMessages(userId) {
    try {
        const response = await fetch(`/chat/messages/${userId}/`);
        const data = await response.json();

        data.messages.forEach(msg => {
            renderMessage(msg, String(msg.sender));
        });
    } catch (e) {
        console.error("Failed to load messages:", e);
    }
}


// ===============================
// LOAD GROUP MESSAGES
// ===============================
async function loadGroupMessages() {
    try {
        const response = await fetch(`/chat/group-messages/`);
        const data = await response.json();

        data.messages.forEach(msg => {
            renderGroupMessage(
                msg,
                String(msg.sender),
                msg.sender_name
            );
        });
    } catch (e) {
        console.error("Failed to load group messages:", e);
    }
}


// ===============================
// CLEAN UNREAD FOR ACTIVE CHAT
// ===============================
function clearUnreadBadge(userId) {
    const sUserId = String(userId);

    if (!isCurrentChatActive(sUserId)) {
        console.warn(`Attempted to clear badge for inactive chat: ${sUserId}`);
        return;
    }

    console.log(`Clearing unread for: ${sUserId}`);

    unreadMessages[sUserId] = 0;
    saveUnreadToStorage();

    updateBadge(sUserId);
    updateTotalUnread();

    const lastSeenKey = "chatLastSeen";
    const lastSeen = JSON.parse(localStorage.getItem(lastSeenKey) || "{}");

    lastSeen[sUserId] = new Date().toISOString();
    localStorage.setItem(lastSeenKey, JSON.stringify(lastSeen));
}


// ===============================
// RENDER PERSONAL MESSAGES
// ===============================
function renderMessage(messageObj, senderId) {
    const body = document.getElementById("chatBody");
    if (!body) return;
    
    const myId = String(window.CURRENT_USER_ID);

    const div = document.createElement("div");
    div.className = "message " + (senderId === myId ? "me" : "other");
    
    // Если есть текст
    if (typeof messageObj === 'string') {
        div.textContent = messageObj;
    } else {
        if (messageObj.message) {
            const textSpan = document.createElement("div");
            textSpan.textContent = messageObj.message;
            div.appendChild(textSpan);
        }
        
        // Если есть файл
        if (messageObj.file && messageObj.file_url) {
            const fileLink = createFileElement(
                messageObj.file_name,
                messageObj.file_url,
                messageObj.file_size
            );
            div.appendChild(fileLink);
        }
    }

    div.style.opacity = '0';
    div.style.transform = 'translateY(10px)';

    body.appendChild(div);
    
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            div.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
            div.style.opacity = '1';
            div.style.transform = 'translateY(0)';
        });
    });
    
    scrollChatToBottom();
}


// ===============================
// RENDER GROUP MESSAGES
// ===============================
function renderGroupMessage(messageObj, senderId, senderName) {
    const body = document.getElementById("chatBody");
    if (!body) return;
    
    const myId = String(window.CURRENT_USER_ID);

    const div = document.createElement("div");
    div.className = "message group-message " + (senderId === myId ? "me" : "other");

    let content = `<div class="group-message-sender">${escapeHtml(senderName)}</div>`;
    
    if (typeof messageObj === 'string') {
        content += `<div class="group-message-text">${escapeHtml(messageObj)}</div>`;
    } else {
        if (messageObj.message) {
            content += `<div class="group-message-text">${escapeHtml(messageObj.message)}</div>`;
        }
    }
    
    div.innerHTML = content;
    
    // Добавляем файл если есть
    if (typeof messageObj === 'object' && messageObj.file && messageObj.file_url) {
        const fileLink = createFileElement(
            messageObj.file_name,
            messageObj.file_url,
            messageObj.file_size
        );
        div.appendChild(fileLink);
    }
 
    div.style.opacity = '0';
    div.style.transform = 'translateY(10px)';

    body.appendChild(div);
    
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            div.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
            div.style.opacity = '1';
            div.style.transform = 'translateY(0)';
        });
    });
    
    scrollChatToBottom();
}

function createFileElement(fileName, fileUrl, fileSize) {
    const fileLink = document.createElement("a");
    fileLink.href = fileUrl;
    fileLink.className = "message-file";
    fileLink.target = "_blank";
    fileLink.download = fileName;
    
    fileLink.innerHTML = `
        <div class="file-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"/>
            </svg>
        </div>
        <div class="file-info">
            <div class="file-name">${escapeHtml(fileName)}</div>
            ${fileSize ? `<div class="file-size">${fileSize}</div>` : ''}
        </div>
        <svg class="file-download-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
        </svg>
    `;
    
    return fileLink;
}


// ===============================
// SCROLL DOWN
// ===============================
function scrollChatToBottom() {
    const body = document.getElementById("chatBody");
    setTimeout(() => {
        body.scrollTop = body.scrollHeight;
    }, 30);
}


// ===============================
// ЭСКЕЙП HTML
// ===============================
function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}


// ===============================
// SHOW USERS LIST
// ===============================
function showUsersList() {
    const header = document.getElementById("chatHeaderText");
    const backBtn = document.getElementById("chatBackBtn");
    const usersList = document.getElementById("chatUsers");
    const chatBody = document.getElementById("chatBody");
    const chatInputBlock = document.getElementById("chatInputBlock");

    if (header) header.textContent = `💬 ${window.CHAT_TRANSLATIONS.personal_chats}`;
    if (backBtn) backBtn.style.display = "none";
    if (usersList) usersList.style.display = "block";
    if (chatBody) chatBody.style.display = "none";
    if (chatInputBlock) chatInputBlock.style.display = "none";

    currentUser = null;
    isGroupChatActive = false;

    updateTotalUnread();
}


// ===============================
// SHOW CHAT VIEW
// ===============================
function showChatView(userName) {
    const header = document.getElementById("chatHeaderText");
    const backBtn = document.getElementById("chatBackBtn");
    const usersList = document.getElementById("chatUsers");
    const chatBody = document.getElementById("chatBody");
    const chatInputBlock = document.getElementById("chatInputBlock");

    if (header) header.textContent = userName;
    if (backBtn) backBtn.style.display = "block";
    if (usersList) usersList.style.display = "none";
    if (chatBody) chatBody.style.display = "block";
    if (chatInputBlock) chatInputBlock.style.display = "flex";
}


// ===============================
// UPDATE BADGE FOR USER
// ===============================
function updateBadge(userId) {
    const sUserId = String(userId);
    const count = unreadMessages[sUserId] || 0;

    const userEl = document.querySelector(`.chat-user[data-user-id="${sUserId}"]`);
    if (!userEl) return;

    let badge = userEl.querySelector(".unread-badge");

    if (count > 0) {
        if (!badge) {
            badge = document.createElement("span");
            badge.className = "unread-badge";
            userEl.appendChild(badge);
        }
        badge.textContent = count;
        badge.style.display = "flex";
    } else {
        if (badge) {
            badge.style.display = "none";
        }
    }
}


// ===============================
// SYNC UNREAD З СЕРВЕРОМ
// ===============================
async function syncUnreadCountsWithServer() {
    try {
        const response = await fetch('/chat/unread-counts/');
        if (!response.ok) return;

        const data = await response.json();

        Object.keys(data).forEach(userId => {
            const count = data[userId];
            if (count > 0) {
                unreadMessages[userId] = count;
            }
        });

        saveUnreadToStorage();
        Object.keys(unreadMessages).forEach(uid => updateBadge(uid));
        updateTotalUnread();

        console.log("Unread counts synced with server");
    } catch (e) {
        console.error("Failed to sync unread counts:", e);
    }
}


// ===============================
// SOUND NOTIFICATIONS
// ===============================
function initNotificationSound() {
    if (!notificationSound) {
        notificationSound = new Audio('/static/js/chat/notification.mp3');
        notificationSound.volume = 0.3;
        
        notificationSound.load();
    }
}

async function enableSound() {
    soundEnabled = true;
    initNotificationSound();
    
    try {
        const originalVolume = notificationSound.volume;
        notificationSound.volume = 0;
        await notificationSound.play();
        notificationSound.pause();
        notificationSound.currentTime = 0;
        notificationSound.volume = originalVolume;
    } catch (err) {
        console.warn('⚠️ Could not unlock sound on first interaction:', err);
        console.log('🔊 Notification sound enabled (will try to play on next interaction)');
    }
}

function playNotificationSound() {
    
    if (!soundEnabled) {
        return;
    }
    
    if (!notificationSound) {
        initNotificationSound();
    }

    notificationSound.currentTime = 0;
    notificationSound.play()
        .then(() => console.log('✅ Sound played successfully'))
        .catch(err => {
            console.warn('❌ Failed to play notification sound:', err);
        });
}

function requestNotificationPermission() {
    if (!("Notification" in window)) return;

    if (Notification.permission === "default") {
        Notification.requestPermission();
    }
}


function showChatNotification(userId, message, senderName = null) {
    if (!("Notification" in window)) return;
    if (Notification.permission !== "granted") return;

    let title = "";
    if (userId === "group") {
        title = senderName ? `${senderName} (Група)` : "Групповий чат";
    } else {
        const userEl = document.querySelector(`.chat-user[data-user-id="${userId}"]`);
        const userName = userEl ? userEl.querySelector(".chat-user-name").textContent : "Користувач";
        title = userName;
    }

    const notification = new Notification(title, {
        body: message,
        tag: `chat-${userId}`,
        requireInteraction: false
    });

    notification.onclick = () => {
        window.focus();
        
        const widget = document.getElementById("chatWidget");
        widget.classList.remove("chat-widget-collapsed");
        widget.classList.add("chat-widget-expanded");

        if (userId === "group") {
            openGroupChat();
        } else {
            const userEl = document.querySelector(`.chat-user[data-user-id="${userId}"]`);
            if (userEl) {
                const userName = userEl.querySelector(".chat-user-name").textContent;
                openChat(userId, userName);
            }
        }

        notification.close();
    };

    setTimeout(() => notification.close(), 5000);
}


// ===============================
// HEARTBEAT FOR WEBSOCKET
// ===============================
function subscribeHeartbeat(ws) {
    const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'ping',
                timestamp: Date.now()
            }));
        } else {
            clearInterval(interval);
        }
    }, 60000);

    ws.addEventListener('close', () => clearInterval(interval));
}


// ===============================
// SENDING MESSAGES
// ===============================


async function sendMessage() {
    const input = document.getElementById("chatInput");
    const message = input.value.trim();

    // Проверяем что есть либо текст либо файл
    if (!message && !selectedFile) return;

    if (!soundEnabled) {
        enableSound();
    }

    // Показываем индикатор загрузки если есть файл
    const fileUploading = document.getElementById("fileUploading");
    const hasFile = !!selectedFile;
    
    if (hasFile) {
        fileUploading.classList.add("show");
    }

    try {
        // Подготавливаем данные
        const messageData = {
            message: message
        };

        // Если есть файл, конвертируем в base64
        if (selectedFile) {
            const fileBase64 = await fileToBase64(selectedFile);
            messageData.file = {
                name: selectedFile.name,
                content: fileBase64
            };
        }

        // Отправляем через WebSocket
        if (isGroupChatActive) {
            if (groupChatWs?.readyState === WebSocket.OPEN) {
                groupChatWs.send(JSON.stringify(messageData));
            } else {
                console.error("Group chat WebSocket not connected");
                throw new Error("WebSocket не подключен");
            }
        } else if (currentUser) {
            const ws = wsConnections[currentUser];
            if (ws?.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(messageData));
            } else {
                console.error(`WebSocket for user ${currentUser} not connected`);
                throw new Error("WebSocket не подключен");
            }
        }

        // Очищаем форму
        input.value = "";
        clearFileSelection();
        
    } catch (error) {
        console.error("Ошибка при отправке сообщения:", error);
        alert("Не вдалося відправити повідомлення. Спробуйте ще раз.");
    } finally {
        // Скрываем индикатор загрузки
        if (hasFile) {
            fileUploading.classList.remove("show");
        }
    }
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            // Убираем префикс "data:*/*;base64,"
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = error => reject(error);
    });
}
