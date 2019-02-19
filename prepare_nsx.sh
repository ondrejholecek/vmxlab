!/bin/bash

vmxlab="./vmxlab.py"
gparams="--verbose"

echo "============================================="
echo "=== Prepare the lab NSX for the first use ==="
echo "============================================="
echo
echo -n "Enter the vCenter's IP address: "
read vcenter
echo -n "Enter the NSX Manager's IP address: "
read nsx

echo
echo "========================================"
echo "=== Create synchronization portgroup ==="
echo "========================================"
echo -n "Enter VLAN ID for VMX synchronization network: "
read vlanid
echo "- Creating portgroup \"vmxsync\" on distributed switch \"lab\" with VLAN $vlanid"
$vmxlab $gparams vcenter --host $vcenter create-portgroup --name vmxsync --dvswitch lab --vlan $vlanid

echo
echo "======================================="
echo "=== Register NSX Manager to vCenter ==="
echo "======================================="
echo "- Getting vCenter thumbprint"
tp=`$vmxlab vcenter --host $vcenter thumbprint`
echo "- Registering NSX Manager to vCenter"
$vmxlab $gparams nsx --host $nsx register --host $vcenter  --thumbprint $tp
echo -n "Enter file containing NSX Manager license: "
read licfile
echo "- Installing and assigning NSX license"
$vmxlab $gparams vcenter --host $vcenter license --file $licfile --nsx --add

echo
echo "========================================"
echo "=== Deploy FortiGate Service Manager ==="
echo "========================================"
echo -n "Enter path to FortiGate Service Manager .ovf file: "
read svmovf
svmdir=`dirname $svmovf`
echo "- Deploying FortiGate Service Manager VM"
$vmxlab $gparams vcenter --host $vcenter deploy --name FortiGate-SVM --ovf $svmovf --disk $svmdir/fortios.vmdk --disk $svmdir/datadrive.vmdk --datastore shared --dnet "Agent Sync Network:lab:vmxsync" --snet "Management Network:VM Network" --start --prop mgmt_mode:DHCP
echo "Wait for FortiGate SVM to boot up and acquire IP address!"
echo -n "Enter IP address of FortiGate SVM: "
read svm

echo "- Configuring sync interface"
$vmxlab $gparams fortigate --host $svm set-interface --interface sync --ip 192.168.9.254 --netmask 255.255.255.0
echo "- Creating dhcp server"
$vmxlab $gparams fortigate --host $svm create-dhcp-server --interface sync --start 192.168.9.1 --end 192.168.9.99 --netmask 255.255.255.0 --gateway 192.168.9.254

echo -n "Enter the URL to FortiGate VMX .ovf file: "
read vmxurl
echo "- Configuring NSX Service"
$vmxlab $gparams fortigate --host $svm create-nsx-connector --nsx $nsx --vmx-url $vmxurl
echo "- Installing NSX Service"
$vmxlab $gparams fortigate --host $svm nsx-install

echo
echo "============================="
echo "=== Configure NSX Manager ==="
echo "============================="
echo "- Getting cluster ID"
cluster=`$vmxlab vcenter --host $vcenter show --cluster`
echo "- Preparing cluster for NSX"
$vmxlab $gparams nsx --host $nsx prepare --cluster $cluster
echo "- Getting portgroup ID of \"vmxsync\" on dvSwitch \"lab\""
portgroup=`$vmxlab vcenter --host $vcenter show --portgroup lab:vmxsync`
echo "- Getting datastore ID of \"shared\" datastore"
datastore=`$vmxlab vcenter --host $vcenter show --datastore shared`
echo "- Deploying agents for service \"labvmx\""
$vmxlab $gparams nsx --host $nsx deploy --cluster $cluster --datastore $datastore --portgroup $portgroup --service labvmx 
echo "- Creating a default Security Policy redirected to \"labvmx\" service and vdom \"nsx\""
$vmxlab $gparams nsx --host $nsx create-policy --name 'Default policy' --direction in --direction out --service labvmx --vdom nsx --logged

echo
echo "Done"
echo 
echo "Note: At this moment everything is prepared but no traffic is redirected to FortiGate VMX."
echo "      To redirect traffic, you need to create a Security Group and apply it to default Policy."
echo 
