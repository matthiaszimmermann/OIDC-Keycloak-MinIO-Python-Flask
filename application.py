
# Copyright (c) 2016, Patrick Uiterwijk <patrick@puiterwijk.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import logging

from flask import Flask, g, Response
from flask_oidc import OpenIDConnect

OIDC_REALM = 'acme'
OIDC_CLIENT_ID = 'system_a'
API_ROLE_1 = 'api_1'
API_ROLE_2 = 'api_2'

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config.update({
    'OIDC_OPENID_REALM': OIDC_REALM,
    'OIDC_CLIENT_SECRETS': 'client_secrets_acme.json', # classic mode
    # 'OIDC_CLIENT_SECRETS': 'client_secrets_acme_ip.json', # docker mode
    'SECRET_KEY': 'choose-something-here',
    'TESTING': True,
    'DEBUG': True,
    'OIDC_TOKEN_TYPE_HINT': 'access_token',
    'OIDC_ID_TOKEN_COOKIE_SECURE': False,
    'OIDC_REQUIRE_VERIFIED_EMAIL': False,
})

oidc = OpenIDConnect(app)

def get_user_info(oidc):
    info = oidc.user_getinfo(['sub', 'preferred_username', 'family_name', 'given_name', 'email'])
    logging.info('oidc.user_getinfo {}'.format(info))

    return info

@app.route('/')
def hello_world():
    logging.info('/')

    if oidc.user_loggedin:
        return ('Hello, %s, <a href="/private">See private</a> '
                '<a href="/logout">Log out</a>') % \
            oidc.user_getfield('email')
    else:
        return 'Welcome anonymous, <a href="/private">Log in</a>'


@app.route('/private')
@oidc.require_login
def hello_me():
    logging.info('/private')

    info = get_user_info(oidc)
    return ('Hello, %s (%s)! <a href="/">Return</a>' %
            (info.get('given_name'), info.get('email')))


# TODO reenable scpoes for accept_token
@app.route('/api', methods=['GET'])
@oidc.accept_token(require_token=True)
# @oidc.require_keycloak_role(OIDC_CLIENT_ID, API_ROLE_1)
def hello_api():
    token_info = g.oidc_token_info
    logging.info('endpoint /api')
    logging.info('g.oidc_token_info {}'.format(json.dumps(token_info, indent=2)))

    if not require_keycloak_role(token_info, OIDC_CLIENT_ID, API_ROLE_1):
        logging.warning('access denied, required role {}:{} missing'.format(OIDC_CLIENT_ID, API_ROLE_1))
        return Response(json.dumps({'error': 'access denied, required role missing'}), status=403)

    sub_info = '{} ({})'.format(token_info['preferred_username'], token_info['sub'])
    return json.dumps({'message': 'hello from endpoint /api1: welcome {}'.format(sub_info)})


# TODO reenable scpoes for accept_token
@app.route('/api2', methods=['GET'])
@oidc.accept_token(require_token=True)
# @oidc.require_keycloak_role(OIDC_CLIENT_ID, API_ROLE_2)
def hello_api2():
    token_info = g.oidc_token_info
    logging.info('endpoint /api')
    logging.info('g.oidc_token_info {}'.format(json.dumps(token_info, indent=2)))

    if not require_keycloak_role(token_info, OIDC_CLIENT_ID, API_ROLE_2):
        logging.warning('access denied, required role {}:{} missing'.format(OIDC_CLIENT_ID, API_ROLE_2))
        return Response(json.dumps({'error': 'access denied, required role missing'}), status=403)

    sub_info = '{} ({})'.format(token_info['preferred_username'], token_info['sub'])
    return json.dumps({'message': 'hello from endpoint /api2: welcome {}'.format(sub_info)})


# TODO replace once supported by framework
# should be available with version 1.5 of flask-OIDC
# def require_keycloak_role(self, client, role):
# see https://github.com/puiterwijk/flask-oidc/blob/master/flask_oidc/__init__.py
def require_keycloak_role(token_info, client, role):
    if client in token_info['resource_access']:
        return role in token_info['resource_access'][client]['roles']

    return False

@app.route('/logout')
def logout():
    logging.info('/logout')

    oidc.logout()
    return 'Hi, you have been logged out! <a href="/">Return</a>'


if __name__ == '__main__':
    # app.run(host='0.0.0.0') # docker mode
    app.run(host='localhost', port=5002) # classic mode

