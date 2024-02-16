import yaml


def read_yaml_file(file_path):
	with open(file_path, 'r') as f:
		file_dict = yaml.load(f,Loader=yaml.FullLoader)
	return file_dict

def write_yaml_file(file_path, data):
	with open(file_path, 'w') as f:
		yaml.dump(data,f)


if __name__ == '__main__':
	test_path = ('../templates/test.yaml')
	data = { 'ciaone':[0,9,8,7,8],
			 'ciao':0,
			 'cia':{'ci': 39, 'yo':[0,9,8]},
	}
	write_yaml_file(test_path, data)