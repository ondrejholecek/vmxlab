#!/bin/bash

vmxlab="./vmxlab.py"
gparams="--verbose"

echo "============================="
echo "=== Prepare test Linux VM ==="
echo "============================="
echo
echo -n "Enter the vCenter's IP address: "
read vcenter

echo -n "Enter the VLAN ID used as default for the test VM: "
read vlanid
portgroup="vlan-$vlanid"
echo "- Creating portgroup \"$portgroup\" on distributed switch \"lab\" with VLAN $vlanid"
$vmxlab $gparams vcenter --host $vcenter create-portgroup --name $portgroup --dvswitch lab --vlan $vlanid

echo -n "Enter the directory with Debian VM teplate files (\"debian-template.ovf\" and \"debian-template-1.vmdk\"): "
read dir
echo "- Deploying the template VM"
$vmxlab $gparams vcenter --host $vcenter deploy --name debian-template --ovf $dir/debian-template.ovf --disk $dir/debian-template-1.vmdk --datastore shared --dnet "VM Network:lab:$portgroup" 

while true; do
	echo -n "Enter the name of VM to clone (empty line when done): "
	read vm
	[ "$vm" == "" ] && break
	echo "- Cloning the template VM to $vm"
	$vmxlab $gparams vcenter --host $vcenter clone-vm --name "$vm" --source debian-template --start
done

echo "- Done"

