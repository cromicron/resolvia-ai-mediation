let socket;
let mediationId;
let thinkingAnimationElement;

document.addEventListener("DOMContentLoaded", function () {
    mediationId = document.body.getAttribute('data-mediation-id');
    socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    socket.emit('join', { mediation_id: mediationId});
    socket.on('all_statements_received', function() {
        fetchInitialBotMessage(mediationId);
    });
    // Event listeners


    document.getElementById("submitChat").addEventListener("click", submitChat);
    document.getElementById("chatInput").addEventListener("keypress", function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            submitChat();
        }
    });
    document.getElementById("toggleStatementBtn").addEventListener("click", toggleStatement);
    document.getElementById("generateListBtn").addEventListener("click", generateList);
    document.getElementById("toggleSidebar").addEventListener("click", toggleSidebar);

    // Initial setup
    document.getElementById("chatInput").disabled = true;
    document.getElementById("submitChat").disabled = true;

    checkStatementsCommitted(mediationId);

    // Additional Event Listeners
    document.getElementById("chatInput").addEventListener("focus", function () {
        isInputFocused = true;
    });
    document.getElementById("chatInput").addEventListener("blur", function () {
        isInputFocused = false;
    });

    const chatDisplay = document.getElementById("chatDisplay");
    chatDisplay.addEventListener("scroll", function () {
        userHasScrolledUp = chatDisplay.scrollTop + chatDisplay.clientHeight < chatDisplay.scrollHeight;
    });
    socket.on('receive_message', function(data) {
        const chatDisplay = document.getElementById("chatDisplay");
        let cssClass;

        if (data.user_id === 'bot') {
            cssClass = 'bot-message';
        } else if (data.user_id.toString() !== user_id.toString()) {
            cssClass = 'other-user-message';
        } else if(data.user_id.toString() === user_id.toString()){
            cssClass = 'user-message'
        }
        if (data.message !== '###continue###') {
            chatDisplay.innerHTML += `<div class="${cssClass}">${data.message}</div>`;
        }
        forceScrollToLatestMessage(chatDisplay);  // Force scroll to show the latest message

        // Show agreement in modal if available
        if (data.agreement) {
            document.getElementById("chatInput").disabled = true;
            document.getElementById("submitChat").disabled = true;
            showModal(data.agreement);
        }
        if (data.all_responded){
            document.getElementById("chatInput").disabled = false;
            document.getElementById("submitChat").disabled = false;
        }
    });
    socket.on('bot_thinking', function(data) {
        const chatDisplay = document.getElementById("chatDisplay");
        if (data.status === 'start') {
            document.getElementById("chatInput").disabled = true;
            document.getElementById("submitChat").disabled = true;
            chatDisplay.innerHTML += `<div class="bot-message typing-animation" id="thinkingAnimation"><span>.</span><span>.</span><span>.</span></div>`;
            thinkingAnimationElement = document.getElementById("thinkingAnimation");
        } else if (data.status === 'stop') {
            thinkingAnimationElement.remove();
            document.getElementById("chatInput").disabled = false;
            document.getElementById("submitChat").disabled = false;
        }
    });

    socket.on('add_new_agreement', function(data) {
        addNewAgreement(data.title, data.text);
    });
});

let isInputFocused = false;
let userHasScrolledUp = false;

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const toggleButton = document.getElementById("toggleSidebar");
    const statementArea = document.querySelector(".statement-area");
    const chatArea = document.querySelector(".chat-area");

    if (sidebar.style.display === "none" || sidebar.style.display === "") {
        sidebar.style.display = "block";
        statementArea.style.marginLeft = "20%";
        statementArea.style.width = "30%";
        chatArea.style.width = "45%";
        toggleButton.style.left = "calc(15% - 20px)";  // Adjust the button's position to be within the sidebar
    } else {
        sidebar.style.display = "none";
        statementArea.style.marginLeft = "0";
        statementArea.style.width = "35%";
        chatArea.style.width = "50%";
        toggleButton.style.left = "10px";  // Move the button back to its original position
    }
}

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
    const chatInput = document.getElementById("chatInput");
    const userText = chatInput.value;
    chatInput.value = '';
    if (userText.trim() !== '') {
        // Emit the user's message to the server
        socket.emit('send_message', {
            message: userText,
            user_id: user_id.toString(),
            mediation_id: mediationId
        });
    }
}

function checkStatementsCommitted(mediationId) {
    fetch(`/check_statements/${mediationId}`)
    .then(response => response.json())
    .then(data => {
        if (data.all_statements_submitted) {
            // Fetch the other user's statement first
            fetchOtherUserStatement(mediationId);
        } else {
            displayWaitingMessage();
            setTimeout(() => checkStatementsCommitted(mediationId), 5000);
        }
    })
    .catch(error => {
        console.error("Error checking statements:", error);
    });
}

