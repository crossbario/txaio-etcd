import six

from txaioetcd import Lease, KeySet, Error, Revision, Deleted, Range, Header
from txaioetcd._types import _increment_last_byte

ENDPOINT_STATUS = '{}/v3alpha/maintenance/status'
ENDPOINT_SET = '{}/v3alpha/kv/put'
ENDPOINT_GET = '{}/v3alpha/kv/range'
ENDPOINT_DELETE = '{}/v3alpha/kv/deleterange'
ENDPOINT_WATCH = '{}/v3alpha/watch'
ENDPOINT_SUBMIT = '{}/v3alpha/kv/txn'
ENDPOINT_LEASE = '{}/v3alpha/lease/grant'


def validate_client_set_parameters(key, value, lease=None, return_previous=None):
    if type(key) != six.binary_type:
        raise TypeError('key must be bytes, not {}'.format(type(key)))

    if type(value) != six.binary_type:
        raise TypeError('value must be bytes, not {}'.format(type(value)))

    if lease is not None and not isinstance(lease, Lease):
        raise TypeError('lease must be a Lease object, not {}'.format(type(lease)))

    if return_previous is not None and type(return_previous) != bool:
        raise TypeError('return_previous must be bool, not {}'.format(type(return_previous)))


def validate_client_get_parameters(key, range_end=None):
    if type(key) == six.binary_type:
        if range_end:
            key = KeySet(key, range_end=range_end)
        else:
            key = KeySet(key)
    elif isinstance(key, KeySet):
        pass
    else:
        raise TypeError('key must either be bytes or a KeySet object, not {}'.format(type(key)))

    if key.type == KeySet._SINGLE:
        range_end = None
    elif key.type == KeySet._PREFIX:
        range_end = _increment_last_byte(key.key)
    elif key.type == KeySet._RANGE:
        range_end = key.range_end
    else:
        raise Exception('logic error')

    return key, range_end


def validate_client_delete_parameters(key, return_previous=None):
    if type(key) == six.binary_type:
        key = KeySet(key)
    elif isinstance(key, KeySet):
        pass
    else:
        raise TypeError('key must either be bytes or a KeySet object, not {}'.format(type(key)))

    if return_previous is not None and type(return_previous) != bool:
        raise TypeError('return_previous must be bool, not {}'.format(type(return_previous)))

    if key.type == KeySet._SINGLE:
        range_end = None
    elif key.type == KeySet._PREFIX:
        range_end = _increment_last_byte(key.key)
    elif key.type == KeySet._RANGE:
        range_end = key.range_end
    else:
        raise Exception('logic error')

    return key, range_end


def validate_client_lease_parameters(time_to_live, lease_id=None):
    if lease_id is not None and type(lease_id) not in six.integer_types:
        raise TypeError('lease_id must be integer, not {}'.format(type(lease_id)))

    if type(time_to_live) not in six.integer_types:
        raise TypeError('time_to_live must be integer, not {}'.format(type(time_to_live)))

    if time_to_live < 1:
        raise TypeError('time_to_live must >= 1 second, was {}'.format(time_to_live))


def validate_client_submit_response(json):
    if u'error' in json:
        error = Error._parse(json)
        raise error

    if u'header' in json:
        header = Header._parse(json[u'header'])
    else:
        header = None

    responses = []
    for r in json.get(u'responses', []):
        if len(r.keys()) != 1:
            raise Exception(
                'bogus transaction response (multiple response tags in item): {}'.format(json))

        first = list(r.keys())[0]

        if first == u'response_put':
            re = Revision._parse(r[u'response_put'])
        elif first == u'response_delete_range':
            re = Deleted._parse(r[u'response_delete_range'])
        elif first == u'response_range':
            re = Range._parse(r[u'response_range'])
        else:
            raise Exception('response item "{}" bogus or not implemented'.format(first))

        responses.append(re)

    return header, responses
