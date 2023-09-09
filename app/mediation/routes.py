from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import current_user, login_required
from flask_socketio import join_room, send, emit
from app import socketio
from app.mediation import mediation_bp
from app import db
from app.models import User, Mediation, Agreement
from app.mediation.forms import MediationForm
from app.mediation.mediation_services import PrivateMediation, PublicMediation, MessagePublic

PUBLIC_MEDIATION_MODEL = "gpt-4"
open_mediators_private = {}
open_mediators_public = {}


def get_current_statement_from_db(mediation_id, user_id):
    mediation = Mediation.query.get_or_404(mediation_id)
    if user_id == mediation.initiator_id:
        return mediation.initiator_conflict_statement
    return mediation.other_conflict_statement


@mediation_bp.route('/start_mediation', methods=['GET', 'POST'])
@login_required
def start_mediation():
    global open_mediators_private
    form = MediationForm()
    if form.validate_on_submit():
        # Check if invitee is a username or email
        user = User.query.filter_by(username=form.invitee.data).first() or User.query.filter_by(
            email=form.invitee.data).first()

        other_user_id = user.id if user else None

        # Create new mediation
        mediation = Mediation(title=form.title.data, initiator_id=current_user.id, other_id=other_user_id)
        db.session.add(mediation)
        db.session.commit()

        if user:
            flash('Mediation started successfully!')
        else:
            # Send an email (mockup function)
            send_invite_email(form.invitee.data)
            flash('Invitation sent to email!')

        # create Mediation instance
        mediator = PrivateMediation(mediation_id=mediation.mediation_id, user_id=current_user.id)

        if mediation.mediation_id not in open_mediators_private.keys():
            open_mediators_private[mediation.mediation_id] = {}
        open_mediators_private[mediation.mediation_id][current_user.id] = mediator
        # session["mediation"][mediation.mediation_id] = {} # register mediation in the session
        return redirect(url_for('mediation.private_mediation', mediation_id=mediation.mediation_id))

    return render_template('mediation/start_mediation.html', form=form)


@mediation_bp.route('/continue_mediation')
@login_required
def continue_mediation():
    # Retrieve mediations for the logged-in user
    mediations = Mediation.query.filter(
        (Mediation.initiator_id == current_user.id) | (Mediation.other_id == current_user.id)).all()
    return render_template('mediation/continue_mediation.html', mediations=mediations)


@mediation_bp.route('/mediation_detail/<int:mediation_id>')
@login_required
def mediation_detail(mediation_id):
    global open_mediators_private
    global open_mediators_public
    mediation = Mediation.query.get_or_404(mediation_id)

    # Check if the user is part of this mediation
    if current_user.id not in [mediation.initiator_id, mediation.other_id]:
        flash('You are not part of this mediation.')
        return redirect(url_for('main.index'))

    # Check if conflict statements exist
    if current_user.id == mediation.initiator_id:
        if mediation.initiator_statement_committed:
            if mediation_id not in open_mediators_public.keys():
                mediator = PublicMediation(
                    mediation_id,
                    model=PUBLIC_MEDIATION_MODEL
                )
                open_mediators_public[mediation_id] = mediator
            return redirect(url_for('mediation.public_mediation', mediation_id=mediation_id))
        else:
            if mediation_id not in open_mediators_private.keys():
                open_mediators_private[mediation_id] = {}

            if current_user.id not in open_mediators_private[mediation_id].keys():
                mediator = PrivateMediation(
                    mediation_id=mediation_id,
                    user_id=current_user.id,
                    load_from_db=True
                )
                open_mediators_private[mediation.mediation_id][current_user.id] = mediator

            return redirect(url_for('mediation.private_mediation', mediation_id=mediation_id))
    else:
        if mediation.other_statement_committed:
            if mediation_id not in open_mediators_public.keys():
                mediator = PublicMediation(
                    mediation_id,
                    model=PUBLIC_MEDIATION_MODEL,
                )
                open_mediators_public[mediation_id] = mediator
            return redirect(url_for('mediation.public_mediation', mediation_id=mediation_id))
        else:
            if mediation_id not in open_mediators_private.keys():
                open_mediators_private[mediation_id] = {}

            if current_user.id not in open_mediators_private[mediation_id].keys():
                mediator = PrivateMediation(
                    mediation_id=mediation_id,
                    user_id=current_user.id,
                    load_from_db=True
                )

                open_mediators_private[mediation.mediation_id][current_user.id] = mediator
            return redirect(url_for('mediation.private_mediation', mediation_id=mediation_id))


@mediation_bp.route('/private_mediation/<int:mediation_id>')
def private_mediation(mediation_id):
    global open_mediators_private
    if mediation_id not in open_mediators_private.keys():
        open_mediators_private[mediation_id] = {}
    if current_user.id not in open_mediators_private[mediation_id].keys():
        new_mediator = PrivateMediation(mediation_id)
        open_mediators_private[mediation_id][current_user.id] = new_mediator
    mediator = open_mediators_private[mediation_id][current_user.id]
    messages = mediator.mediator.chat_history[1:]  # load chat history
    statement = get_current_statement_from_db(user_id=current_user.id, mediation_id=mediation_id)

    return render_template(
        'mediation/private_mediation.html',
        mediation_id=mediation_id,
        messages=messages,
        current_statement=statement,
    )

