import sys
import subprocess

def exec_app(appname, exptype):
        while True:
                p1 = subprocess.Popen('/home/ubuntu/parsec-3.0/bin/parsecmgmt -a run -p ' + appname + ' -i ' + exptype + ' -n 4', stdout=subprocess.PIPE, shell=True)
                output, error = p1.communicate()
                duration = 0
                for line in output.splitlines():
                        out = line.strip()
                        if out.startswith('real'):
                                vals = out.split('m')
                                mins = float(vals[0][5:])
                                secs = float(vals[1][:-1])
                                duration = mins*60 + secs
                print appname, duration

if __name__ == '__main__':
        testnum = int(sys.argv[1])
        testtype = sys.argv[2]
        apps = []
        with open('./tests') as f:
            apps = f.read().splitlines()
        exptype = 'simsmall'
        if testtype == '2':
                exptype = 'simlarge'
        print 'Running test num ', apps[testnum], '  with type ', exptype
        exec_app(apps[testnum], exptype)

