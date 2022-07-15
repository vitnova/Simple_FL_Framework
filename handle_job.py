from tensorflow import keras
from tensorflow.keras.models import model_from_json
from tensorflow.keras.layers import Reshape, Dense, Conv2D, Flatten, MaxPooling2D
from tensorflow.keras.optimizers import RMSprop
from tensorflow.keras.utils import to_categorical
import pandas
import numpy as np
import server_socket
import config
import random
import os
import json
from update_weight import update_weight
from concurrent.futures import ThreadPoolExecutor
import traceback
import encrypt
import threading

executor = ThreadPoolExecutor(2)

mutexs = {}

def get_mutex(job_id):
	if not job_id in mutexs:
		mutexs[job_id] = threading.Lock()
	return mutexs[job_id]

# 获取job目录
def get_job_dic(job_id):
	return os.path.join("jobs/", job_id)

# 获取job配置信息
def get_job(job_id):
	with open(get_job_dic(job_id) + "/conf.json", "r") as f:
		return json.load(f)

# 向客户端分发job
def dispatch_job(availableClients, path, props):
	try:
		(public_key, private_key) = encrypt.key_gen(path)
		props['key'] = public_key
		for client in availableClients:
			server_socket.dispatch_job(client, props)
	except Exception as e:
		errorFile = open(path + '/server_error.log', 'a')
		errorFile.write(traceback.format_exc())
		errorFile.close()		

# 处理用户提交的job
def submit_job(model_json, train_data, test_data, props):
	num = props['client_num']
	availableNum = 0
	availableClients = []

	clients_list = config.get()['clients']
	# 随机顺序
	random.shuffle(clients_list)
	for client in clients_list:
		if availableNum >= num:
			break;
		elif server_socket.test(client):
			availableNum += 1
			availableClients.append(client)

	if availableNum < num:
		return {
			'code': 503,
			'msg': 'Clients are busy now'
		}

	job_id = server_socket.gen()
	path = os.path.join("jobs/", job_id)
	os.makedirs(path)
	os.makedirs(path + '/args')
    
	props['job_id'] = job_id
	props['status'] = 0
	props['fit_count'] = 0
	props['now_accepted_count'] = 0
	props['clients'] = availableClients

	train_nums = []
	last_num = props['train_num']
	step = int(last_num / availableNum)

	for i in range(0, availableNum):
		if availableNum == i:
			train_nums.push(last_num)
		else:
			train_nums.append(step)
			last_num -= step

	props['client_train_nums'] = train_nums

	with open(path + '/conf.json', 'w') as f:
		json.dump(props, f)

	executor.submit(dispatch_job, availableClients, path, props)

	return {
		'code': 200,
		'msg': 'success',
		'data': {
			'id': job_id
		}
	}

def model_compile(model, props):
	model.compile(optimizer=props['optimizer'], loss=props['loss'], metrics=props['metrics'])

def get_test_set(props):
	train_data = pandas.read_csv("data/" + props['test_data'])
	return (train_data.iloc[:,2:], to_categorical(train_data.iloc[:,1]))

# 处理当前epoch结束
def handle_epochs_finish(job_id, job_path, client_id, weights, data):
	try:
		client_weights = []
		for i, client in enumerate(data['clients']):
			if client == client_id:
				client_weights.append(weights)
			else:
				with open(job_path + "/args/" + str(i) + ".json", "r") as f:
					client_weights.append(json.load(f))

		weight_path = job_path + "/args/sum.json"
		if os.path.exists(weight_path):
			with open(weight_path, "r") as f:
				old_weights = json.load(f)
		else:
			old_weights = weights

		new_weights = update_weight(old_weights, data['train_num'], data['client_train_nums'], client_weights)
		with open(job_path + '/args/sum.json', 'w') as f:
			json.dump(new_weights, f)
		
		data['now_accepted_count'] = 0
		data['fit_count'] += 1
		if data['fit_count'] >= data['epochs']:
			data['status'] = 1

			new_weights = np.array(weights)
			for i, sequence in enumerate(new_weights):
				new_weights[i] = np.array(new_weights[i])
				for j, weight in enumerate(sequence):
					new_weights[i][j] = np.array(new_weights[i][j])
					if isinstance(weight, list):
						for z, weightz in enumerate(weight):
							new_weights[i][j][z] = np.array(new_weights[i][j][z])

			model = model_from_json(json.dumps(data['model']))
			model.set_weights(new_weights)
			model_compile(model, data)
			model.save(job_path + "/final_model.h5")

			(test_set, test_label) = get_test_set(data)
			test_loss, test_accuracy = model.evaluate(test_set, test_label)
			test_loss = np.float(test_loss)
			test_accuracy = np.float(test_accuracy)

			with open(job_path + '/evaluation.json', 'w') as f:
				json.dump({
					"test_loss": test_loss,
					"test_accuracy": test_accuracy
				}, f)
			print('test_loss:', test_loss, ',test_accuracy:', test_accuracy)
		else:
			for client in data['clients']:
				server_socket.continue_next_job(client, job_id, encrypt.encrypt_with_private_key(new_weights, job_path))

		with open(job_path + '/conf.json', 'w') as f:
			json.dump(data, f)

	except Exception as e:
		errorFile = open(job_path + '/server_error.log', 'a')
		errorFile.write(traceback.format_exc())
		errorFile.close()

# 接收客户端训练后的最新权值
def receive_weights_from_client(job_id, client_id, weights):
	mutex = get_mutex(job_id)
	mutex.acquire(10)

	data = get_job(job_id)
	data['now_accepted_count'] += 1
	job_path = get_job_dic(job_id)

	weights = json.loads(encrypt.decrypt_with_private_key(weights, job_path))

	# 若本轮训练均已完成，则更新权重并进行通知客户机进行下一轮训练
	# 否则等待
	if data['now_accepted_count'] >= data['client_num']:
		executor.submit(handle_epochs_finish, job_id, job_path, client_id, weights, data)
	else:
		data['now_accepted_count'] += 1

	client_store_name = 0
	for i, client in enumerate(data['clients']):
		if client == client_id:
			client_store_name = str(i)
			break

	with open(job_path + '/args/' + client_store_name + '.json', 'w') as f:
		json.dump(weights, f)

	with open(job_path + '/conf.json', 'w') as f:
		json.dump(data, f)

	mutex.release()

	return {
		'code': 200,
		'msg': 'success'
	}

# 获取job配置
def pull_job_status(job_id):
	return get_job(job_id)