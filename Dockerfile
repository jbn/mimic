FROM python:3.5-onbuild

WORKDIR /mimic_server/

COPY ./ /mimic_server

RUN python setup.py install

EXPOSE 8901

CMD ["python", "-m", "mimic.server", "--host", "0.0.0.0", "--port", "8901"]
