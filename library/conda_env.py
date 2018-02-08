#!/usr/bin/python

import json
import re
from ansible.module_utils.basic import *

def get_conda(module):
	return module.get_bin_path('conda', required=True)

def conda_env_exists(module, conda):
	cmd = [conda, 'env', 'list', '--json']
	(rc, stdout, stderr) = module.run_command(cmd)

	r = re.compile('.*/{0}$'.format(module.params['name']))
	envs = json.loads(stdout)['envs']

	return any([r.match(env) for env in envs])

def conda_create_env(module, conda, name, python, packages):
	env_exists = conda_env_exists(module, conda)

	if env_exists:
		return True, False, {'msg': 'Environment {0} already exists'.format(name) }

	cmd = [conda, 'create', '-y', '-n', name, '--json']

	if python:
		cmd.append('python={0}'.format(python))

	if packages:
		cmd.extend(packages)

	(rc, stdout, stderr) = module.run_command(cmd)

	if rc == 0:
		return True, True, {'data': stdout }
	else:
		return False, False, {'data': stderr }

def conda_remove_env(module, conda, name):
	env_exists = conda_env_exists(module, conda)

	if not env_exists:
		return True, False, {'msg': 'Environment {0} does not exist'.format(name) }

	cmd = [conda, 'env', 'remove', '-y', '-n', name, '--json']
	(rc, stdout, stderr) = module.run_command(cmd)

	if rc == 0:
		return True, True, {'data': stdout }
	else:
		return False, False, {'data': stderr }

def main():

	module = AnsibleModule(argument_spec={
		'name': {'required': True, 'type': 'str'},
		'python': {'default': None, 'type': 'str'},
		'packages': {'default': None, 'type': 'list'},
		#'file': {'default': None, 'type': 'str'},
		'state': {
			'default': 'present',
			'choices': ['present', 'absent'],
			'type': 'str'
		}
	})

	conda = get_conda(module)
	name = module.params['name']
	python = module.params['python']
	packages = module.params['packages']
	state = module.params['state']

	if state == 'present':
		success, has_changed, result = conda_create_env(module, conda, name, python, packages)

	if state == 'absent':
		success, has_changed, result = conda_remove_env(module, conda, name)

	if success:
		module.exit_json(changed=has_changed, meta=result)
	else:
		module.fail_json(msg='conda failed', meta=result)

if __name__ == '__main__':
	main()
