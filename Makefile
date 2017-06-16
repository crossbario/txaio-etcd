.PHONY: test docs pep8

default: test

grep_pb_api:
	grep 'etcdserverpb.*"' docs/rpc.swagger.json | grep -v "ref" | grep -v "title" | uniq | sort | tr -d '"' | tr -d ": {"

test:
	python examples/connect.py
	python examples/crud.py
	python examples/transaction.py
	python examples/lease.py
	python examples/watch.py

install:
	pip install --upgrade -e .[dev]

pep8:
	pep8 test/*.py txaioetcd/*.py

# This will run pep8, pyflakes and can skip lines that end with # noqa
flake8:
	#flake8 --max-line-length=119 test/*.py txaioetcd/*.py
	flake8 --ignore=E501 test/*.py txaioetcd/*.py

# cleanup everything
clean:
	rm -rf ./txaioetcd.egg-info
	rm -rf ./build
	rm -rf ./dist
	rm -rf ./temp
	rm -rf ./_trial_temp
	rm -rf ./.tox
	rm -rf ./.eggs
	rm -rf ./.cache
	rm -rf ./test/.coverage.*.*
	rm -rf ./docs/_build
	rm -rf ./docs/_spelling
	rm -f ./basic.spec
	-find . -name "*.tar.gz" -type f -exec rm -f {} \;
	-find . -name "*.egg" -type f -exec rm -f {} \;
	-find . -name "*.pyc" -type f -exec rm -f {} \;
	-find . -name "*__pycache__" -type d -exec rm -rf {} \;
	docker rmi crossbario/txaioetcd

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
