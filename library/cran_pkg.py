#!/usr/bin/python

import os
from ansible.module_utils.basic import *

def get_rscript(module, executable):
	'''Return the path to the R executable'''

	# Check for the R executable on the PATH
	# else, check the default path on most systems
	candidate_paths = ['Rscript', '/usr/bin/Rscript']

	if executable is not None:
		# If the path is to the home directory, add the path to the executable
		if os.path.isdir(executable):
			executable = os.path.join(executable, 'bin', 'Rscript')

		candidate_paths = (executable,)

	for path in candidate_paths:
		r = module.get_bin_path(path, required=False)
		if r is not None:
			break
	else:
		module.fail_json(
			msg='Unable to find the Rscript executable in {}'.format(
				','.join(candidate_paths)
			)
		)

	return r


def error_wrapper(r_cmd):
	'''Wrap an R command in error-handling/exit code and return new cmd'''
	cmd = (
		'tryCatch({},'
		'warning = function(w) {{ cat(message(w), stderr()); quit("no", 1, F) }},'
		'error = function(e) {{ cat(message(e), stderr()); quit("no", 1, F) }})'
	).format(r_cmd)

	return cmd


def run_r_command(module, rscript, r_cmd):
	'''Run R command and return system information'''
	r_cmd = error_wrapper(r_cmd)
	cmd = [rscript, '-e', r_cmd]
	
	(rc, stdout, stderr) = module.run_command(cmd)

	return rc, stdout, stderr


def package_exists(module, rscript, name):
	'''Return wether or not a specific package is installed'''
	r_cmd = 'cat("{}" %in% rownames(installed.packages()))'.format(name)

	(rc, stdout, stderr) = run_r_command(module, rscript, r_cmd)

	if rc != 0:
		module.fail_json(
			msg='Could not tell if {} is already installed.'.format(name)
		)
	elif stdout == 'TRUE':
		return True
	else:
		return False


def get_default_lib(module, rscript):
	'''Return the default library path'''
	r_cmd = 'cat(.libPaths()[1])'

	(rc, stdout, stderr) = run_r_command(module, rscript, r_cmd)

	if rc != 0:
		module.fail_json(msg='Could not verify default library path')
	else:
		return stdout


def get_default_repo(module, rscript):
	'''Return the default CRAN repository URL'''
	r_cmd = 'cat(getOption("repos")[1])'

	(rc, stdout, stderr) = run_r_command(module, rscript, r_cmd)

	if rc != 0:
		module.fail_json(msg='Could not verify default CRAN repository')
	elif stdout == '@CRAN@':
		module.fail_json(msg='No default CRAN mirror set')
	else:
		return stdout


def install_package(module, rscript, name, lib, repo):
	if package_exists(module, rscript, name):
		return False, False, 'Package {} already installed'.format(name)

	lib = get_default_lib(module, rscript) if lib is None else lib
	repo = get_default_repo(module, rscript) if repo is None else repo

	r_cmd = 'install.packages("{name}", lib="{lib}", repos="{repos}")'.format(
		name = name,
		lib = lib,
		repos = repo
	)


	(rc, stdout, stderr) = run_r_command(module, rscript, r_cmd)

	if rc != 0:
		return True, False, stderr.strip()
	else:
		return False, True, stdout.strip()


def remove_package(module, rscript, name, lib):
	'''Remove package if it exists'''
	if not package_exists(module, rscript, name):
		return False, False, 'Package {} is not installed'.format(name)

	lib = get_default_lib(module, rscript) if lib is None else lib

	r_cmd = 'remove.packages("{name}", lib="{lib}")'.format(name=name, lib=lib)

	(rc, stdout, stderr) = run_r_command(module, rscript, r_cmd)

	if rc != 0:
		return True, False, stderr.strip()
	else:
		return False, True, stdout.strip()


def main():

	module = AnsibleModule(
		argument_spec=dict(
			name=dict(required=True),
			repo=dict(required=False, default=None),
			library=dict(required=False, default=None, aliases=['lib']),
			executable=dict(required=False, default=None, aliases=['path']),
			state=dict(
				required=False,
				default='present',
				choices=['present', 'absent']
			)
		)
	)

	name = module.params['name']
	repo = module.params['repo']
	lib = module.params['library']
	executable = module.params['executable']
	state = module.params['state']

	rscript = get_rscript(module, executable)

	if state == 'present':
		failed, changed, msg = install_package(module, rscript, name, lib, repo)
	elif state == 'absent':
		failed, changed, msg = remove_package(module, rscript, name, lib)

	if not failed:
		module.exit_json(changed=changed, msg=msg, executable=rscript)
	else:
		module.fail_json(msg=msg)

if __name__ == '__main__':
	main()