@mediation_bp.route('/handle_request_private', methods=['POST'])
def handle_request_private():
    """route to interact with the private mediator"""
    data = request.get_json()
    mediation_id = int(data.get('mediation_id'))
    mediator = open_mediators_private[mediation_id][current_user.id]
    mediation = Mediation.query.get_or_404(mediation_id)
    if mediation.initiator_id == current_user.id:
        mediator.current_conflict_statement = mediation.initiator_conflict_statement
    else:
        mediator.current_conflict_statement = mediation.other_conflict_statement

    input_data = data.get('input')

    # the user can edit the conflict statement in a text window. If he types in something there it is
    # returned by the statementInput field in the json.
    conflict_statement = data.get('statementInput')
    if conflict_statement == "None" or conflict_statement == "":
        conflict_statement = None

    if conflict_statement is not None and conflict_statement != mediator.current_conflict_statement:
        mediator.current_conflict_statement = conflict_statement
        if mediation.initiator_id == current_user.id:
            mediation.initiator_conflict_statement = conflict_statement
        else:
            mediation.other_conflict_statement = mediator.current_conflict_statement
        input_data = f"I adjusted the conflict statement: {conflict_statement}. {input_data}"
        # TODO: also make a system message.
        db.session.commit()

    output_data = mediator.send_request_to_openai(input_data)
    show_button = "###show_button###" in output_data

    mediator.add_to_db({"role": "user", "content": input_data})

    statement_text = mediator.extract_initial_statement()

    if statement_text:
        bot_message = mediator.mediator.chat_history[-2]["content"]
        mediator.add_to_db({"role": "assistant", "content": bot_message})
        mediator.current_conflict_statement = statement_text
        if mediation.initiator_id == current_user.id:
            mediation.initiator_conflict_statement = mediator.current_conflict_statement

        else:
            mediation.other_conflict_statement = mediator.current_conflict_statement
        mediator.add_to_db(mediator.mediator.chat_history[-1])
    else:
        bot_message = output_data
        mediator.add_to_db({"role": "assistant", "content": bot_message})
    db.session.commit()

    return jsonify({'output': bot_message, 'statementText': statement_text, 'showButton': show_button})

@mediation_bp.route('/submit_statement', methods=['POST'])
@login_required
def submit_statement():
    """Submit the comitting statement"""
    data = request.get_json()
    mediation_id = int(data.get('mediation_id'))
    statement = data.get('statement')
    mediation = Mediation.query.get_or_404(mediation_id)
    if mediation.initiator_id == current_user.id:
        mediation.initiator_statement_committed = True
        mediation.initiator_conflict_statement = statement
    else:
        mediation.other_statement_committed = True
        mediation.other_conflict_statement = statement

    db.session.commit()
    # TODO: redirect or some other logic for ending
    if mediation.initiator_statement_committed and mediation.other_statement_committed:
        socketio.emit('all_statements_submitted', {'status': 'complete'}, room=str(mediation_id))
    url = (url_for('mediation.public_mediation', mediation_id=mediation.mediation_id))
    return jsonify({"redirect": url})

@socketio.on('join')
def on_join(data):
    """join chatroom"""
    room = data['mediation_id']
    join_room(room)
    send({"message": f"a user has entered the room."}, room=room)


@mediation_bp.route('/public_mediation/<int:mediation_id>')
def public_mediation(mediation_id: int):
    """route to load up the public mediation page and all its functionality"""
    mediation = Mediation.query.get_or_404(mediation_id)
    global open_mediators_public
    if mediation_id not in open_mediators_public.keys():
        mediator = PublicMediation(
            mediation_id,
            model=PUBLIC_MEDIATION_MODEL
        )
        open_mediators_public[mediation_id] = mediator

    messages = db.session.query(
        MessagePublic.user_id,
        MessagePublic.role,
        MessagePublic.content
    ).filter_by(
        mediation_id=mediation_id
    ).order_by(
        MessagePublic.sequence_number
    ).all()

    if current_user.id == mediation.initiator_id:
        statement_self = mediation.initiator_conflict_statement
        statement_other = mediation.other_conflict_statement
        id_other = mediation.other_id
        name_other = User.query.get_or_404(id_other).username
    else:
        statement_self = mediation.other_conflict_statement
        statement_other = mediation.initiator_conflict_statement
        id_other = mediation.initiator_id
        name_other = User.query.get_or_404(id_other).username
    agreements_db = Agreement.query.filter_by(mediation_id=mediation_id).all()
    # Construct a list of dictionaries from the Agreement objects
    agreements = [{'title': agreement.agreement_title, 'text': agreement.agreement_statement} for agreement in agreements_db]

    return render_template(
        'mediation/public_mediation.html',
        user_id=current_user.id,
        mediation_id=mediation_id,
        conflict_statement_user=statement_self,
        conflict_statement_other=statement_other,
        name_other=name_other,
        messages=messages,
        agreements=agreements,
    )


