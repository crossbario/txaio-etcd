.PHONY: test docs pep8 examples

default: test

grep_pb_api:
	grep 'etcdserverpb.*"' docs/rpc.swagger.json | grep -v "ref" | grep -v "title" | uniq | sort | tr -d '"' | tr -d ": {"

install:
	pip install --upgrade -e .[dev]

test:
	python examples/connect.py
	python examples/crud.py
	python examples/transaction.py
	python examples/lease.py
	python examples/watch.py

test_py37:
	tox -e py37

test_syntax:
	tox -e flake8,mypy,yapf

test_docs:
	tox -e sphinx

build_sql:
	psql -h localhost postgres postgres -f txaioetcd/pgetcd.sql

examples:
	cd examples && sh run.sh

examples_etcdb:
	cd examples/etcdb && sh run.sh

clean:
	-docker rmi crossbario/txaioetcd
	-rm -rf .mypy_cache
	-rm -rf .pytest_cache
	-rm -rf ./txaioetcd.egg-info
	-rm -rf ./build
	-rm -rf ./dist
	-rm -rf ./temp
	-rm -rf ./_trial_temp
	-rm -rf ./.tox
	-rm -rf ./.eggs
	-rm -rf ./.cache
	-rm -rf ./test/.coverage.*.*
	-rm -rf ./docs/_build
	-rm -rf ./docs/_spelling
	-rm -f ./basic.spec
	-find . -name "*.tar.gz" -type f -exec rm -f {} \;
	-find . -name "*.egg" -type f -exec rm -f {} \;
	-find . -name "*.pyc" -type f -exec rm -f {} \;
	-find . -name "*__pycache__" -type d -exec rm -rf {} \;

# auto-format code - WARNING: this my change files, in-place!
autoformat:
	yapf -ri --style=yapf.ini txaioetcd

# publish to PyPI
publish: clean
	python setup.py sdist bdist_wheel
	twine upload dist/*

# start a single-node etcd cluster in a Docker container
docker_etcd:
	docker run \
		--rm \
		--net=host \
		-p 2379:2379 \
		-p 2380:2380 \
		-v /usr/share/ca-certificates/:/etc/ssl/certs \
		-v ${PWD}/.etcd:/etcd-data \
		--name cf-etcd \
		quay.io/coreos/etcd:latest \
			/usr/local/bin/etcd \
			--data-dir=/etcd-data \
			--name cf-etcd \
			--advertise-client-urls http://0.0.0.0:2379 \
			--listen-client-urls http://0.0.0.0:2379

# build an example image
docker_build:
	docker build -f docker/Dockerfile -t crossbario/txaioetcd docker/

# test the example image
docker_test:
	docker run -it --rm --net=host -v ${PWD}/examples:/examples crossbario/txaioetcd
