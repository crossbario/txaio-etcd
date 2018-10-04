etcd
----

Installation
............

To build and install etcd 3.1

.. code-block:: sh

    ETCD_VER=v3.1.0
    DOWNLOAD_URL=https://github.com/coreos/etcd/releases/download
    curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz \
        -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
    sudo mkdir -p /opt/etcd && sudo tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz \
        -C /opt/etcd --strip-components=1

To verify the installation, check the version

.. code-block:: sh

    /opt/etcd/etcd --version

Open a console and start etcd

.. code-block:: sh

    /opt/etcd/etcd

To scratch the etcd database

.. code-block:: sh

    rm -rf ~/default.etcd/


Test using etcdctl
..................

Get cluster status

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl endpoint -w table status

Set a key

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl put foo hello

Get a key

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl get foo

Watch a key

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl watch foo


Test using curl
...............


Get cluster status

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/maintenance/status -X POST -d '{}'

Set a key (value "hello" on key "foo" both base64 encoded):

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/kv/put -X POST -d '{"key": "Zm9v", "value": "YmFy"}'

Get a key ("foo" base64 encoded)

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/kv/range -X POST -d '{"key": "Zm9v"}'

Watch a key ("foo" base64 encoded)

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/watch -X POST -d '{"create_request": {"key": "Zm9v"}}'
