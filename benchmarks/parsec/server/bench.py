import requests
import time
import os
import ConfigParser
import Queue
import numpy as np
import threading
import json
import subprocess

RESULT_Q = Queue.Queue()
PERF_SERVER = None
INTERVAL = 0
BENCH_ID = round(time.time())

def processor(url, perfserver_url):
        while True:
                resp = executor()
                RESULT_Q.put(resp)

def executor():
        return_code = subprocess.call("/home/ubuntu/parsec-3.0/bin/parsecmgmt -a run -p parsec.blackscholes -i simsmall", shell=True)
        #start = time.time()
        #r = requests.post(url, files=files)
        #resptime =  r.json().get('exec_time')
        #end = time.time()
        #return (round(resptime,3), round((end-start)*1000,3))
        return 10

def perf_logger():
        start = time.time()
        end = start
        arr = []
        while not RESULT_Q.empty():
                arr.append(RESULT_Q.get(False))
        print arr
        a = np.array(arr)
        size = len(arr)
        if size == 0:
                print "no sample yet"
        else:
                percentile = np.percentile(a, 90, axis=0)
                avg = np.average(a, axis=0)

                end = time.time()
                out = {"timestamp" : int(round(end*1000)),  "current_interval" : int(INTERVAL), "run_id" : BENCH_ID, "CResp" : avg.tolist(),  "C90%Resp" : percentile.tolist(),  "CThru" : [float(size), float(size)]}
                print ("Sending output : " + str(out))
                #r = requests.post(PERF_SERVER, data=json.dumps(out), headers={"content-type": "text/javascript"})
                r = requests.post(PERF_SERVER,json=out)

        duration = end-start
        threading.Timer(INTERVAL - duration, perf_logger).start()


if __name__ == '__main__':
        print 'Reading config ...'
        conf = os.path.join(os.path.dirname(__file__), './config')
        config = ConfigParser.ConfigParser();
        config.read(conf);
        url  = config.get('IMAGES', 'UPLOAD_URL')
        INTERVAL  = float(config.get('PROCESSING', 'INTERVAL'))
        perfserver_url  = config.get('PROCESSING', 'INDICES_LOCAL_MANAGER')
        print 'Starting perf logger ...'
        PERF_SERVER = perfserver_url
        t = threading.Thread(target=perf_logger)
        t.start()

        print 'Starting processor ...'
        processor(url, perfserver_url)

