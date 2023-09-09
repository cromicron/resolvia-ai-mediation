let chatHistory = []; // Initialize chat history

function sendData() {
    const inputText = document.getElementById('inputText');
    const message = inputText.value;
    const specialInputText = document.getElementById('specialInput');
    const specialMessage = specialInputText ? specialInputText.value : null;
    inputText.value = '';

    // Add user's message to chat history
    chatHistory.push(['User', message]);
    displayChat();

    $.ajax({
        url: 'http://127.0.0.1:5000/process-text',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 'input': message, 'specialInput': specialMessage }),
        success: function (response) {
            chatHistory.push(['Python', response.output]);
            displayChat();
            if (response.specialText) {
                displaySpecialText(response.specialText);
            }

            // show or hide outputButton based on the response
            if (response.showButton) {
                document.getElementById('submitStatementButton').style.display = 'block';
            } else {
                document.getElementById('submitStatementButton').style.display = 'none';
            }
        }
    });
}

// Add the functionality to send the message when Enter is pressed
document.getElementById("inputText").addEventListener("keydown", function(e) {
    if (e.keyCode === 13 && !e.shiftKey) {
        e.preventDefault();
        sendData();
    }
});

document.getElementById('specialButton').addEventListener('click', displaySpecialText);

function displayChat() {
    const chatBox = document.getElementById('chatBox');
    chatBox.innerHTML = '';

    chatHistory.forEach(item => {
        var message = document.createElement('div');
        message.textContent = item[1];
        message.className = item[0] === 'User' ? 'user-message' : 'bot-message';
        chatBox.appendChild(message);
    });

    scrollToBottom();
}

function scrollToBottom() {
    const chatBox = document.getElementById('chatBox');
    chatBox.scrollTop = chatBox.scrollHeight;
}

function displaySpecialText(specialText) {
    let specialArea = document.getElementById('specialArea');
    let specialContainer = document.getElementById('specialContainer');
    let chatWrapper = document.getElementById('chatWrapper');

    if (!specialArea.classList.contains('show')) {
        if (!document.getElementById('specialInput')) {
            specialContainer.innerHTML = '<textarea id="specialInput" class="special-input" rows="25" cols="50"></textarea>';
        }

        specialArea.classList.add('show');
        chatWrapper.classList.add('shrink');
    }

    document.getElementById('specialInput').value = specialText;
}
document.getElementById('submitStatementButton').addEventListener('click', function() {
    let specialInputText = document.getElementById('specialInput').value;

    $.ajax({
        url: '/end_initial_session',  // Flask route URL
        type: 'POST',
        data: JSON.stringify({ 'specialInput': specialInputText }),  // Send specialInput to backend
        contentType: 'application/json', // specify the content type
        success: function(response) {
            // Redirect to public_mediation only if end_session is successful
            window.location.href = "/public_mediation";
        }
    });
});

