import json

def get():
	return json.load(open('configs/common_config.json', 'r' ,encoding="utf-8"))