from tensorflow import keras
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical
import pandas
import numpy as np
import copy

# calulate new weights.
def update_weight(weights, train_nums = 0, client_train_nums = [], client_weights = []):
	client_len = len(client_weights)
	for i, sequence in enumerate(weights):
		for j, weight in enumerate(sequence):
			if isinstance(weight, list):
				for z, weightz in enumerate(weight):
					new_weight = 0
					for k in range(0, client_len):
						new_weight += client_weights[k][i][j][z] * client_train_nums[k] / train_nums
					weights[i][j][z] = new_weight					
			else:
				new_weight = 0
				for k in range(0, client_len):
					new_weight += client_weights[k][i][j] * client_train_nums[k] / train_nums
				weights[i][j] = new_weight
	return weights

if __name__ == '__main__':
	model = load_model(r'./examples/model.h5')
	test_arr1 = model.get_weights()
	test_arr2 = copy.deepcopy(test_arr1)
	for i in range(0, len(test_arr2)):
		for j in range(0, len(test_arr2[i])):
			test_arr2[i][j] += 0.05
	print('old: ', test_arr1)
	weights = update_weight(test_arr1, 10, [2, 8], [test_arr1, test_arr2])
	print('new: ',  weights)
	model.set_weights(weights)

	test_data = pandas.read_csv('./examples/mnist_train_3w_b.csv')
	test_img = test_data.iloc[:,2:786]
	test_label = to_categorical(test_data.iloc[:,1])
	test_loss, test_accuracy = model.evaluate(test_img, test_label)
	print('test_loss:', test_loss, ',test_accuracy:', test_accuracy)