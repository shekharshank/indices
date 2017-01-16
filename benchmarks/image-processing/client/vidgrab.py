import subprocess
import threading
import os
import time
import cv2
import sys
import signal
import collections
import numpy as np
import  json
import paramiko as pm
import requests
import fabric.api
from fabric.api import env, settings

INTERVAL=2
DURATION=0
PERF_SERVER='http://<PERF_SERVER>:9950/api/runtime_perf'
APPS=[]
VMMAP = {}
UPLOAD_URL='http://<APP_SERVER>:8080/api/file_upload'
LIBVIRT_URL='qemu+ssh://<HOST>/system'
VIDFILE='test.mp4'

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


def upload_file(image):
        #files = {'image': open(image_file, 'rb')}
        files = {'image': open(image)}
        start = time.time()
        r = requests.post(UPLOAD_URL, files=files)
        resptime =  float(r.text)*1000
        end = time.time()
        return (round(resptime,3), round((end-start)*1000,3))


def exec_app(vidobj, tests, sample_count):
	interference = tests
	appname = 'img_processing'

	for i in range(sample_count):	
		end = time.time()
		output = [0.001]
		t = threading.Thread(target=perf_logger, args=['prev',interference,end,output,])
		t.start()
		time.sleep(INTERVAL)

	for i in range(sample_count):	
		start = time.time()
		end = start
		output = []
		while INTERVAL > (end -start):
			startFrame, frame = vidobj.read()
			outputfile = 'tempfile.jpg'
			cv2.imwrite(outputfile,frame)
	                resp = upload_file(outputfile)
			duration =  resp[0]
			#print duration
			output.append(duration)
			end = time.time()
		t = threading.Thread(target=perf_logger, args=[appname,interference,end,output,])
		t.start()

def startvm(test_count):
	vmname = VMMAP['parsec'+str(test_count)][1]
	p1 = subprocess.Popen('virsh -c ' + LIBVIRT_URL + ' start ' + vmname, stdout=subprocess.PIPE, shell=True)
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
		cmd = 'nohup /home/ubuntu/run.sh ' + appname + ' >& /dev/null < /dev/null &'
		fabric.api.execute(remote_command, cmd, hosts=[client_ip])
		print 'created interference for ' + 'parsec'+ str(i+1) + ' and task ' + appname
	

def executor(sample_count, image_file):
	testconfigs = []
	
	
	with open('./testlist') as f:
	    testconfigs = f.read().splitlines()

	test_count = 0
	
	for testconf in testconfigs:
		myVideObject = cv2.VideoCapture(VIDFILE)
		myVideObject.open(VIDFILE)

		tests = testconf.split(',')
		if len(tests) == 1 and tests[0] == '':
			tests = []
		if len(tests) > test_count:
			test_count += 1
			print "starting vm ..."
			startvm(test_count)
		create_interference(tests)
		exec_app(myVideObject, tests, sample_count)
		myVideObject.release()


'''
Main function goes here
'''
def main(argv):
	global APPS
	global DURATION
	global VMLIST
	
	env.user = 'ubuntu'
	env.connection_attempts = 10

	DURATION = int(sys.argv[1])
	with open('./tests') as f:
	    APPS = f.read().splitlines()
	with open('./vmlist') as f:
	    for line in f:
		vals = line.split()
		VMMAP[vals[0]] = (vals[1], vals[2])
	sample_count = DURATION / INTERVAL
	#image_dir='data'
	#files = os.listdir(image_dir)
	image_file=''
	executor(sample_count,image_file)

'''
caller of main function
'''
if __name__ == '__main__':
	main(sys.argv)
