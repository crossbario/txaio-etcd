###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Crossbar.io Technologies GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

import argparse
import csv
import json
import os
import sys
import binascii

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks, returnValue

from txaioetcd import Client
from txaioetcd._version import __version__

ADDRESS_ETCD = u'http://localhost:2379'


@inlineCallbacks
def get_all_keys(reactor, key_type, value_type, etcd_address):
    """Returns all keys from etcd.

    :param reactor: reference to Twisted' reactor.
    :param etcd_address: Address with port number where etcd is
        running.
    :return: An instance of txaioetcd.Range containing all keys and
        their values.
    """
    etcd = Client(reactor, etcd_address)
    result = yield etcd.get(b'\x00', range_end=b'\x00')

    res = {}
    for item in result.kvs:
        if key_type == u'utf8':
            key = item.key.decode('utf8')
        elif key_type == u'binary':
            key = binascii.b2a_base64(item.key).decode().strip()
        else:
            raise Exception('logic error')

        if value_type == u'json':
            value = json.loads(item.value.decode('utf8'))
        elif value_type == u'binary':
            value = binascii.b2a_base64(item.value).decode().strip()
        elif value_type == u'utf8':
            value = item.value.decode('utf8')
        else:
            raise Exception('logic error')

        res[key] = value

    returnValue(res)


@inlineCallbacks
def export_as_json(reactor, key_type, value_type, output_path, etcd_address):
    res = yield get_all_keys(reactor, key_type, value_type, etcd_address)
    if output_path:
        with open(output_path, 'w') as file:
            json.dump(res, file, sort_keys=True, indent=4, ensure_ascii=False)
    else:
        json.dump(res, sys.stdout, sort_keys=True, indent=4, ensure_ascii=False)
        print('\n')


@inlineCallbacks
def export_as_csv(reactor, key_type, value_type, output_path, etcd_address):
    res = yield get_all_keys(reactor, key_type, value_type, etcd_address)
    file = open(output_path, 'w') if output_path else StringIO()
    writer = csv.writer(file)
    for k, v in res.items():
        if value_type == u'utf8':
            writer.writerow([k, v])
        else:
            writer.writerow([k, json.dumps(v, separators=(',', ':'), ensure_ascii=False)])

    if not output_path:
        print(file.getvalue())


def main():
    parser = argparse.ArgumentParser(description='Utility to dump etcd database to a file.')

    parser.add_argument('-a', '--address',
                        help='Address(with port number) of the etcd daemon (default: {})'.format(
                            ADDRESS_ETCD),
                        default=ADDRESS_ETCD)

    parser.add_argument('-k', '--key-type',
                        help='The key type in the etcd database (default: utf8).',
                        choices=['utf8', 'binary'],
                        default='utf8')

    parser.add_argument('-v', '--value-type',
                        help='The value type in the etcd database (default: json).',
                        choices=['json', 'binary', 'utf8'],
                        default='json')

    parser.add_argument('-f', '--output-format',
                        help='The output format for the database dump (default: json).',
                        choices=['json', 'csv'],
                        default='json')

    parser.add_argument('-o',
                        '--output-file',
                        default=None,
                        help='Path for the output file. When unset, output goes to stdout.')

    parser.add_argument('--version', action='version',
                        version='txaio-etcd version: {}'.format(__version__))

    args = parser.parse_args()

    output_file = args.output_file
    if output_file and output_file.startswith('~'):
        output_file = os.path.expanduser(output_file)

    react(export_as_csv if args.output_format == 'csv' else export_as_json,
          (args.key_type, args.value_type, output_file, args.address))


if __name__ == '__main__':
    main()