function fetchOtherUserStatement(mediationId) {
    fetch(`/get_other_statement/${mediationId}`)
    .then(response => response.json())
    .then(data => {
        // Update the other statement textarea with the fetched data
        const otherStatementArea = document.getElementById("otherStatement");
        otherStatementArea.textContent = data.other_statement;

        // Now fetch the initial bot message
        fetchInitialBotMessage(mediationId);
    })
    .catch(error => {
        console.error("Error fetching other user's statement:", error);
    });
}

function displayWaitingMessage() {
    const chatDisplay = document.getElementById("chatDisplay");
    const existingWaitingMessage = document.getElementById("waitingMessage");

    // If the waiting message is already displayed, don't display it again
    if (existingWaitingMessage) {
        return;
    }

    chatDisplay.innerHTML += `<div class="bot-message" id="waitingMessage">Waiting for the other user to submit their statement...</div>`;
}


function fetchInitialBotMessage(mediationId) {
    fetch('/get-initial-bot-message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mediation_id: mediationId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            const chatDisplay = document.getElementById("chatDisplay");
            chatDisplay.innerHTML += `<div class="bot-message">${data.message}</div>`;
        }
        document.getElementById("chatInput").disabled = false;
        document.getElementById("submitChat").disabled = false;
    });
}
function forceScrollToLatestMessage(chatDisplay) {
    chatDisplay.scrollTop = chatDisplay.scrollHeight;
}

// Modal functionality
function showModal(agreementText) {
    document.getElementById('agreement-text').innerText = agreementText;
    document.getElementById('user-comments').value = ''; // Clear comments textbox
    document.getElementById('modal-overlay').style.display = 'flex';
}

function hideModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

document.getElementById('agree-btn').addEventListener('click', function() {
    const userComments = document.getElementById('user-comments').value;
    // Handle agree action and use userComments if needed.
    socket.emit('respond_to_agreement', {
            decision: true,
            message: userComments,
            user_id: user_id.toString(),
            mediation_id: mediationId
        });
    hideModal();
});

document.getElementById('disagree-btn').addEventListener('click', function() {
    const userComments = document.getElementById('user-comments').value;
    socket.emit('respond_to_agreement', {
            decision: false,
            message: userComments,
            user_id: user_id.toString(),
            mediation_id: mediationId
        });
    hideModal();
});


function addNewAgreement(title, text) {
    const agreementTitles = document.getElementById("agreementTitles");

    // Create a new list item element
    const listItem = document.createElement('li');

    // Create a new title element
    const titleElement = document.createElement('h3');
    titleElement.textContent = title;
    titleElement.classList.add("agreement-title");

    // Add event listener to the title to toggle its associated text
    titleElement.addEventListener("click", function() {
        const content = titleElement.nextElementSibling;

        if (content.classList.contains("hidden")) {
            content.classList.remove("hidden");
        } else {
            content.classList.add("hidden");
        }
    });

    // Create a new text element and hide it by default
    const textElement = document.createElement('p');
    textElement.textContent = text;
    textElement.classList.add("hidden");

    // Append the title and text elements to the list item
    listItem.appendChild(titleElement);
    listItem.appendChild(textElement);

    // Append the list item to the agreement titles list
    agreementTitles.appendChild(listItem);
}


document.getElementById("viewAgreementsBtn").addEventListener("click", function() {
    const agreementList = document.getElementById("agreementList");

    if (agreementList.classList.contains("hidden")) {
        agreementList.classList.remove("hidden");
    } else {
        agreementList.classList.add("hidden");
    }
});

// This handles the toggle for individual agreements based on their titles
document.querySelectorAll(".agreement-title").forEach(title => {
    title.addEventListener("click", function() {

        // 1. Hide all agreement contents
        document.querySelectorAll('.agreement-content').forEach(content => {
            content.classList.add('hidden');
        });

        // 2. Toggle the content of the clicked title
        const content = title.nextElementSibling;
        content.classList.remove('hidden');
    });
});



function populateAgreementTitles(agreements) {
    const agreementTitles = document.getElementById("agreementTitles");
    agreementTitles.innerHTML = "";

    agreements.forEach((agreement, index) => {
        const listItem = document.createElement("li");
        listItem.textContent = agreement.title;
        listItem.addEventListener("click", function() {
            showSelectedAgreement(agreements[index]);
        });
        agreementTitles.appendChild(listItem);
    });
}

function showSelectedAgreement(agreement) {
    const selectedAgreement = document.getElementById("selectedAgreement");
    const selectedAgreementTitle = document.getElementById("selectedAgreementTitle");
    const selectedAgreementContent = document.getElementById("selectedAgreementContent");

    selectedAgreementTitle.textContent = agreement.title;
    selectedAgreementContent.textContent = agreement.text;
    selectedAgreement.classList.remove("hidden");
}
