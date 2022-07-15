from flask import Flask, request
import time
import os
import random
import client_job
import requests
import config
import json

app = Flask(__name__)

@app.route('/')
def index():
	return {
		'code': 200,
		'msg': 'welcome'
	}

@app.route('/status', methods=["GET"])
def test():
	return {
		'code': 200,
		'msg': 'available'
	}

@app.route('/job/create', methods=["POST"])
def receive_job():
	return client_job.handle_job(json.loads(request.data))

@app.route('/job/<job_id>/continue', methods=["POST"])
def continue_next_job(job_id):
	return client_job.update_job(job_id, json.loads(request.data)['weights'])

def notify_job(job_id, weights):
	try:
		config_map = config.get()
		r = requests.post("http://" + config_map['target_server'] + "/job/" + job_id + "/" + config_map['self_client'], json={
				'weights': weights
			})
		print(r.text)
		if r.json()['code'] == 200:
			return True
	except Exception as e:
		print(e)
		return False

if __name__ == '__main__':
	config_map = config.get()
	app.run('0.0.0.0', port=config_map['client_port'], debug=config_map['debug'])