# Collectd Linux Perf Python Plugin
This is a collectd Python plugin to collect micro architectural data from Linux perf. The plugin collects both host and virtual machine specific metrics.

## Python Version
The plugin has been tested with Python 2.7.

# Third Party Libraries and Dependencies
The plugin requires the following libraries:
* [Linux Perf] (http://packages.ubuntu.com/trusty/linux-tools-common)
* [collectd 5.5 or higher] (https://collectd.org/)
* [py-cpuinfo] (https://pypi.python.org/pypi/py-cpuinfo)


##Installation
Ensure correct version of Linux perf is installed for the kernel and the perf command works.

##Configuration
Add this to /etc/collectd/collectd.conf:

    <Plugin python>
        ModulePath "/usr/share/collectd/python/"
        LogTraces true
        Interactive false
        Import "linux_perf"

        <Module linux_perf>
                duration 5
                refresh_interval 30
                temp_output_dir "/usr/share/collectd/out"
                collect_vm false
                #vm_name  "VM_NAME"
        </Module>
    </Plugin>

Ensure temp_output_dir path exists.

Modify /etc/collectd/collectd.conf  to include perf.db.

Extract the files from collectd-linux-perf to /usr/share/collectd/.

Restart the collectd service.
