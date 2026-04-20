FROM node:lts-alpine

RUN apk add --no-cache python3 py3-pip tini su-exec \
    && mkdir -p /home/node/.n8n \
    && chown -R node:node /home/node/.n8n

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

RUN npm install -g n8n@latest \
    && npm cache clean --force

USER node
WORKDIR /home/node

EXPOSE 5678
ENTRYPOINT ["tini", "--", "n8n"]
