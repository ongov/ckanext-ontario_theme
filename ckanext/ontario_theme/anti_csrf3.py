import anti_csrf
import webob
from webob.exc import HTTPForbidden

from flask import Flask, make_response, render_template, request
from ckan.common import config, is_flask_request
import ckan.lib.base as base

import logging

log = logging.getLogger(__name__)


CSRF_ERR = 'CSRF authentication failed. Token missing or invalid.'

domain = config.get('ckan.ontario_theme.csrf_domain', '')



def after_request_function(response):
    #request = Request(environ)
    #self.session = environ['beaker.session']
    #self.session.save()
    #if is_valid():
    resp = response
    #else:
    #    return response
    if 'text/html' in resp.headers.get('Content-type', ''):
        token = anti_csrf.get_response_token(request, resp)
        new_response = anti_csrf.apply_token(resp.get_data(as_text=True), token)
        resp.set_data(new_response)
        return resp

    else:
        return response

def is_valid():#
    return is_safe() or unsafe_request_is_valid()

def unsafe_request_is_valid():
#        return is_secure() and good_referer() and \
#               good_origin() and check_token()
    return check_token()

##############################################################################


def is_secure():
    # allow requests which have the x-forwarded-proto of https (inserted by nginx)
    if request.headers.get('X-Forwarded-Proto') == 'https':
        return True
    return request.scheme == 'https'

def is_safe():
    "Check if the request is 'safe', if the request is safe it will not be checked for csrf"
    # api requests are exempt from csrf checks
    if request.path.startswith("/api"):
        return True

    # get/head/options/trace are exempt from csrf checks
    return request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE')

def good_referer():
    "Returns true if the referrer is https and matching the host"
    if not request.headers.get('Referer'):
        return False
    else:
        match = "https://{}".format(domain)
        return request.headers.get('Referer').startswith(match)

def good_origin():
    """
    checks if the origin header is present and matches the header"
    :param domain: string: the expected origin domain
    :return: boolean: true if the origin header is present and matches the expected domain
    """
    origin = request.headers.get('origin', None)
    if not origin:
        log.warning("Potentially unsafe CSRF request is missing the origin header")
        return True
    else:
        match = "https://{}".format(domain)
        return origin.startswith(match)

def _get_post_token():
    """Retrieve the token provided by the client. Or return None if not present
        This is normally a single 'token' parameter in the POST body.
        However, for compatibility with 'confirm-action' links,
        it is also acceptable to provide the token as a query string parameter,
        if there is no POST body.
    """
    if request.environ['webob.adhoc_attrs'].has_key(anti_csrf.TOKEN_FIELD_NAME):
        return request.token
    # handle query string token if there are no POST parameters
    # this is needed for the 'confirm-action' JavaScript module
    if not request.method == 'POST' and (request.args.get(anti_csrf.TOKEN_FIELD_NAME) and len(request.args.get(anti_csrf.TOKEN_FIELD_NAME)) == 1):
        token = request.args.get(TOKEN_FIELD_NAME)
        #del request.GET[anti_csrf.TOKEN_FIELD_NAME]
        return token
    post_tokens = request.form.getlist(anti_csrf.TOKEN_FIELD_NAME)
    if not post_tokens or len(post_tokens) != 1:
        return None
    token = post_tokens[0]
    # drop token from request so it doesn't populate resource extras
    #del request.POST[anti_csrf.TOKEN_FIELD_NAME]
    return token

def get_cookie_token():
    """Retrieve the token expected by the server.
       This will be retrieved from the 'token' cookie
       """
    if anti_csrf.TOKEN_FIELD_NAME in request.cookies:
        log.debug("Obtaining token from cookie")
        return request.cookies.get(anti_csrf.TOKEN_FIELD_NAME)
    else:
        return None

def check_token():
    log.debug("Checking token matches Token {}, cookie_token: {}".format(_get_post_token(), get_cookie_token()))
    return _get_post_token() is not None and _get_post_token() == get_cookie_token()

