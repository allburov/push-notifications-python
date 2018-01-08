"""Pusher Push Notifications Python server SDK"""

import json
import re

import requests
import six

SDK_VERSION = '0.9.0'
INTEREST_MAX_LENGTH = 164
INTEREST_REGEX = re.compile('^(_|=|@|,|\\.|:|[A-Z]|[a-z]|[0-9])*$')


class PusherValidationError(ValueError):
    """Error thrown when the Push Notifications publish body is invalid"""
    pass

class PusherAuthError(ValueError):
    """Error thrown when the Push Notifications secret key is incorrect"""
    pass

class PusherMissingInstanceError(KeyError):
    """Error thrown when the instance id used does not exist"""
    pass

class PusherServerError(Exception):
    """Error thrown when the Push Notifications service has an internal server
    error
    """
    pass

def handle_http_error(response_body, status_code):
    """Handle different http error codes from the Push Notifications service"""
    error_string = '{}: {}'.format(
        response_body.get('error', 'Unknown error'),
        response_body.get('description', 'no description'),
    )
    if status_code == 401:
        raise PusherAuthError(error_string)
    elif status_code == 404:
        raise PusherMissingInstanceError(error_string)
    elif 400 <= status_code < 500:
        raise PusherValidationError(error_string)
    elif 500 <= status_code < 600:
        raise PusherServerError(error_string)


class PushNotifications(object):
    """Pusher Push Notifications API client
    This client class can be used to publish notifications to the Pusher
    Push Notifications service"""

    def __init__(self, instance_id, secret_key, endpoint=None):
        if not isinstance(instance_id, six.string_types):
            raise TypeError('instance_id must be a string')
        if not isinstance(secret_key, six.string_types):
            raise TypeError('secret_key must be a string')
        if (endpoint is not None
                and not isinstance(endpoint, six.string_types)):
            raise TypeError('endpoint must be a string')

        self.instance_id = instance_id
        self.secret_key = secret_key
        self._endpoint = endpoint

    @property
    def endpoint(self):
        """Property method to calculate the correct Pusher API host"""
        default_endpoint = '{}.pushnotifications.pusher.com'.format(
            self.instance_id,
        ).lower()
        return self._endpoint or default_endpoint

    def publish(self, interests, publish_body):
        """Publish the given publish_body to the specified interests.

        Args:
            interests (list): List of interests that the publish body should
                be sent to.
            publish_body (dict): Dict containing the body of the push
                notification publish request.
                (see https://docs.pusher.com/push-notifications)

        Returns:
            A dict containing the publish response from the Pusher Push
            Notifications service.
            (see https://docs.pusher.com/push-notifications)

        Raises:
            TypeError: if interests is not a list
            TypeError: if publish_body is not a dict
        """
        if not isinstance(interests, list):
            raise TypeError('interests must be a list')
        if not isinstance(publish_body, dict):
            raise TypeError('publish_body must be a dictionary')
        if not interests:
            raise ValueError('Publishes must target at least one interest')

        for interest in interests:
            if not isinstance(interest, six.string_types):
                raise TypeError(
                    'Interest {} is not a string'.format(interest)
                )
            if len(interest) > INTEREST_MAX_LENGTH:
                raise ValueError(
                    'Interest "{}" is longer than the maximum of {} chars'.format(
                        interest,
                        INTEREST_MAX_LENGTH,
                    )
                )
            if '-' in interest:
                raise ValueError(
                    'Interest "{}" contains a "-" which is forbidden. '.format(
                        interest,
                    )
                    + 'have you considered using a "_" instead?'
                )
            if not INTEREST_REGEX.match(interest):
                raise ValueError(
                    'Interest "{}" contains a forbidden character. '.format(
                        interest,
                    )
                    + 'Allowed characters are: ASCII upper/lower-case letters, '
                    + 'numbers or one of _=@,.:'
                )

        publish_body['interests'] = interests
        session = requests.Session()
        request = requests.Request(
            'POST',
            'https://{}/publish_api/v1/instances/{}/publishes'.format(
                self.endpoint,
                self.instance_id,
            ),
            json=publish_body,
            headers={
                'host': self.endpoint,
                'authorization': 'Bearer {}'.format(self.secret_key),
                'x-pusher-library': 'pusher-push-notifications-python {}'.format(
                    SDK_VERSION,
                )
            },
        )

        response = session.send(request.prepare())
        try:
            response_body = response.json()
        except json.decoder.JSONDecodeError:
            response_body = {}

        if response.status_code != 200:
            handle_http_error(response_body, response.status_code)

        return response_body
