FROM python:3

RUN pip install twisted txaioetcd

VOLUME /examples

CMD ["/bin/bash", "/examples/run.sh"]