@mediation_bp.route('/check_statements/<int:mediation_id>')
def check_statements(mediation_id):
    """check if both users have comitted their statemetns, before public mediation can start"""
    mediation = Mediation.query.get_or_404(mediation_id)
    return jsonify(
        {'all_statements_submitted': mediation.initiator_statement_committed and mediation.other_statement_committed})


@mediation_bp.route('/get_other_statement/<int:mediation_id>')
def get_other_statement(mediation_id):
    """got statement by other user"""
    mediation = Mediation.query.get_or_404(mediation_id)
    if mediation.initiator_id == current_user.id and mediation.other_statement_committed:
        other_statement = mediation.other_conflict_statement
    elif mediation.initiator_id != current_user.id and mediation.initiator_statement_committed:
        other_statement = mediation.initiator_conflict_statement
    else:
        other_statement = None
    return jsonify({'other_statement': other_statement})


@mediation_bp.route('/get-initial-bot-message', methods=['POST'])
def get_initial_bot_message():
    """check if bot has already created his greeting message"""
    global open_mediators_public
    data = request.get_json()
    mediation_id = int(data.get('mediation_id'))
    mediator = open_mediators_public[mediation_id]
    if mediator.initial_message_generated:
        return jsonify({"message": None})
    initial_message = mediator.send_request_to_openai("init")
    mediator.add_to_db({"role": "assistant", "content": initial_message})
    return jsonify({"message": initial_message})


def send_invite_email(email):
    """After creating mediation, send intvite to another user"""
    # To implement
    print(f"Invitation email sent to {email}!")



@socketio.on('send_message')
def handle_message(data):
    """sending messages in chat room"""
    mediator = open_mediators_public[int(data['mediation_id'])]
    input_data = data.get('message')
    user_id = current_user.id
    emit('receive_message', {'user_id': user_id, 'message': input_data}, room=data['mediation_id'])
    name = mediator.username_1 if user_id == mediator.userid_1 else mediator.username_2
    user_message = f"{name}: {input_data}"
    mediator.add_to_db(entry={"role": "user", "content": user_message}, user_id=user_id)
    # Get the bot response
    emit('bot_thinking', {'status': 'start'}, room=data['mediation_id'])
    output_data = mediator.send_request_to_openai(user_message)
    if output_data != "###continue###":
        mediator.add_to_db({"role": "assistant", "content": output_data})
        extracted_agreement = mediator.extract_agreement()
    else:
        extracted_agreement = None
    # Emit the bot's response back to the client
    emit('bot_thinking', {'status': 'stop'}, room=data['mediation_id'])
    emit('receive_message', {'user_id': 'bot', 'message': output_data, 'agreement': extracted_agreement},
         room=data['mediation_id'])


@socketio.on('respond_to_agreement')
def respond_to_agreement(data):
    """agree or disagree to generated agreement by bot"""
    mediator = open_mediators_public[int(data['mediation_id'])]
    agree = data.get("decision")
    comment = data.get('message')
    user_id = current_user.id

    output = "I agree " + comment if agree else "I disagree " + comment
    mediator.agreed[user_id] = agree
    mediator.to_respond_to_agreement[user_id] = False

    if True not in mediator.to_respond_to_agreement.values(): # check if all users submitted response
        all_responded = True
    else:
        all_responded = False
    emit(
        'receive_message',
        {'user_id': user_id, 'message': output, 'responded': True, 'all_responded': all_responded},
        room=data['mediation_id']
    )
    name = mediator.username_1 if user_id == mediator.userid_1 else mediator.username_2
    user_message = f"{name}: {output}"
    mediator.add_to_db(entry={"role": "user", "content": user_message}, user_id=user_id)
    if all_responded:
        new_agreement = mediator.commit_agreement() # will return False, if users did not agree
        if new_agreement:
            agreement_title, agreement_text = new_agreement
            emit('add_new_agreement', {'title': agreement_title, 'text': agreement_text})
        emit('bot_thinking', {'status': 'start'}, room=data['mediation_id'])
        output_data = mediator.send_request_to_openai(user_message, evaluate_agreement=True)
        if output_data != "###continue###":
            mediator.add_to_db({"role": "assistant", "content": output_data})
            extracted_agreement = mediator.extract_agreement()
        else:
            extracted_agreement = None
        # Emit the bot's response back to the client
        emit('bot_thinking', {'status': 'stop'}, room=data['mediation_id'])
        emit('receive_message', {'user_id': 'bot', 'message': output_data, 'agreement': extracted_agreement},
             room=data['mediation_id'])





