#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Automatic Docker Image Deployment via Docker Hub Webhooks."""

import json
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


def _docker_callback(url, payload):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    requests.post(url, data=json.dumps(payload), headers=headers)


class MyHandler(tornado.web.RequestHandler):

    def post(self):
        logging.debug("payload = %s" % self.request.body)
        try:
            data = json.loads(self.request.body.decode('utf8'))
        except ValueError:
            message = 'Request body is not a valid JSON'
            logging.debug(message)
            raise tornado.web.HTTPError(400, message=message)

        image = data['repository']['repo_name']
        tag = data['push_data']['tag']
        fn_image = '{}:{}'.format(image, tag)
        # TODO check if allowed

        # get containers running current version of the image
        containers = DOCKER.containers(filters={'ancestor': fn_image})

        for container in containers:
            cid = container['Id']
            # pull new version of the image
            DOCKER.pull(image, tag=tag)

            info = DOCKER.inspect_container(cid)
            env = dict([tuple(_.split('=')) for _ in info['Config']['Env']])

            # create a new container using fresh image
            network = list(container['NetworkSettings']['Networks'].keys())[0]
            networking_config = DOCKER.create_networking_config(
                {network: DOCKER.create_endpoint_config()}
            )

            # stop and remove previous instance if present
            DOCKER.stop(cid, timeout=0)
            DOCKER.remove_container(cid, force=True)
            cid = DOCKER.create_container(
                fn_image, detach=True, environment=env,
                networking_config=networking_config)
            # start the new container
            DOCKER.start(cid)

if __name__ == '__main__':
    app = tornado.web.Application([
        (r'/', MyHandler)
    ])
    logging.getLogger().setLevel(logging.DEBUG)
    app.listen(80)
    tornado.ioloop.IOLoop.instance().start()
