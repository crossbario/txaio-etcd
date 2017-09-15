import base64

import six

from txaioetcd import Lease, KeySet, Error, Revision, Deleted, Range, Header
from txaioetcd._types import _increment_last_byte

ENDPOINT_STATUS = '{}/v3alpha/maintenance/status'
ENDPOINT_PUT = '{}/v3alpha/kv/put'
ENDPOINT_GET = '{}/v3alpha/kv/range'
ENDPOINT_DELETE = '{}/v3alpha/kv/deleterange'
ENDPOINT_WATCH = '{}/v3alpha/watch'
ENDPOINT_SUBMIT = '{}/v3alpha/kv/txn'
ENDPOINT_LEASE = '{}/v3alpha/lease/grant'


class StatusRequestAssembler:
    def __init__(self, root_url):
        self.root_url = root_url

    @property
    def url(self):
        return ENDPOINT_STATUS.format(self.root_url).encode()

    @property
    def data(self):
        return {}


class T:
    def __init__(self, root_url):
        self._data = None
        self._url = ENDPOINT_GET.format(root_url).encode()
        self.__validate()
        self.__assemble()

    @property
    def url(self):
        return self._url

    @property
    def data(self):
        return self._data

    def __assemble(self):
        pass

    def __validate(self):
        pass


class PutRequestAssembler:
    def __init__(self, root_url, key, value, lease=None, return_previous=None):
        self._key = key
        self._value = value
        self._lease = lease
        self._return_previous = return_previous
        self._data = None
        self._url = ENDPOINT_PUT.format(root_url).encode()
        self.__validate()
        self.__assemble()

    @property
    def url(self):
        return self._url

    @property
    def data(self):
        return self._data

    def __assemble(self):
        self._data = {
            u'key': base64.b64encode(self._key).decode(),
            u'value': base64.b64encode(self._value).decode()
        }
        if self._return_previous:
            self._data[u'prev_kv'] = True
        if self._lease and self._lease.lease_id:
            self._data[u'lease'] = self._lease.lease_id

    def __validate(self):
        if type(self._key) != six.binary_type:
            raise TypeError('key must be bytes, not {}'.format(type(self._key)))

        if type(self._value) != six.binary_type:
            raise TypeError('value must be bytes, not {}'.format(type(self._value)))

        if self._lease is not None and not isinstance(self._lease, Lease):
            raise TypeError('lease must be a Lease object, not {}'.format(type(self._lease)))

        if self._return_previous is not None and type(self._return_previous) != bool:
            raise TypeError('return_previous must be bool, not {}'.format(
                type(self._return_previous)))


class GetRequestAssembler:
    def __init__(self, root_url, key, range_end=None):
        self._key = key
        self._range_end = range_end
        self._data = None
        self._url = ENDPOINT_GET.format(root_url).encode()
        self.__validate()
        self.__assemble()

    @property
    def url(self):
        return self._url

    @property
    def data(self):
        return self._data

    def __assemble(self):
        self._data = {
            u'key': base64.b64encode(self._key.key).decode()
        }
        if self._range_end:
            self._data[u'range_end'] = base64.b64encode(self._range_end).decode()

    def __validate(self):
        if type(self._key) == six.binary_type:
            if self._range_end:
                self._key = KeySet(self._key, range_end=self._range_end)
            else:
                self._key = KeySet(self._key)
        elif isinstance(self._key, KeySet):
            pass
        else:
            raise TypeError(
                'key must either be bytes or a KeySet object, not {}'.format(type(self._key)))

        if self._key.type == KeySet._SINGLE:
            self._range_end = None
        elif self._key.type == KeySet._PREFIX:
            self._range_end = _increment_last_byte(self._key.key)
        elif self._key.type == KeySet._RANGE:
            self._range_end = self._key.range_end
        else:
            raise Exception('logic error')


class DeleteRequestAssembler:
    def __init__(self, root_url, key, return_previous=None):
        self._key = key
        self._return_previous = return_previous
        self._data = None
        self._url = ENDPOINT_DELETE.format(root_url).encode()
        self.__validate()
        self.__assemble()

    @property
    def url(self):
        return self._url

    @property
    def data(self):
        return self._data

    def __assemble(self):
        self._data = {
            u'key': base64.b64encode(self._key.key).decode(),
        }
        if self._range_end:
            # range_end is the key following the last key to delete
            # for the range [key, range_end).
            # If range_end is not given, the range is defined to contain only
            # the key argument.
            # If range_end is one bit larger than the given key, then the range
            # is all keys with the prefix (the given key).
            # If range_end is '\\0', the range is all keys greater
            # than or equal to the key argument.
            #
            self._data[u'range_end'] = base64.b64encode(self._range_end).decode()

        if self._return_previous:
            # If prev_kv is set, etcd gets the previous key-value pairs
            # before deleting it.
            # The previous key-value pairs will be returned in the
            # delete response.
            #
            self._data[u'prev_kv'] = True

    def __validate(self):
        if type(self._key) == six.binary_type:
            self._key = KeySet(self._key)
        elif isinstance(self._key, KeySet):
            pass
        else:
            raise TypeError(
                'key must either be bytes or a KeySet object, not {}'.format(type(key)))

        if self._return_previous is not None and type(self._return_previous) != bool:
            raise TypeError('return_previous must be bool, not {}'.format(
                type(self._return_previous)))

        if self._key.type == KeySet._SINGLE:
            self._range_end = None
        elif self._key.type == KeySet._PREFIX:
            self._range_end = _increment_last_byte(self._key.key)
        elif self._key.type == KeySet._RANGE:
            self._range_end = self._key.range_end
        else:
            raise Exception('logic error')


class LeaseRequestAssembler:
    def __init__(self, root_url, time_to_live, lease_id=None):
        self._time_to_live = time_to_live
        self._lease_id = lease_id
        self._data = None
        self._url = ENDPOINT_LEASE.format(root_url).encode()
        self.__validate()
        self.__assemble()

    @property
    def url(self):
        return self._url

    @property
    def data(self):
        return self._data

    def __assemble(self):
        self._data = {
            u'TTL': self._time_to_live,
            u'ID': self._lease_id or 0,
        }

    def __validate(self):
        if self._lease_id is not None and type(self._lease_id) not in six.integer_types:
            raise TypeError('lease_id must be integer, not {}'.format(type(self._lease_id)))

        if type(self._time_to_live) not in six.integer_types:
            raise TypeError('time_to_live must be integer, not {}'.format(
                type(self._time_to_live)))

        if self._time_to_live < 1:
            raise TypeError('time_to_live must >= 1 second, was {}'.format(self._time_to_live))


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
