document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("submitChat").addEventListener("click", submitChat);
    document.getElementById("chatInput").addEventListener("keypress", function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            submitChat();
        }
    });
    document.getElementById("toggleStatementBtn").addEventListener("click", toggleStatement);
    document.getElementById("generateListBtn").addEventListener("click", generateList);
    // Disable chat input initially
    document.getElementById("chatInput").disabled = true;
    document.getElementById("submitChat").disabled = true;
    // Fetch the initial bot message
    fetchInitialBotMessage();

});

function toggleStatement() {
    const statementArea = document.getElementById("userStatementArea");
    const textarea = statementArea.querySelector("textarea");
    if (textarea.style.height && textarea.style.height !== "90%") {
        textarea.style.height = "90%";
    } else {
        textarea.style.height = "50px";
    }
}

function generateList() {
    const userStatementField = document.getElementById("userStatement");
    const userStatement = userStatementField.value;

    fetch('/generate-list', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ statement: userStatement }),
    })
    .then(response => response.json())
    .then(data => {
        userStatementField.value = data.result;
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function submitChat() {
    const chatDisplay = document.getElementById("chatDisplay");
    const chatInput = document.getElementById("chatInput");
    const userText = chatInput.value;
    chatInput.value = '';

    if (userText.trim() !== '') {
        // Display user's message immediately
        chatDisplay.innerHTML += `<div class="user-message">${userText}</div>`;
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'bot-message';
        typingIndicator.innerHTML = `
          <div id="typing-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        `;
        chatDisplay.appendChild(typingIndicator);

        fetch('/public_process_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({input: userText, user_id: user_id})
        })
            .then(response => response.json())
            .then(data => {
                const botText = data.output;
                chatDisplay.removeChild(typingIndicator);
                chatDisplay.innerHTML += `<div class="bot-message">${botText}</div>`;
                chatDisplay.scrollTop = chatDisplay.scrollHeight;
            })
            .catch(error => {
                console.error('Error:', error);
                // Remove the typing indicator in case of an error
                chatDisplay.removeChild(typingIndicator);
            });
    }
}
function fetchMessages() {
    fetch('/get-messages')
    .then(response => response.json())
    .then(data => {
        const chatDisplay = document.getElementById("chatDisplay");

        // Check if loading animation is currently being displayed
        const isLoadingDisplayed = document.getElementById("loadingAnimation");

        if (!isLoadingDisplayed) {
            chatDisplay.innerHTML = '';
        }

        data.messages.forEach(msg => {
            let cssClass = 'user-message';
            if (msg.user_id === 'bot') {
                cssClass = 'bot-message';
            } else if (msg.user_id !== user_id) {
                cssClass = 'other-user-message';
            }
            chatDisplay.innerHTML += `<div class="${cssClass}">${msg.message}</div>`;
        });
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    });
}
function fetchInitialBotMessage() {
    showLoadingAnimation();
    fetch('/get-initial-bot-message')
    .then(response => response.json())
    .then(data => {
        const chatDisplay = document.getElementById("chatDisplay");
        chatDisplay.innerHTML += `<div class="bot-message">${data.message}</div>`;
        hideLoadingAnimation();
        // Unfreeze user inputs
        document.getElementById("chatInput").disabled = false;
        document.getElementById("submitChat").disabled = false;
        // Start fetching messages periodically after the initial bot message is displayed
        setInterval(fetchMessages, 1000);
    });
}

function showLoadingAnimation() {
    const chatDisplay = document.getElementById("chatDisplay");
    const loadingDiv = document.createElement("div");
    loadingDiv.id = "loadingAnimation";
    loadingDiv.className = "bot-message";
    loadingDiv.innerHTML = `
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
    `;
    chatDisplay.appendChild(loadingDiv);
    chatDisplay.scrollTop = chatDisplay.scrollHeight; // Scroll to the bottom
}

function hideLoadingAnimation() {
    const loadingDiv = document.getElementById("loadingAnimation");
    if (loadingDiv) {
        loadingDiv.remove();
    }
}