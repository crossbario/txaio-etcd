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
import base64
import csv
import json
import os
import sys

from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks, returnValue

from txaioetcd import Client, Transaction, OpSet, OpDel
from txaioetcd.cli.exporter import get_all_keys, ADDRESS_ETCD

TYPE_CSV = 'csv'
TYPE_JSON = 'json'


@inlineCallbacks
def csv_to_dict(csv_file, value_type):
    with open(csv_file) as file:
        if value_type == u'utf8':
            result = yield {row[0]: row[1] for row in csv.reader(file)}
        else:
            result = yield {row[0]: json.loads(row[1]) for row in csv.reader(file)}
    returnValue(result)


@inlineCallbacks
def json_to_dict(json_file):
    with open(json_file) as file:
        result = yield json.loads(file.read().strip())
    returnValue(result)


@inlineCallbacks
def get_input_content(input_format, input_file, value_type):
    if input_format == TYPE_CSV:
        input_content = yield csv_to_dict(input_file, value_type)
    elif input_format == TYPE_JSON:
        input_content = yield json_to_dict(input_file)
    else:
        raise ValueError('Only csv and json input is supported.')
    returnValue(input_content)


def get_db_diff(old_database, to_import_database, key_type, value_type):
    diff = {}
    to_update = {}
    to_delete = {}

    for k, v in to_import_database.items():

        if key_type == u'binary':
            k = base64.b64decode(k)

        if value_type == u'binary':
            v = base64.b64decode(v)

        if old_database.get(k, None) != v:
            if not isinstance(k, bytes):
                k = k.encode()
            if not isinstance(v, bytes):
                v = v.encode()
            to_update.update({k: v})

    diff.update({'to_update': to_update, 'to_delete': to_delete})
    return diff


@inlineCallbacks
def import_to_db(reactor, key_type, value_type, input_format, input_file, etcd_address, dry_run,
                 dry_output, verbosity):
    db_current = yield get_all_keys(reactor, key_type, value_type, etcd_address)
    db_import = yield get_input_content(input_format, input_file, value_type)
    db_diff = yield get_db_diff(db_current, db_import, key_type, value_type)

    transaction = []

    if dry_run:
        if dry_output:
            with open(dry_output, 'w') as file:
                json.dump(db_diff, file, sort_keys=True, indent=4, ensure_ascii=False)
        else:
            json.dump(db_diff, sys.stdout, sort_keys=True, indent=4, ensure_ascii=False)
            print('\n')
    else:
        for k, v in db_diff['to_update'].items():
            transaction.append(OpSet(k, v))

        for key in db_diff['to_delete'].keys():
            transaction.append(OpDel(key))

        etcd = Client(reactor, etcd_address)
        yield etcd.submit(Transaction(success=transaction))
        if verbosity == 'verbose':
            json.dump(db_diff, sys.stdout, sort_keys=True, indent=4, ensure_ascii=False)
            print('\n')
        elif verbosity == 'compact':
            print('{} updated.'.format(len(db_diff['to_update'])))
            print('{} deleted.'.format(len(db_diff['to_delete'])))


def main():
    parser = argparse.ArgumentParser(
        description='Utility to import external file to etcd database.')

    parser.add_argument('input_file', help='Path for the input file.')

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

    parser.add_argument('-f', '--input-format',
                        help='The input format for the database file (default: json).',
                        choices=['json', 'csv'],
                        default='json')

    parser.add_argument('-d', '--dry-run', action='store_true', default=False,
                        help='Print the potential changes to import.')

    parser.add_argument('-o', '--dry-output',
                        help='The file to put the result of dry run (default: stdout).')

    parser.add_argument('--verbosity', default='silent', choices=['silent', 'compact', 'verbose'],
                        help='Set the verbosity level.')

    args = parser.parse_args()

    input_file = os.path.expanduser(args.input_file)
    if not os.path.exists(input_file):
        print('Error: Input file {} does not exist.'.format(input_file))
        exit(1)

    react(
        import_to_db,
        (args.key_type, args.value_type, args.input_format, input_file, args.address, args.dry_run,
         args.dry_output, args.verbosity)
    )


if __name__ == '__main__':
    main()
