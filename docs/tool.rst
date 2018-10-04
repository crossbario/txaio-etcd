Command line tools
==================

The `txaio-etcd` package contains two command line tools:

* `etcd-exporter`
* `etcd-importer`

These can be used to export and import data from and to etcd.

The tools support various options for key/value types and input/output format, eg the exporter:

.. code-block:: console

    (cpy362_1) oberstet@thinkpad-t430s:~$ etcd-export --help
    usage: etcd-export [-h] [-a ADDRESS] [-k {utf8,binary}]
                       [-v {json,binary,utf8}] [-f {json,csv}] [-o OUTPUT_FILE]

    Utility to dump etcd database to a file.

    optional arguments:
      -h, --help            show this help message and exit
      -a ADDRESS, --address ADDRESS
                            Address(with port number) of the etcd daemon (default:
                            http://localhost:2379)
      -k {utf8,binary}, --key-type {utf8,binary}
                            The key type in the etcd database (default: utf8).
      -v {json,binary,utf8}, --value-type {json,binary,utf8}
                            The value type in the etcd database (default: json).
      -f {json,csv}, --output-format {json,csv}
                            The output format for the database dump (default:
                            json).
      -o OUTPUT_FILE, --output-file OUTPUT_FILE
                            Path for the output file. When unset, output goes to
                            stdout.

and the importer:

.. code-block:: console

    (cpy362_1) oberstet@thinkpad-t430s:~$ etcd-import --help
    usage: etcd-import [-h] [-a ADDRESS] [-k {utf8,binary}]
                       [-v {json,binary,utf8}] [-f {json,csv}] [-d]
                       [-o DRY_OUTPUT] [--verbosity {silent,compact,verbose}]
                       input_file

    Utility to import external file to etcd database.

    positional arguments:
      input_file            Path for the input file.

    optional arguments:
      -h, --help            show this help message and exit
      -a ADDRESS, --address ADDRESS
                            Address(with port number) of the etcd daemon (default:
                            http://localhost:2379)
      -k {utf8,binary}, --key-type {utf8,binary}
                            The key type in the etcd database (default: utf8).
      -v {json,binary,utf8}, --value-type {json,binary,utf8}
                            The value type in the etcd database (default: json).
      -f {json,csv}, --input-format {json,csv}
                            The input format for the database file (default:
                            json).
      -d, --dry-run         Print the potential changes to import.
      -o DRY_OUTPUT, --dry-output DRY_OUTPUT
                            The file to put the result of dry run (default:
                            stdout).
      --verbosity {silent,compact,verbose}
                            Set the verbosity level.
