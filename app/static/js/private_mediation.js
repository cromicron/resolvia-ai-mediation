document.addEventListener("DOMContentLoaded", function() {
  document.getElementById("submitChat").addEventListener("click", submitChat);
  document.getElementById("chatInput").addEventListener("keypress", function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      submitChat();
    }
  });

  document.getElementById("showStatement").addEventListener("click", function() {
    document.getElementById("statementInput").style.display = 'block';
  });

  document.getElementById("submitStatement").addEventListener("click", function() {
    document.getElementById("statementInput").style.display = 'none';
  });
});

function submitChat() {
  const chatInput = document.getElementById("chatInput");
  const chatDisplay = document.getElementById("chatDisplay");
  const statementInput = document.getElementById("statementInput");
  const userText = chatInput.value;
  chatInput.value = '';

  if (userText.trim() !== '') {
    chatDisplay.innerHTML += `<div class="user-message">${userText}</div>`;
    chatDisplay.scrollTop = chatDisplay.scrollHeight;

    // Create a new typing indicator and append it to the chat
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
    let mediationId = document.body.getAttribute('data-mediation-id');
    // Send data to server
    fetch('/handle_request_private', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({input: userText, statementInput: statementInput.value, mediation_id: mediationId})
    })
    .then(response => response.json())
    .then(data => {
      const botText = data.output;

      // Remove the typing indicator
      chatDisplay.removeChild(typingIndicator);

      // Add the bot's message to the chat
      chatDisplay.innerHTML += `<div class="bot-message">${botText}</div>`;
      chatDisplay.scrollTop = chatDisplay.scrollHeight;

      // If statementText is not null or empty, show the statement text area and set its value
      if (data.statementText) {
        statementInput.style.display = 'block';
        statementInput.value = data.statementText;
      }
    })
    .catch(error => {
      console.error('Error:', error);

      // Remove the typing indicator in case of an error
      chatDisplay.removeChild(typingIndicator);
    });
  }
}

document.getElementById("submitStatement").addEventListener("click", function(event) {
    const confirmationMessage = "Submitting the statement concludes your private session with your mediator. The statement will be sent to the other person. You cannot change the statement anymore. By submitting you commit that the statement is your true perspective of the conflict. Your statement will serve as a basis for the public mediation.";
    const statementInput = document.getElementById("statementInput");
    const statementText = statementInput.value;

    // Prevent the default action right away
    event.preventDefault();

    if (window.confirm(confirmationMessage)) {
        // If user confirms, then proceed with the submission logic
        let mediationId = document.body.getAttribute('data-mediation-id');

        // Send data to server
        fetch('/submit_statement', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({mediation_id: mediationId, statement: statementText})
        })
        .then(response => response.json())
        .then(data => {
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        })
        .catch(error => console.error('Error:', error));
    }
});

