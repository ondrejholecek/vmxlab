#!/bin/bash

vmxlab="./vmxlab.py"
gparams="--verbose"

echo "================================================="
echo "=== Prepare the lab vCenter for the first use ==="
echo "================================================="
echo
echo "Before continuing please make sure you can login to vCenter"
echo "over the WebUI on the standard HTTPs port 443."
echo
echo "This interface is not available immediatelly after deploying!"
echo "Please wait until it you can reach it!"
echo
echo -n "Enter the vCenter's IP address: "
read ip

echo "- Creating default datacenter"
$vmxlab $gparams vcenter --host $ip datacenter --create
echo "- Creating default cluster"
$vmxlab $gparams vcenter --host $ip cluster --create

while true; do
	echo -n "Enter IP address of one ESXi host (when finished keep empty): "
	read host
	[ "$host" = "" ] && break
	echo "- Getting certificate thumbprint for host $host"
	tp=`$vmxlab esxi --host $host thumbprint`
	echo "- Registering host $host to vCenter"
	$vmxlab $gparams vcenter --host $ip register --esxi $host --thumbprint $tp
done

echo "- Creating distributed switch \"lab\" with all current hosts NIC \"vmnic1\" attached"
$vmxlab $gparams vcenter --host $ip create-dvswitch --name lab --nic vmnic1 --all-hosts

echo -n "Enter NFS server IP: "
read nfsip
echo -n "Enter NFS path: "
read nfspath

for host in `$vmxlab vcenter --host $ip list-hosts | awk '{print $1}'`; do
	echo "- Mounting NFS datastore \"shared\" from $nfsip:$nfspath"
	$vmxlab $gparams esxi --host $host add-nfs-datastore --name shared --host $nfsip --path $nfspath
done

echo "- Done"
