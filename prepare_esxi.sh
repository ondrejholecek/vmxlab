#!/bin/bash

vmxlab="./vmxlab.py"
gparams="--verbose"

function wait_for_device {
	local ip=$1
	while true; do
		ping -W1 -n -c1 $ip >/dev/null 2>&1
		[ $? -eq 0 ] && break
		echo -n .
	done
}

echo "=============================================="
echo "=== Prepare the lab ESXi for the first use ==="
echo "=============================================="
echo
echo -n "Enter the initial IP address: "
read esxi
echo -n "- Waiting for IP to start responding: "
wait_for_device $esxi
echo

echo "- Enabling SSH"
$vmxlab $gparams esxi --host $esxi ssh --enable
echo "- Removing wrong MAC address - phase 1"
$vmxlab $gparams esxi --host $esxi erase-mac --phase 1
echo "Wait for device to reboot"
sleep 20

echo -n "Enter the new IP address: "
read esxi
echo -n "- Waiting for IP to start responding: "
wait_for_device $esxi
echo

echo "- Removing wrong MAC address - phase 2"
$vmxlab $gparams esxi --host $esxi erase-mac --phase 2
echo "Wait for device to reboot"
sleep 20

echo -n "Enter the final IP address: "
read esxi
echo -n "- Waiting for IP to start responding: "
wait_for_device $esxi
echo

echo "- Removing default small datastore"
$vmxlab $gparams esxi --host $esxi delete-datastore --locals

echo "- Done"
