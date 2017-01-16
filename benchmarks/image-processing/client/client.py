import subprocess
import threading
import socket
import os
import time
import cv2
import sys
import signal
import collections
import numpy as np
import json
import random
import paramiko as pm
import requests
import fabric.api
import ping
from fabric.api import env, settings

INTERVAL=5.0
DURATION=0
PERF_SERVER='http://<PERF_SERVER>:5001'
SLO='/api/receive_slo'
LATENCY='/api/receive_latency'
MIGRATE='/api/migrate'
SERVER_IP='<APP_SERVER>'
PORT=8080
APP_NAME='img_processing'
VIDFILE='test.mp4'
TESTFILE='testfile.jpg'
SKT = None
CHANGE = "0"

BENCH_ID = round(time.time())

def perf_logger(end,arr):
        a = np.array(arr)
        size = len(arr)
        if size == 0:
                print "no sample yet"
        else:
                percentile = np.percentile(a, 90, axis=0).round(3)
                avg = np.average(a, axis=0).round(3)
	
                out = {"timestamp" : int(round(end*1000)),  "current_interval" : int(INTERVAL), "CResp" : avg.tolist(),
			  "C90%Resp" : percentile.tolist(), "name" : APP_NAME}
                print ("Sending output : " + str(out))
                r = requests.post(PERF_SERVER+SLO,json=out)
		content = r.json()
		if len(content) != 0:
			global CHANGE
			CHANGE = "1"
			resp = measure_latencies(content)
			returnval = {'appname': APP_NAME, 'mdcs' : resp}
			post_latencies(returnval)
		#print content

def post_latencies(resp):
	r = requests.post(PERF_SERVER+LATENCY,json=resp)
	server = r.text
	if server != '':
		global CHANGE
		CHANGE = "2"
		postval = {'appname': APP_NAME, 'server' : server}
		r = requests.post(PERF_SERVER+MIGRATE,json=postval)
		print "Switching server to: " + server
		CHANGE = "3"
		global SERVER_IP
		global PORT
		SERVER_IP = server
		PORT = PORT2
		SKT.close()
			
	print r.text
	

def measure_latencies(mdcs):
	resp = {}
	mdc_threads = []
	for mdc, ip in mdcs.iteritems():
		#measure_latency	(resp, mdc, ip)
		t = threading.Thread(target=measure_latency, args=[resp,mdc,ip,])
		t.start()
		mdc_threads.append(t)
	for m in mdc_threads:
		m.join()
	return resp

def measure_http(ip):
        server = ip
        upload_url = URL_PREFIX + server + URL_SUFFIX
        #files = {'image': open(image_file, 'rb')}
        #files = {'image': open(TESTFILE)}
	out = []
	for i in range (0,5):
		name = str(i+1) + TESTFILE
		files = {'image': open(name)}
		start = time.time()
		r = requests.post(upload_url, files=files)
		resptime =  float(r.text)*1000
		end = time.time()
		duration = round((end-start)*1000,3)
        	print (round(resptime,3), duration, server)
		out.append(duration)
	return out


def measure_ping(ip):
	out = []
	for i in range (0,5):
		resp = ping.quiet_ping(ip, count=2) 
		out.append(round(resp[1],3))
	return out	

		
def measure_latency (returnvar, mdc, ip):
	print ip
	#httpout = measure_http(ip)
	#pingout = measure_ping(ip)
	s = socket.socket() 
	s.connect((ip, PORT))
	s.settimeout(5)
	s.send("Hello server!")
	s.recv(1024)
	out = []
	
	for i in range (0,5):
		resp = upload_file(TESTFILE, s)
		out.append(resp[1])
	out.sort()
	#print pingout, httpout, out
	#print out
	s.close()
	returnvar[mdc] = out[3] 
	

def upload_file(filename, s):
	server = SERVER_IP
        start = time.time()
	filesize = os.path.getsize(filename)
	filesize = bin(filesize)[2:].zfill(32) # encode filesize as 32 bit binary
	s.send(filesize)
	f = open(filename,'rb')
	l = f.read(1024)
	while (l):
		s.send(l)
		l = f.read(1024)
	f.close()
	#s.sendall(content)
	resp = s.recv(1024)
        resptime =  float(resp)
        end = time.time()
        return (resptime, round((end-start)*1000,3), server)

def log_resp(filewriter, duration, exec_time, server):
	filewriter.write(str(int(round(time.time()*1000)))+","+str(duration)+","+str(exec_time)+","+server+","+CHANGE+"\n")
	filewriter.flush()

def executor():

	f = open('response.csv','w')
	f.write('TIMESTAMP,RESPONSE_TIME,EXECUTION_TIME,SERVER_IP\n')
	
	outputfile = 'tempfile.jpg'
	start = time.time()
	output = []
	myVideObject = cv2.VideoCapture(VIDFILE)
	myVideObject.open(VIDFILE)
	global SKT
	while True:
	    try:
	        SKT = socket.socket() 
		serverip = SERVER_IP
		print serverip, PORT
		SKT.connect((serverip, PORT))
		SKT.send("Hello server!")
		resp = SKT.recv(1024)
		print(repr(resp))
	
		last_time = time.time() 
	
		while True:
				timediff = time.time() - last_time
				if timediff < 0.20:
					time.sleep(0.20 - timediff)
				last_time = time.time()
				startFrame, frame = myVideObject.read()
				cv2.imwrite(outputfile,frame)
				resp = upload_file(outputfile, SKT)
				output.append(resp[:-1])
				t = threading.Thread(target=log_resp, args=[f,resp[1],resp[0],resp[2],])
				t.start()
				end = time.time()
				if end - start >= INTERVAL:
					t = threading.Thread(target=perf_logger, args=[end,output,])
					t.start()
					start = end
					output = []
		SKT.close()
	    except Exception, e:
	    	print "received exception", str(e)
		time.sleep(0.1)
		#SKT.close()
	myVideObject.release()

def remote_command(cmd):
	with settings(warn_only=True):
		fabric.api.run('pkill -9 run.sh')
	time.sleep(1)
	fabric.api.run(cmd, pty=False)


'''
Main function goes here
'''
def main(argv):
	
	env.user = 'ubuntu'
	env.connection_attempts = 5

	executor()

'''
caller of main function
'''
if __name__ == '__main__':
	main(sys.argv)
