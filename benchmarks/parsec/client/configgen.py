import random
import sys

def gen_configs(test_count, max_comb, repeat):
	test_array = []
	for t in range (test_count):
		test_array.append(str(t+1))
		print test_array[t]
	
	for i in range (1,max_comb):
		for k in range (repeat-1):
			for t in range (test_count):
				print test_array[t] + "," + str(random.randint(1,test_count))
		for t in range (test_count):
			test_array[t] = test_array[t] + "," +  str(random.randint(1,test_count))
			print test_array[t] 
	

def main(argv):
        test_count = int(sys.argv[1])
        max_comb = int(sys.argv[2])
	repeat = 20
	gen_configs(test_count, max_comb, repeat)

if __name__ == '__main__':
        main(sys.argv)

