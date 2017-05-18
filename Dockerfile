FROM python:3.5-alpine

WORKDIR /mimic/

COPY ./ /mimic

# Install ProxyBroker first. I'm using an old repo because the api changed
# and I haven't updated it yet. None of the repositories need gcc at
# runtime, but some of the ProxyBroker requirements need gcc for
# compilation. Compile, but remove in this one RUN layer to keep it light.
RUN apk add --update alpine-sdk && \
    pip3 install -r ProxyBroker/requirements.txt && \
    cd ProxyBroker && python setup.py install && \
    pip3 install -r requirements.txt && \
    cd /mimic && python setup.py install && \ 
    apk del alpine-sdk 

EXPOSE 8901

CMD ["python", "-m", "mimic.server", "--host", "0.0.0.0", "--port", "8901"]
