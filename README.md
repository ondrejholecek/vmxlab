# vmxlab
Libraries and utilities to help setting the lab for VMware ESXi(s) managed by vCenter with (vSphere) NSX and FortiGate VMX.

:exclamation: **This is not production ready application!** It is rather a proof of concept, showing how different VMware APIs and FortiGate can work together to help setting up the test lab.

# Contents

The repository is composed of following parts:
  - [Shell scripts to guide you through setting up the environment from point zero](#shell-scripts)
  - [Utility vmxlab.py that combines all the APIs in simple command line tool](#vmxlab-utility)
  - [Python modules implementing different APIs that can be used in your programs](#modules)

## Shell scripts

These scripts are very simple scripts using the `vmxlab.py` utility described bellow. Those are not meant to be generic scripts at all, but they rather show what kind of commands with what parameters can be useful when setting up the lab. They also do not do any input validation and have some hardcoded values that expect certain setting of vCenter/NSX/ESxi/FortiGate.

### prepare_esxi.sh

Guides you though initial setup of ESXi VM after deploying in DHCP VLAN. In two phases it removed the saved invalid MAC addresses and the default small local datastore.

Example:
```
$ ./prepare_esxi.sh
==============================================
=== Prepare the lab ESXi for the first use ===
==============================================

Enter the initial IP address: 10.1.8.71
- Waiting for IP to start responding: ......
- Enabling SSH
SSH enabled on ESXi host 10.1.8.71
- Removing wrong MAC address - phase 1
Wait for device to reboot
Enter the new IP address: 10.1.8.47
- Waiting for IP to start responding:
- Removing wrong MAC address - phase 2
Wait for device to reboot
Enter the final IP address: 10.1.8.14
- Waiting for IP to start responding:
- Removing default small datastore
Deleting local datastore "datastore1"
- Done
```

### prepare_vcenter.sh

Initial configuration of brand new vCenter. Creates datastore and cluster and allows to register all ESXi hosts in the cluster. 

Then it creates the `lab` distributed switch that spans though all the registered ESXi hosts and attaches the uplink(s) to `vmnic1` on each ESXi host (which should be physically configured as a VLAN trunk port with the right VLANs tagged).

At the end it mount the NFS shared datastore on each of the ESXi host. The datastore name in vCenter is hardcoded to `shared`.

```
$ ./prepare_vcenter.sh
=================================================
=== Prepare the lab vCenter for the first use ===
=================================================

Before continuing please make sure you can login to vCenter
over the WebUI on the standard HTTPs port 443.

This interface is not available immediatelly after deploying!
Please wait until it you can reach it!

Enter the vCenter's IP address: 10.1.8.62
- Creating default datacenter
Creating datacenter "Datacenter" on vCenter host 10.1.8.62
- Creating default cluster
Creating cluster "Cluster" on vCenter host 10.1.8.62
Enter IP addresses ESXi host (when finished press enter): 10.1.8.37
- Getting certificate thumbprint for host 10.1.8.37
- Registering host 10.1.8.37 to vCenter
Registering ESXi host 10.1.8.37 to vCenter 10.1.8.62
Enter IP addresses ESXi host (when finished press enter): 10.1.8.14
- Getting certificate thumbprint for host 10.1.8.14
- Registering host 10.1.8.14 to vCenter
Registering ESXi host 10.1.8.14 to vCenter 10.1.8.62
Enter IP addresses ESXi host (when finished press enter):
- Creating distributed switch "lab" with all current hosts NIC "vmnic1" attached
Creating dvSwitch "lab"
Enter NFS server IP: 10.1.8.25
Enter NFS path: /mnt/vol/dataset
- Mounting NFS datastore "shared" from 10.1.8.25:/mnt/vol/dataset
Created NFS datastore "shared"
- Mounting NFS datastore "shared" from 10.1.8.25:/mnt/vol/dataset
Created NFS datastore "shared"
- Done
```

### prepare_nsx.sh

First it creates a dedicated portgroup for synchronization network between FortiGate Service Manager and all VMX agent VMs.

Then it registeres the NSX Manager to vCenter, uploads the license and assigns it to the current NSX Manager.

After that it deploys the FortiGate Service Manager VM from the OVF template stored locally and when it boot up, it configures the basic parameters and connects it to the NSX Manager. Then it prepares the current cluster for NSX services and deploys the FortiGate VMX agent VMs to all the ESXi hosts.

At the end it creates a default Security Policy that redirects all traffic to FortiGate VMX.

**The only thing that is missing before the NSX starts redirecting traffic through FortiGate VMX is creating a custom Security Groups and assigning them to the default Security Policy.**

```
$ ./prepare_nsx.sh
=============================================
=== Prepare the lab NSX for the first use ===
=============================================

Enter the vCenter's IP address: 10.1.8.62
Enter the NSX Manager's IP address: 10.1.8.36

========================================
=== Create synchronization portgroup ===
========================================
Enter VLAN ID for VMX synchronization network: 111
- Creating portgroup "vmxsync" on distributed switch "lab" with VLAN 111
Created portgroup "vmxsync"

=======================================
=== Register NSX Manager to vCenter ===
=======================================
- Getting vCenter thumbprint
- Registering NSX Manager to vCenter
Enter file containing NSX Manager license: /tmp/license
- Installing and assigning NSX license
Adding license key to vCenter
Assigning license key to NSX Manager

========================================
=== Deploy FortiGate Service Manager ===
========================================
Enter path to FortiGate Service Manager .ovf file: /tmp/svm0245/FortiGate-VMX-Service-Manager.ovf
Deployed VM "FortiGate-SVM"
Started VM "FortiGate-SVM"
Wait for FortiGate SVM to boot up and acquire IP address!
Enter IP address of FortiGate SVM: 10.1.8.48
- Configuring sync interface
- Creating dhcp server
Enter the URL to FortiGate VMX .ovf file: http://10.1.8.75/vmx-b0231/FortiGate-VMX.ovf
- Configuring NSX Service
- Installing NSX Service

=============================
=== Configure NSX Manager ===
=============================
- Getting cluster ID
- Preparing cluster for NSX
- Getting portgroup ID of "vmxsync" on dvSwitch "lab"
- Getting datastore ID of "shared" datastore
- Deploying agents for service "labvmx"
- Creating a default Security Policy redirected to "labvmx" service and vdom "nsx"
Created Security Policy "Default policy"

Done

Note: At this moment everything is prepared but no traffic is redirected to FortiGate VMX.
      To redirect traffic, you need to create a Security Group and apply it to default Policy.
```

## vmxlab utility

`vmxlab.py` is CLI based utility that calls the procedures from the modules described bellow.

It has many commands divided into several groups depending where and how the action should be performed. You can use `-h` after the target specific command to get all necessary parameters. For example, to create a new portgroup on vCenter, you can use:

```$ ./vmxlab.py vcenter create-portgroup -h
usage: vmxlab.py vcenter create-portgroup [-h] --name DVSWITCH_PGNAME
                                          --dvswitch DVSWITCH_NAME --vlan DVSWITCH_VLANID

optional arguments:
  -h, --help               show this help message and exit
  --name DVSWITCH_PGNAME       Name of the portgroup
  --dvswitch DVSWITCH_NAME     Name of the dvSwitch
  --vlan DVSWITCH_VLANID       VLAN ID
```

### On ESXi host

```
$ ./vmxlab.py esxi -h
usage: vmxlab.py esxi [-h] --host HOST [--user USER] [--password PASSWORD]
                      [--port PORT] [--sshport SSHPORT]
                      {ssh,thumbprint,erase-mac,list-datastores,delete-datastore,add-nfs-datastore}
                      ...

positional arguments:
  {ssh,thumbprint,erase-mac,list-datastores,delete-datastore,add-nfs-datastore}
    ssh                 SSH service
    thumbprint          Print SSL certificate thumbprint
    erase-mac           Erase hardcoded MAC address
    list-datastores     List all datastores
    delete-datastore    Delete datastores
    add-nfs-datastore   Add NFS datastore

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           ESXi hostname or IP
  --user USER           ESXi username, default "root"
  --password PASSWORD   ESXi password, default "fortinet"
  --port PORT           ESXi vSphere API port
  --sshport SSHPORT     ESXi ssh port
```

### On vCenter 

```
$ ./vmxlab.py vcenter -h
usage: vmxlab.py vcenter [-h] --host HOST [--user USER] [--password PASSWORD]
                         [--port PORT] [--datacenter DATACENTER]
                         [--cluster CLUSTER]
                         {datacenter,cluster,list-hosts,license,thumbprint,register,deploy,create-portgroup,create-dvswitch,extend-dvswitch,clone-vm,show}
                         ...

positional arguments:
  {datacenter,cluster,list-hosts,license,thumbprint,register,deploy,create-portgroup,create-dvswitch,extend-dvswitch,clone-vm,show}
    datacenter          Datacenter management
    cluster             Cluster management
    list-hosts          List all registered ESXi hosts
    license             License management
    thumbprint          Show vCenter certificate thumbprint
    register            Register ESXi server
    deploy              Deploy VM from OVF
    create-portgroup    Create portgroup
    create-dvswitch     Create dvSwitch
    extend-dvswitch     Extend dvSwitch to the ESXi host
    clone-vm            Light clone VM
    show                Show MOIDs for various objects

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           vCenter hostname or IP
  --user USER           vCenter username, default
                        "administrator@vsphere.local"
  --password PASSWORD   vCenter password, default "fortinet"
  --port PORT           vCenter vSphere API port
  --datacenter DATACENTER
                        Datacenter name
  --cluster CLUSTER     Cluster name
```

### On NSX Manager

```
$ ./vmxlab.py nsx -h
usage: vmxlab.py nsx [-h] --host HOST [--user USER] [--password PASSWORD]
                     [--port PORT]
                     {create-policy,save-policy,delete-policy,restore-policy,register,prepare,deploy,undeploy}
                     ...

positional arguments:
  {create-policy,save-policy,delete-policy,restore-policy,register,prepare,deploy,undeploy}
    create-policy       Create Security Policy
    save-policy         Save Security Policies
    delete-policy       Delete Security Policy
    restore-policy      Restore Security Policy
    register            Register to vCenter
    prepare             Prepare ESXi hosts for NSX
    deploy              Deploy NSX service
    undeploy            Delete NSX service

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           NSX hostname or IP
  --user USER           NSX user, default "admin"
  --password PASSWORD   NSX password, default "default"
  --port PORT           NSX API port
```

### On FortiGate Service Manager

```
$ ./vmxlab.py fortigate -h
usage: vmxlab.py fortigate [-h] --host HOST [--user USER]
                           [--password PASSWORD] [--port PORT]
                           {set-interface,create-dhcp-server,create-nsx-connector,nsx-install}
                           ...

positional arguments:
  {set-interface,create-dhcp-server,create-nsx-connector,nsx-install}
    set-interface       Configure the NIC parameters
    create-dhcp-server  Configure new DHCP server
    create-nsx-connector
                        Configure new NSX connector
    nsx-install         Install the NSX service

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           FortiGate hostname or IP
  --user USER           FortiGate super-admin user, default "admin"
  --password PASSWORD   Password, default empty
  --port PORT           FortiGate SSH port
```

## Modules

In the lib directory there are following modules providing procedures to communicate with different APIs

### ESXi.py and vCenter.py

Communication with (standalone) ESXi host or with VMware vCenter host. Both use VMware vSphere API implemented in Python by [pyVmomi](https://github.com/vmware/pyvmomi).

For ESXi it also contains functions to erase the saved MAC addresses. This is done over SSH.

### NSX.py

Very simple NSX REST API implementation using [Requests](http://docs.python-requests.org/en/master/) and [ElementTree](https://docs.python.org/2/library/xml.etree.elementtree.html) for parsing the responses.

### FortiGate.py

The simplest communication with FortiGate Service Manager over SSH using [Paramiko](http://www.paramiko.org/).
