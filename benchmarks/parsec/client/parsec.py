import subprocess
import threading
import os
import time
import sys
import signal
import collections
import numpy as np, json
import paramiko as pm
import requests
import fabric.api
from fabric.api import env, settings

INTERVAL=2
DURATION=0
PERF_SERVER='http://<manager_IP>:9950/api/runtime_perf'
APPS=[]
VMMAP = {}
BENCH_ID = round(time.time())



def perf_logger(test_name,interference,end,arr):
        a = np.array(arr)
        size = len(arr)
        if size == 0:
                print "no sample yet"
        else:
                percentile = np.percentile(a, 90, axis=0).round(3)
                avg = np.average(a, axis=0).round(3)
	
                out = {"timestamp" : int(round(end*1000)),  "current_interval" : int(INTERVAL), "run_id" : test_name, "run_grp" :  str(BENCH_ID), "CResp" : [avg.tolist()],
			  "C90%Resp" : [percentile.tolist()],  "CThru" : [float(size), float(size)], "name" : "parsec", "interference": interference}
                print ("Sending output : " + str(out))
                r = requests.post(PERF_SERVER,json=out)


def exec_app(client, tests, sample_count):
	appname = APPS[int(tests[-1]) - 1]
	print appname
	interference = tests[:-1]

	for i in range(sample_count):	
		start = time.time()
		end = start
		output = []
		while INTERVAL > (end -start):
			(stdin, stdout, stderr) = client.exec_command('/home/ubuntu/parsec-3.0/bin/parsecmgmt -a run -p ' + appname + ' -i simsmall -n 4')
			duration = 0
			for line in stdout:
				out = line.strip()
				if out.startswith('real'):
					vals = out.split('m')
					mins = float(vals[0][5:])
					secs = float(vals[1][:-1])
					duration = round(mins*60 + secs,3)
			output.append(duration)
			end = time.time()
		t = threading.Thread(target=perf_logger, args=[appname,interference,end,output,])
		t.start()

def startvm(test_count):
	vmname = VMMAP['parsec'+str(test_count-1)][1]
	p1 = subprocess.Popen('virsh start ' + vmname, stdout=subprocess.PIPE, shell=True)
        output, error = p1.communicate()
        duration = 0
        for line in output.splitlines():
        	out = line.strip()
		print out
	time.sleep(1)

def remote_command(cmd):
	with settings(warn_only=True):
		fabric.api.run('pkill -9 run.sh')
	time.sleep(1)
	fabric.api.run(cmd, pty=False)


def create_interference(tests):
	for i in range(len(tests)):
		appname = APPS[int(tests[i]) - 1]
		client_ip = VMMAP['parsec'+ str(i+1)][0]
		cmd = 'nohup /home/ubuntu/run.sh ' + appname + ' parsec.blackscholes >& /dev/null < /dev/null &'
		fabric.api.execute(remote_command, cmd, hosts=[client_ip])
		print 'created interference for ' + 'parsec'+ str(i+1) + ' and task ' + appname
	

def executor(sample_count):
	testconfigs = []
	
	
	client = pm.SSHClient()
	client.load_system_host_keys()
	client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
	client.set_missing_host_key_policy(pm.AutoAddPolicy())
	client.connect(VMMAP['parsec-bench'][0], username='ubuntu')

	with open('./testlist') as f:
	    testconfigs = f.read().splitlines()

	test_count = 1
	
	for testconf in testconfigs:
		tests = testconf.split(',')
		if len(tests) > test_count:
			test_count += 1
			print "starting vm ..."
			startvm(test_count)
		create_interference(tests[:-1])
		exec_app(client, tests, sample_count)


'''
Main function goes here
'''
def main(argv):
	global APPS
	global DURATION
	global VMLIST
	
	env.user = 'ubuntu'
	env.connection_attempts = 100

	DURATION = int(sys.argv[1])
	with open('./tests') as f:
	    APPS = f.read().splitlines()
	with open('./vmlist') as f:
	    for line in f:
		vals = line.split()
		VMMAP[vals[0]] = (vals[1], vals[2])
	sample_count = DURATION / INTERVAL
	executor(sample_count)

'''
caller of main function
'''
if __name__ == '__main__':
	main(sys.argv)
