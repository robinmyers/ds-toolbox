#!/usr/bin/python

import os
import json
from ansible.module_utils.basic import *

def get_conda(module, executable):
	'''Return the path to the conda executable'''

	# Check for conda executable on the PATH
	# else, check the defualt path in the user's home directory
	candidate_paths = ('conda', '~/anaconda/bin/conda', '~/anaconda3/bin/conda')

	if executable is not None:
		# If the path is to the base directory, add the path to the exectuable
		if os.path.isdir(executable):
			executable = os.path.join(executable, 'bin', 'conda')

		candidate_paths = (executable,)

	for path in candidate_paths:
		conda = module.get_bin_path(path, required=False)
		if conda is not None:
			break
	else:
		module.fail_json(
			msg='Unable to find the conda exectuable in: {}'.format(','.join(candidate_paths))
		)

	return conda


def get_envs(module, conda):
	'''Return a list of the available environment names'''
	cmd = [conda, 'env', 'list', '--json']
	(rc, stdout, stderr) = module.run_command(cmd)

	stdout = json.loads(stdout)
	envs = [os.path.basename(env) for env in stdout['envs']]

	return envs


def env_exists(module, conda, name):
	'''Return whether or not the environment exists'''
	envs = get_envs(module, conda)
	return name in envs


def create_env(module, conda, name, python, packages):
	'''Create the environment if it doesn't already exist'''

	if env_exists(module, conda, name):
		return False, False, 'Environment {} already exists'.format(name)
	
	cmd = [conda, 'create', '-y', '-q', '-n', name, '--json']

	if python:
		cmd.append('python={}'.format(python))

	if packages:
		cmd.extend(packages)

	(rc, stdout, stderr) = module.run_command(cmd)

	if rc != 0:
		return True, False, json.loads(stdout)['messages']
	else:
		return False, True, json.loads(stdout)


def remove_env(module, conda, name):
	'''Remove the environment if it exists'''

	if not env_exists(module, conda, name):
		return False, False, 'Environment {0} does not exist'.format(name)

	cmd = [conda, 'env', 'remove', '-y', '-q', '-n', name, '--json']
	(rc, stdout, stderr) = module.run_command(cmd)

	if rc != 0:
		return True, False, json.loads(stdout)['messages']
	else:
		return False, True, json.loads(stdout)


def main():

	module = AnsibleModule(
		argument_spec=dict(
			name=dict(required=True),
			python=dict(required=False, default=None),
			packages=dict(required=False, default=None, type='list'),
			executable=dict(required=False, default=None, aliases=['path']),
			state=dict(
				required=False,
				default='present',
				choices=['present', 'absent']
			)
		)
	)

	name = module.params['name']
	python = module.params['python']
	packages = module.params['packages']
	executable = module.params['executable']
	state = module.params['state']

	conda = get_conda(module, executable)

	if state == 'present':
		failed, changed, msg = create_env(module, conda, name, python, packages)
	elif state == 'absent':
		failed, changed, msg = remove_env(module, conda, name)

	if not failed:
		module.exit_json(changed=changed, msg=msg, executable=conda)
	else:
		module.fail_json(msg=msg)


if __name__ == '__main__':
	main()
