#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Automatic Docker Image Deployment via Docker Hub Webhooks."""

import json
import os
import sys
import logging
import requests
import tornado.ioloop
import tornado.web
import docker

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.DEBUG,
                    stream=sys.stdout)
DOCKER = docker.Client(base_url='unix://var/run/docker.sock')
DOCKER_REPO = os.environ.get('DOCKER_REPO', 'foo:latest')


def _docker_callback(url, payload):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    requests.post(url, data=json.dumps(payload), headers=headers)


class MyHandler(tornado.web.RequestHandler):

    def post(self):
        env = dict(os.environ)
        logging.debug("payload = %s" % self.request.body)
        data = json.loads(self.request.body.decode('utf8'))
        if set(('callback_url', 'repository')) <= set(data.keys()):
            self.send_error(
                400, message='Request does not have required components')

        containers = DOCKER.containers(filters={'ancestor': DOCKER_REPO})
        for container in containers:
            DOCKER.stop(container['Id'], timeout=0)
            DOCKER.remove_container(container['Id'], force=True)

        image, tag = DOCKER_REPO.split(':')
        DOCKER.pull(image, tag=tag)

        nginx = DOCKER.containers(filters={'ancestor': 'nginx'})
        network = list(nginx['NetworkSettings']['Networks'].keys())[0]

        env = {
            'VIRTUAL_HOST': os.environ.get('TARGET_HOST'),
            'LETSENCRYPT_HOST': os.environ.get('TARGET_HOST'),
            'VIRTUAL_NETWORK': network,
            'LETSENCRYPT_EMAIL': os.environ.get('ADMIN_EMAIL')
        }
        networking_config = DOCKER.create_networking_config(
            {network: DOCKER.create_endpoint_config()}
        )
        cid = DOCKER.create_container(
            DOCKER_REPO, detach=True, environment=env,
            networking_config=networking_config)
        DOCKER.start(cid)

        self.finish()


if __name__ == '__main__':
    app = tornado.web.Application([
        (r'/', MyHandler)
    ])
    logging.getLogger().setLevel(logging.DEBUG)
    app.listen(80)
    tornado.ioloop.IOLoop.instance().start()
