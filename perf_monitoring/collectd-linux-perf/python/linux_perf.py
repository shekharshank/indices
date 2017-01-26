import collectd
import subprocess
import datetime, time
import cpuinfo
import os
import ConfigParser

HARDWARE_MAP_FILE = 'hardware/hardware_map.info'
HARDWARE_PARAM_FILE = 'hardware/hardware_registers.info'
_hardware_param_map = {}

# reads the initial configuration of the service
def configure(configobj):
        collectd.debug('Configuring plugin')
        config = {c.key: c.values for c in configobj.children}
        global _duration
        global _vmmap
        global _refresh_interval
        global _collectvm
        global _isvmnamesupplied
        global _refresh_time
        global _temp_out
        _duration = str(config.get("duration")[0])
        _temp_out = config.get("temp_output_dir")[0]
        _collectvm = config.get("collect_vm")[0]
	if _collectvm:
		_isvmnamesupplied = False
		_vmmap = {}
		_refresh_time = time.time()
		_refresh_interval = config.get("refresh_interval")[0]
		vmconfig = config.get("vm_name")
		if vmconfig is not None:
			_isvmnamesupplied = True
			_vmmap = {config.get("vm_name")[0] : None}

# refreshes the list of vms to check for new vms
def refresh_vmname_list():
        p = subprocess.Popen("virsh list --name" , shell=True,  stdout=subprocess.PIPE)
        out,err = p.communicate()
        global _vmmap
        _vmmap = {}
        for line in out.splitlines():
                vmname = line.strip()
                if vmname != "":
                        _vmmap[line] = None
# adds additional details for processing
def fill_vm_details():
        vmkeys = _vmmap.keys()
        for vmname in vmkeys:
                # assuming we are using libvirt to run the vms
                p = subprocess.Popen("cat /var/run/libvirt/qemu/" + vmname + ".pid", shell=True,  stdout=subprocess.PIPE)
                processid = p.communicate()[0]
                _vmmap[vmname] = [processid]

                p = subprocess.Popen("virsh dominfo " + vmname , shell=True,  stdout=subprocess.PIPE)
                out,err = p.communicate()
                for line in out.splitlines():
                        if line.startswith('UUID:'):
                                _vmmap[vmname].append(line.split(':')[1].strip())

def identify_hardware():
	hardware_file = os.path.join(os.path.dirname(__file__), HARDWARE_MAP_FILE)
	hardware_model_map = {}
	with  open(hardware_file, 'r') as f:
        	for line in f:
                	vals=line.rstrip('\n').split('=')
	                keys=vals[1].split(',')
        	        vendor = keys[0]
	                model = int(keys[1])
        	        family = int(keys[2])
                	hardware_model_map[(vendor,model,family)] =  vals[0]

	info = cpuinfo.get_cpu_info()
	hardware_name = hardware_model_map.get((info.get('vendor_id'), info.get('model'), info.get('family')))
	if hardware_name is None:
        	hardware_name = 'UNKNOWN'
	return hardware_name
		
def fill_mem_bw_counter_names(hardware_name, hardware_params):
	global _hardware_param_map
	counters = hardware_params.get('MEM_BW', hardware_name)
	
	_hardware_param_map = {'MEM_BW' : counters}
	operation = hardware_params.get('MEM_BW_COUNTER_RELATION', hardware_name)
	_hardware_param_map['MEM_BW_COUNTER_RELATION'] =  operation

# initialize
def init():
        collectd.debug('Initializing plugin')
	hardware_name = identify_hardware()
	if hardware_name == 'UNKNOWN':
		msg = 'ERROR: Perf Plugin: Unrecognized hardware type.'
		raise Exception(msg)
	hardware_params_file = os.path.join(os.path.dirname(__file__), HARDWARE_PARAM_FILE)
        hardware_params  = ConfigParser.ConfigParser();
        hardware_params.read(hardware_params_file);
	fill_mem_bw_counter_names(hardware_name, hardware_params)
	
	if _collectvm:	
		if (not _isvmnamesupplied):
			refresh_vmname_list()
			_refresh_time = time.time()
		fill_vm_details()

# converts string for processing
def get_number(s):
    try:
        return float(s)
    except ValueError:
        return -1
        #return float('nan')


