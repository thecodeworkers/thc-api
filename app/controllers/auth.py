import ast
from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from marshmallow import ValidationError
from mongoengine import NotUniqueError

from app.collections.client_type import ClientTypes
from app.collections.credit_line import CreditLines
from app.collections.profile import Profiles
from app.collections.role import Roles
from app.collections.client import Clients
from app.collections.user import Users
from app.schemas.client_schema import SaveClientInput
from app.schemas.credit_line_schema import SaveCreditLineInput
from app.schemas.profile_schema import SaveProfileInput
from app.utils import response, rewrite_abort, parser_one_object
from app.utils.auth.password_jwt import *
from app.utils.auth.token import generate_confirmation_token, confirm_token
from app.utils.config.email import send_mail

bp = Blueprint('auth', __name__, url_prefix='/')


@bp.route('/register', methods=['POST'])
def register():
    """
    Register User
    """
    profiles = []
    credit_line_instance = None
    new_user_instance = None
    try:
        for profile in request.json['profiles']:
            profile['client_type'] = ClientTypes.objects.get(employment_type=profile['client_type'])
            profiles.append(profile)
        profiles = SaveProfileInput(many=True).load(profiles, unknown='EXCLUDE')
        for i in range(len(profiles)):
            profiles[i] = Profiles(**profiles[i]).save()

    except ValidationError as err:
        rewrite_abort(400, err)
    except NotUniqueError as err:
        rewrite_abort(422, err)
    except Exception as err:
        rewrite_abort(500, err)

    # Credit Line
    try:
        schema = SaveCreditLineInput()
        credit_line = schema.load(request.json['credit_line'], unknown='EXCLUDE')
        credit_line_instance = CreditLines(**credit_line).save()

    except ValidationError as err:
        for profile in profiles:
            profile.delete()
        rewrite_abort(400, err)
    except Exception as err:
        for profile in profiles:
            profile.delete()
        rewrite_abort(500, err)

    try:
        request.json['password'] = encrypt_data(request.json, 'password')
        request.json['role_type'] = Roles.objects.get(type=request.json['role_type'])
        request.json['profiles'] = profiles
        request.json['credit_line'] = credit_line_instance

        client_instance = SaveClientInput().load(request.json, unknown='EXCLUDE')

        new_user_instance = Clients(**client_instance).save()

        token = generate_confirmation_token(new_user_instance.email)
        # return '{}'.format(token)
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        html = render_template('send_confirmation.html', confirm_url=confirm_url)
        subject = "Please confirm your email"
        send_mail(new_user_instance.email, html, subject)

        return response(parser_one_object(new_user_instance)), 201

    except NotUniqueError as err:
        new_user_instance.delete()
        credit_line_instance.delete()
        for profile in profiles:
            profile.delete()
        rewrite_abort(422, err)

    except Exception as err:
        new_user_instance.delete()
        credit_line_instance.delete()
        for profile in profiles:
            profile.delete()
        rewrite_abort(400, err)


@bp.route('/confirm/<token>', methods=['GET'])
def confirm_email(token):
    email = None
    try:
        email = confirm_token(token)
    except Exception as err:
        rewrite_abort(410, err)

    user = Users.objects.get(email=email)
    if user.verified:
        pass
    else:
        user.verified = True
        user.update()
    return response(parser_one_object(user)), 201


@bp.route('/login', methods=['POST'])
def login():
    """
    User login
    """

    try:
        data = request.json

        user = Users.objects.get(
            email=data['email']
        )

        if not user.verified:
            if data['password'] == decrypt_data(user.password):
                return response(generate_jwt(user))
            else:
                err = 'Your password is incorrect.'
                rewrite_abort(401, err)

    except Exception as err:
        rewrite_abort(422, err)
