import ast
from flask import Blueprint, request, jsonify
from flask_mail import Message
from mongoengine import NotUniqueError

from app.collections.client_type import ClientTypes
from app.collections.credit_line import CreditLines
from app.collections.profile import Profiles
from app.collections.role import Roles
from app.collections.client import Clients
from app.collections.user import Users
from app.utils import response, rewrite_abort
from app.utils.auth.password_jwt import *

bp = Blueprint('auth', __name__, url_prefix='/')


@bp.route('/register', methods=['POST'])
def register():
    """
    Register User
    """
    if request.content_type == 'application/json':
        data = request.get_json()
    else:
        data = request.form

    profiles = []
    client, credit_line = None, None

    try:
        # Profiles
        names = ast.literal_eval(data['name'])
        last_names = ast.literal_eval(data['last_name'])
        ages = ast.literal_eval(data['age'])
        personal_ids = ast.literal_eval(data['personal_id'])
        incomes = ast.literal_eval(data['income'])
        employment_types = ast.literal_eval(data['employment_type'])

        client_type = ClientTypes.objects.get(
            employment_type=employment_types[0]
        )
        # Profiles
        for i in range(len(names)):
            if i > 0:
                if employment_types[i] != employment_types[i-1]:

                    client_type = ClientTypes.objects.get(
                        employment_type=employment_types[i]
                    )

            profile = Profiles(name=names[i], last_name=last_names[i],
                               age=ages[i],
                               personal_id=personal_ids[i],
                               income=incomes[i], client_type=client_type)

            profiles.append(profile)
        for profile in profiles:
            profile.save()

    except NotUniqueError as err:
        try:
            for profile in profiles:
                profile.delete()
        except Exception as err:
            pass
        rewrite_abort(422, err)

    except Exception as err:
        try:
            for profile in profiles:
                profile.delete()
        except Exception as err:
            pass
        rewrite_abort(400, err)

    try:
        # Credit Line
        budget = data['budget']
        initial_payment = data['initial_payment']
        financing_value = data['financing_value']
        credit_line_type = data['credit_line_type']
        financing_time = data['financing_time']

        credit_line = CreditLines(budget=budget,
                                  initial_payment=initial_payment,
                                  financing_value=financing_value,
                                  credit_line_type=credit_line_type,
                                  financing_time=financing_time)
        credit_line.save()

    except Exception as err:
        for profile in profiles:
            profile.delete()
        rewrite_abort(400, err)

    client = None
    try:
        email = data['email']
        password = encrypt_data(data, 'password')
        role_type = data['role_type']
        role = Roles.objects.get(type=role_type)
        client = Clients(email=email, password=password, role_type=role,
                         profile=profiles, credit_line=credit_line,
                         number_owners=len(profiles), referred_by='me')
        client.save()

    except NotUniqueError as err:
        for profile in profiles:
            profile.delete()
        credit_line.delete()
        rewrite_abort(422, err)

    except Exception as err:

        for profile in profiles:
            profile.delete()
        credit_line.delete()
        rewrite_abort(400, err)

    msg = Message('Hello', sender='yourId@gmail.com', recipients=['id1@gmail.com'])
    msg.body = "Hello Flask message sent from Flask-Mail"
    mail.send(msg)

    return jsonify(response(client.to_json()))


@bp.route('/login', methods=['POST'])
def login():
    """
    User login
    """

    if request.content_type == 'application/json':
        data = request.get_json()
    else:
        data = request.form

    try:
        user = Users.objects.get(
            email=data['email']
        )

        if not user.verified:
            if data['password'] == decrypt_data(user.password):
                return jsonify(response(generate_jwt(user)))
            else:
                err = 'Your password is incorrect.'
                rewrite_abort(401, err)

    except Exception as err:
        rewrite_abort(422, err)