def get_vm_perf_command():
        comm_pre =  "perf stat -x , -o " + _temp_out + "/"
        comm_post =  " sleep " + _duration
	command = []

        for vmname, data in _vmmap.iteritems():
                command_default =   comm_pre + vmname + "_all.out " + " -e  cs,page-faults,cycles,instructions " +  " -p " + data[0] + comm_post
		command.append(command_default)
                command_cache =   comm_pre + vmname + "_cache.out " + " -e  cache-references,cache-misses " +  " -p " + data[0] + comm_post
		command.append(command_cache)
                command_membw =   comm_pre + vmname + "_membw.out " + " -e  " + _hardware_param_map.get('MEM_BW') +  " -p " + data[0] + comm_post
		command.append(command_membw)
                command_kvm =   comm_pre + vmname + "_kvm.out " + " -e  sched:sched_switch,kvm:kvm_exit,sched:sched_stat_wait,sched:sched_stat_iowait" +  " -p " + data[0] + comm_post
		command.append(command_kvm)

	return command

def parse_and_set_result(file_name, is_host, membw_counter_count=0):

        all_vals = []
        membw_counter1 = 0.0
        with  open(file_name, 'r') as f:
                count = 0
                for line in f:
                        count += 1
                        if count < 3:
                                continue
                        linevals = line.split(',')
			# if first mem bw counter 
                        if (is_host and count == 9) or ((not is_host) and membw_counter_count != 0 and count == 4 ):
                                membw_counter1 = linevals[0]
                                if membw_counter_count == 1:
                                        all_vals.append(get_number(membw_counter1))
			# else if second 	
                        elif (membw_counter_count == 2) and ((is_host and count == 10) or (not is_host)):
				value = eval(membw_counter1 + _hardware_param_map.get('MEM_BW_COUNTER_RELATION') + linevals[0])
				all_vals.append(value)
                        else:
                                all_vals.append(get_number(linevals[0]))
        return all_vals


# reader function
def reader(input_data=None):
        out_all = collectd.Values();
        out_all.plugin = 'linux_perf'
        out_all.type = 'perf'

        # command to write  host perf metriss to file
        # ORDER IS IMPORTANT
        host_command =  "perf stat -x , -o " +  _temp_out + "/all.out " + " -e cs,page-faults,cycles,instructions,cache-references,cache-misses,"  
	host_command += _hardware_param_map.get('MEM_BW') + ","
	host_command += "sched:sched_switch,kvm:kvm_exit,sched:sched_stat_wait,sched:sched_stat_iowait" + " -a sleep " + _duration


        commands = [host_command]

        if  _collectvm:
		# refresh the list of vms if needed
		if  (not _isvmnamesupplied) and (time.time() >  (_refresh_time + _refresh_interval)):
			refresh_vmname_list()
			fill_vm_details()

		vm_commands = get_vm_perf_command()
		commands.extend(vm_commands)

        processes = [subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE) for cmd in commands]
        for p in processes:
                p.wait()


	membw_counter_count = len(_hardware_param_map.get('MEM_BW').split(","))

        # parse and send host value
        host_filename =  _temp_out + "/all.out"
        out_all.plugin_instance = "all"

	all_vals = parse_and_set_result(host_filename, True, membw_counter_count)

        out_all.values = all_vals
        out_all.dispatch()


        # loop through vm list and send data
        if  _collectvm:
		filename_sfx_list = ["_all.out","_cache.out","_membw.out","_kvm.out"]
		collectd.debug(str(_vmmap))
		for vmname, data in _vmmap.iteritems():
			all_vals = []
			out_all.plugin_instance = data[1]
			for result_type in filename_sfx_list:
				vmdata_filename =  _temp_out + "/" + vmname + result_type
				if filename_sfx_list == "_membw.out":
					vals = parse_and_set_result(vmdata_filename, False, membw_counter_count)
					all_vals.extend(vals)
				else:
					vals = parse_and_set_result(vmdata_filename, False)
					all_vals.extend(vals)

			out_all.values = all_vals
			collectd.debug('dipatching: ' + str(out_all.values))
			out_all.dispatch()



collectd.register_config(configure)
collectd.register_init(init)
collectd.register_read(reader)

