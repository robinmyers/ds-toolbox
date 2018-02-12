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


def get_packages(module, conda, env):
	'''Return a list of packages installed'''
	cmd = [conda, 'list', '--json']

	if env is not None:
		cmd.extend(['-n', env])

	(rc, stdout, stderr) = module.run_command(cmd)

	stdout = json.loads(stdout)
	packages = [(p['name'], p['version']) for p in stdout]

	return packages


def package_exists(module, conda, env, name, version):
	'''Return whether or not a specific packages and version exists'''
	packages = get_packages(module, conda, env)

	if version is None:
		packages = [p[0] for p in packages]
		return name in packages
	else:
		return (name, version) in packages


def install_package(module, conda, env, name, version, channel):
	'''Install package if it doesn't exist or is at a different version'''
	if package_exists(module, conda, env, name, version):
		return False, False, 'Package {} already installed'.format(name, version)

	cmd = [conda, 'install', '-y', '-q', '--json']

	if env is not None:
		cmd.extend(['-n', env])

	if channel is not None:
		cmd.extend(['-c', channel])

	if version is None:
		cmd.append(name)
	else:
		cmd.append('{}={}'.format(name, version))

	(rc, stdout, stderr) = module.run_command(cmd)

	if rc != 0:
		return True, False, json.loads(stdout)['message']
	else:
		#return False, True, json.loads(stdout)
		return False, True, json.loads(stdout)


def remove_package(module, conda, env, name):
	'''Remove package if it exists'''
	if not package_exists(module, conda, env, name, None):
		return False, False, 'Package {} is not installed'.format(name)

	cmd = [conda, 'remove', '-y', '-q', '--json', name]

	if env is not None:
		cmd.extend(['-n', env])

	(rc, stdout, stderr) = module.run_command(cmd)

	if rc != 0:
		return True, False, stderr
	else:
		return False, True, json.loads(stdout)


def main():

	module = AnsibleModule(
		argument_spec = dict(
			name=dict(required=True),
			version=dict(required=False, default=None, aliases=['ver']),
			environment=dict(required=False, default=None, aliases=['env']),
			channel=dict(required=False, default=None),
			executable=dict(required=False, default=None, aliases=['path']),
			state=dict(
				required=False,
				default='present',
				choices=['present', 'absent']
			)
		)
	)

	name = module.params['name']
	version = module.params['version']
	env = module.params['environment'] #
	channel = module.params['channel'] 
	executable = module.params['executable'] #
	state = module.params['state']

	conda = get_conda(module, executable)
	
	# If environment is given check to see if it exists, fail ig it doesn't
	if env is not None and not env_exists(module, conda, env):
		module.fail_json(msg='Environment {} does not exist'.format(env))

	if state == 'present':
		failed, changed, msg = install_package(module, conda, env, name, version, channel)
	elif state == 'absent':
		failed, changed, msg = remove_package(module, conda, env, name)

	if not failed:
		module.exit_json(changed=changed, msg=msg, executable=conda)
	else:
		module.fail_json(msg=msg)


if __name__ == '__main__':
	main()
