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

from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks

from txaioetcd import Client

ADDRESS_ETCD = u'http://localhost:2379'


def _get_all_keys(reactor, etcd_address):
    """Returns all keys from etcd.

    :param reactor: reference to Twisted' reactor.
    :param etcd_address: Address with port number where etcd is
        running.
    :return: An instance of txaioetcd.Range containing all keys and
        their values.
    """
    etcd = Client(reactor, etcd_address)
    return etcd.get(b'\x00', range_end=b'\x00')


@inlineCallbacks
def export_as_json(reactor, output_path, etcd_address):
    result = yield _get_all_keys(reactor, etcd_address)
    res = {item.key.decode(): item.value.decode() for item in result.kvs}
    with open(output_path, 'w') as file:
        json.dump(res, file, sort_keys=True, indent=4)


@inlineCallbacks
def export_as_csv(reactor, output_path, etcd_address):
    result = yield _get_all_keys(reactor, etcd_address)
    res = {item.key.decode(): item.value.decode() for item in result.kvs}
    with open(output_path, 'w') as file:
        writer = csv.writer(file)
        writer.writerow(['keys', 'values'])
        for k, v in res.items():
            writer.writerow([k, v])


def main():
    parser = argparse.ArgumentParser(description='Utility to dump etcd database to a file.')
    parser.add_argument('-a', '--address', help='Address(with port number) of the etcd daemon.',
                        default=ADDRESS_ETCD)
    parser.add_argument('-f', '--output-format', help='The output format for the database dump.',
                        default='json')
    parser.add_argument('-o', '--output-file', help='Path for the output file.')
    args = parser.parse_args()

    output_format = args.output_format.lower()
    if output_format not in ['json', 'csv']:
        print("Error: output format must either be json or csv.")
        exit(1)

    output_file = args.output_file if args.output_file else 'etc-dump.{}'.format(output_format)
    if output_file.startswith('~'):
        output_file = os.path.expanduser(output_file)

    react(export_as_csv if output_format == 'csv' else export_as_json, (output_file, args.address))


if __name__ == '__main__':
    main()
