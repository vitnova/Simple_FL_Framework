from tensorflow import keras
from tensorflow.keras.models import model_from_json, load_model
from tensorflow.keras.layers import Reshape, Dense, Conv2D, Flatten, MaxPooling2D
from tensorflow.keras.optimizers import RMSprop
from tensorflow.keras.utils import to_categorical
import pandas
import numpy as np
import config
import random
import os
import json
from update_weight import update_weight
import client_socket
from concurrent.futures import ThreadPoolExecutor
import traceback
import encrypt

executor = ThreadPoolExecutor(2)

def get_job_dic(job_id):
	return os.path.join("jobs/", job_id)

def get_job(job_id):
	with open(get_job_dic(job_id) + "/client_conf.json", "r") as f:
		return json.load(f)

def model_compile(model, props):
	model.compile(optimizer=RMSprop(lr=0.001), loss=props['loss'], metrics=props['metrics'])

def fit(model, train_data, train_label, batch_size):
	model.fit(train_data, train_label, epochs=1, batch_size=batch_size, verbose=2)

def get_dataset(props):
	train_data = pandas.read_csv("data/" + props['train_data'])
	return (train_data.iloc[:,2:], to_categorical(train_data.iloc[:,1]))

# 处理接收到的job
def async_handle_job(job_id, path, props):
	try:
		model = model_from_json(json.dumps(props['model']))
		(train_set, train_label) = get_dataset(props)
		model_compile(model, props)
		fit(model, train_set, train_label, props['batch_size'])
		model.save(path + "/model.h5")
		weights_list = model.get_weights()

		for i, sequence in enumerate(weights_list):
			weights_list[i] = weights_list[i].tolist()

		client_socket.notify_job(job_id, encrypt.encrypt_with_public_key(json.dumps(weights_list), path))
	except Exception as e:
		errorFile = open(path + '/client_error.log', 'a')
		errorFile.write(traceback.format_exc())
		errorFile.close()

# 响应接收到的job
def handle_job(props):
	job_id = props['job_id']
	path = get_job_dic(job_id)
	if not os.path.exists(path):
		os.makedirs(path)
	
	with open(path + "/public.pem", "w") as f:
		f.write(props['key'])
	props.pop('key')

	with open(path + '/client_conf.json', 'w') as f:
		json.dump(props, f)

	executor.submit(async_handle_job, job_id, path, props)

	return {
		'code': 200,
		'msg': 'success'
	}

# 处理新一轮epoch
def handle_update_job(job_id, weights):
	try:
		data = get_job(job_id)
		path = get_job_dic(job_id)
		model_path = path + "/model.h5"
		if isinstance(weights, str):
			weights = json.loads(encrypt.decrypt_with_public_key(weights, path))

		(train_set, train_label) = get_dataset(data)
		model = load_model(model_path)

		new_weights = np.array(weights)
		for i, sequence in enumerate(new_weights):
			new_weights[i] = np.array(new_weights[i])
			for j, weight in enumerate(sequence):
				new_weights[i][j] = np.array(new_weights[i][j])
				if isinstance(weight, list):
					for z, weightz in enumerate(weight):
						new_weights[i][j][z] = np.array(new_weights[i][j][z])

		model.set_weights(new_weights)
		fit(model, train_set, train_label, data['batch_size'])
		model.save(path + "/model.h5")

		weights_list = model.get_weights()

		for i, sequence in enumerate(weights_list):
			weights_list[i] = weights_list[i].tolist()

		client_socket.notify_job(job_id, encrypt.encrypt_with_public_key(json.dumps(weights_list), path))
	except Exception as e:
		errorFile = open(path + '/client_error.log', 'a')
		errorFile.write(traceback.format_exc())
		errorFile.close()

# 响应新一轮epoch
def update_job(job_id, weights):
	executor.submit(handle_update_job, job_id, weights)
	return {
		'code': 200,
		'msg': 'success'
	}

if __name__ == '__main__':
	job_id = '2022_07_12_23_27_17_753'
	path = get_job_dic(job_id)
	#dic_weights = load_model(path + "/model.h5").get_weights()
	#for i in range(0, len(dic_weights)):
	#	dic_weights[i] = dic_weights[i].tolist()

	#with open(path + '/weight', 'w') as f:
	#	json.dump(dic_weights, f)	
	client_socket.notify_job(job_id, load_model(path + "/model.h5").get_weights())