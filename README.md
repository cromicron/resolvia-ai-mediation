# Conflict Mediation Assistant

The **Conflict Mediation Assistant** offers a structured approach to conflict resolution. Whether dealing with workplace disagreements, personal disputes, or other conflicts, this platform uses the power of GPT to guide participants through a mediation process.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Features

- **Private Mediation**: Dive deep into the conflict with the guidance of your AI-Mediator. Once you've grasped your stance, the system aids you in crafting a well-articulated statement about the dispute.
  
- **Public Mediation**: Engage in constructive dialogue with the other party, facilitated by your AI-Mediator.

- **Agreement Tool**: The AI-Mediator assists both participants in reaching mutual agreements, methodically steering the conversation towards conflict resolution.

## Installation

1. **Setting Up a Virtual Environment**:
    - Install `virtualenv`:
      ```
      pip install virtualenv
      ```
    - Activate the virtual environment:
      ```
      virtualenv venv
      source venv/bin/activate
      ```
      For Windows:
      ```
      .\venv\Scripts\activate
      ```

2. **Clone and Setup**:
    - Clone the repository:
      ```
      git clone https://github.com/LMU-Seminar-LLMs/conflict-mediation-assistant.git
      ```
    - Navigate to the project directory and install dependencies:
      ```
      cd conflict-mediation-assistant
      pip install -r requirements.txt
      ```
    - Add your OpenAI credentials to `.env_template` and rename the file to `.env`. If you don't wish to use an organization, simply remove the relevant line.

3. **Run the Application**:
   - From the root directory, execute:
     ```
     python -m flask run
     ```
     
   - open ```http://127.0.0.1:5000``` in a browser.

     

## Usage

To experience the Conflict Mediation Assistant locally before deploying on a server, follow the steps below:

1. **User Registration**:
    - From the  **main page** click on register.
    - Register two distinct users.
    - Ensure you retain the login credentials for both.

2. **Starting a Mediation**:
    - Initiate a new mediation session.
    - Provide a relevant **title**.
    - Invite the second user by entering their **username**. For testing purposes it MUST be a registered user,

3. **Private Mediation Phase**:
    - Interact with your AI-Mediator for an in-depth understanding of the conflict.
    - The AI-Mediator will generate a conflict statement for you.
    - Collaborate with the AI in the **statement section** on the right.
    - Once satisfied, **submit** the statement to transition to the public mediation space.

4. **Public Mediation Phase**:
    - The invited second user should **log in** from a separate browser.
    - They must also navigate through their private mediation phase.
    - Once both users have completed their statements, the shared AI-Mediator will facilitate a conversation in the public space to help both parties reach a resolution.



## License

This project falls under the [MIT License](LICENSE.md).
