from flask import Flask, request
import time
import os
import random
import handle_job
import requests
import config
import json

app = Flask(__name__)

def gen():
	return time.strftime("%Y_%m_%d_%H_%M_%S_") + str(random.randint(1, 1000))

@app.route('/')
def index():
	return {
		'code': 200,
		'msg': 'welcome'
	}

@app.route('/job', methods=["POST"])
def submit_job():
	print("接收到任务请求")
	form = json.loads(request.data)
	return handle_job.submit_job(form['model'], form['train_data'], form['test_data'], form)

@app.route('/job/<job_id>', methods=["GET"])
def get_submit_job(job_id):
	return handle_job.pull_job_status(job_id)

@app.route('/job/<job_id>/<client_id>', methods=["POST"])
def update_job(job_id, client_id):
	print("接收到", client_id, "的任务[", job_id, "]最新的权值数据")
	return handle_job.receive_weights_from_client(job_id, client_id, json.loads(request.data)['weights'])

def test(addr):
	try:
		r = requests.get("http://" + addr + "/status")
		if r.json()['msg'] == 'available':
			return True
	except Exception as e:
		return False

def dispatch_job(addr, data):
	try:
		r = requests.post("http://" + addr + "/job/create", json=data)
		if r.json()['code'] == 200:
			return True
	except Exception as e:
		print(e)
		return False

def continue_next_job(addr, job_id, weights):
	try:
		r = requests.post("http://" + addr + "/job/" + job_id + "/continue", json={'weights': weights})
		if r.json()['code'] == 200:
			return True
	except Exception as e:
		return False

if __name__ == '__main__':
	config_map = config.get()
	app.run('0.0.0.0', port=config_map['server_port'], debug=config_map['debug'])