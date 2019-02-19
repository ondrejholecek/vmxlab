#!/usr/bin/env python2.7

import argparse
import sys
import json

from lib.ESXi import ESXi
from lib.vCenter import vCenter
from lib.NSX import NSX
from lib.FortiGate import FortiGate


parser = argparse.ArgumentParser(description='VMX lab scripts')
parser.add_argument('--verbose', default=False, action='store_true', help='Be verbose')
parser.add_argument('--check-certs', default=False, action='store_true', help='Valid SSL certificates, disabled by default')

subparsers = parser.add_subparsers(dest='section')
parser_esxi = subparsers.add_parser('esxi', help='ESXi related commands')
parser_esxi.add_argument('--host', required=True, help='ESXi hostname or IP')
parser_esxi.add_argument('--user', default='root', help='ESXi username, default "root"')
parser_esxi.add_argument('--password', default='fortinet', help='ESXi password, default "fortinet"')
parser_esxi.add_argument('--port', default=443, type=int, help='ESXi vSphere API port')
parser_esxi.add_argument('--sshport', default=22, type=int, help='ESXi ssh port')

esxi_subparsers = parser_esxi.add_subparsers(dest='action')
parser_esxi_ssh  = esxi_subparsers.add_parser('ssh', help='SSH service')
parser_esxi_ssh_action = parser_esxi_ssh.add_mutually_exclusive_group(required=True)
parser_esxi_ssh_action.add_argument('--status', action='store_true', help='Print current status')
parser_esxi_ssh_action.add_argument('--enable', action='store_true', help='Start the service')
parser_esxi_ssh_action.add_argument('--disable', action='store_true', help='Stop the service')
parser_esxi_thumbprint = esxi_subparsers.add_parser('thumbprint', help='Print SSL certificate thumbprint')
parser_esxi_erasemac   = esxi_subparsers.add_parser('erase-mac', help='Erase hardcoded MAC address')
parser_esxi_erasemac.add_argument('--phase', required=True, choices=['1', '2', '?'], help="Choose phase, 1 or 2, or ? to get the latest phase finished")
parser_esxi_listdatastores    = esxi_subparsers.add_parser('list-datastores', help='List all datastores')
parser_esxi_deletedatastores  = esxi_subparsers.add_parser('delete-datastore', help='Delete datastores')
parser_esxi_deletedatastores_a = parser_esxi_deletedatastores.add_mutually_exclusive_group(required=True)
parser_esxi_deletedatastores_a.add_argument('--locals', action='store_true', help='Delete all local datastores')
parser_esxi_deletedatastores  = esxi_subparsers.add_parser('add-nfs-datastore', help='Add NFS datastore')
parser_esxi_deletedatastores.add_argument('--name', required=True, dest='nfs_name', help='Datastore name')
parser_esxi_deletedatastores.add_argument('--host', required=True, dest='nfs_host', help='IP address of the NFS server')
parser_esxi_deletedatastores.add_argument('--path', required=True, dest='nfs_path', help='Path the NFS server')

parser_vcenter = subparsers.add_parser('vcenter', help='vCenter related commands')
parser_vcenter.add_argument('--host', required=True, help='vCenter hostname or IP')
parser_vcenter.add_argument('--user', default='administrator@vsphere.local', help='vCenter username, default "administrator@vsphere.local"')
parser_vcenter.add_argument('--password', default='fortinet', help='vCenter password, default "fortinet"')
parser_vcenter.add_argument('--port', default=443, type=int, help='vCenter vSphere API port')
parser_vcenter.add_argument('--datacenter', default='Datacenter', help='Datacenter name')
parser_vcenter.add_argument('--cluster', default='Cluster', help='Cluster name')

vcenter_subparsers = parser_vcenter.add_subparsers(dest='action')
parser_vcenter_datacenter = vcenter_subparsers.add_parser('datacenter', help='Datacenter management')
parser_vcenter_datacenter_action = parser_vcenter_datacenter.add_mutually_exclusive_group(required=True)
parser_vcenter_datacenter_action.add_argument('--create', action='store_true', help='Create datacenter')

parser_vcenter_cluster = vcenter_subparsers.add_parser('cluster', help='Cluster management')
parser_vcenter_cluster_action = parser_vcenter_cluster.add_mutually_exclusive_group(required=True)
parser_vcenter_cluster_action.add_argument('--create', action='store_true', help='Create cluster')

parser_vcenter_listhosts = vcenter_subparsers.add_parser('list-hosts', help='List all registered ESXi hosts')

parser_vcenter_license   = vcenter_subparsers.add_parser('license', help='License management')
parser_vcenter_license_source = parser_vcenter_license.add_mutually_exclusive_group(required=True)
parser_vcenter_license_source.add_argument('--key', dest='license_key', help='License key')
parser_vcenter_license_source.add_argument('--file', dest='license_file', help='License file')
parser_vcenter_license.add_argument('--add', dest='license_add', action='store_true', default=False, help='Add license to vCenter')
parser_vcenter_license.add_argument('--nsx', dest='license_nsx', action='store_true', default=False, help='Assign license to NSX Manager')

parser_vcenter_thumbprint = vcenter_subparsers.add_parser('thumbprint', help='Show vCenter certificate thumbprint')

parser_vcenter_register   = vcenter_subparsers.add_parser('register', help='Register ESXi server')
parser_vcenter_register.add_argument('--esxi', required=True, help='Hostname of IP or ESXi host')
parser_vcenter_register.add_argument('--thumbprint', required=True, help='Thumbprint of ESXi host SSL certificate')
parser_vcenter_register.add_argument('--user', dest='esxi_user', default='root', help='Admin user on ESXi host')
parser_vcenter_register.add_argument('--password', dest='esxi_password', default='fortinet', help='Admin password on ESXi host')
parser_vcenter_register.add_argument('--port', dest='esxi_port', type=int, default=443, help='API port on ESXi host')

parser_vcenter_deploy   = vcenter_subparsers.add_parser('deploy', help='Deploy VM from OVF')
parser_vcenter_deploy.add_argument('--name', dest='deploy_name', required=True, help='Name of the new VM')
parser_vcenter_deploy.add_argument('--ovf', dest='deploy_ovf', required=True, help='Path to the OVF file')
parser_vcenter_deploy.add_argument('--disk', dest='deploy_disk', action="append", required=True, help='Disk(s) path (in the right order)')
parser_vcenter_deploy.add_argument('--datastore', dest='deploy_datastore', required=True, help='Datastore to create VM on')
parser_vcenter_deploy.add_argument('--dnet', dest='deploy_dnet', action="append", default=[], help='Network(s) on distributed vSwitch')
parser_vcenter_deploy.add_argument('--snet', dest='deploy_snet', action="append", default=[], help='Network(s) on standard vSwitch')
parser_vcenter_deploy.add_argument('--start', dest='deploy_start', action="store_true", default=False, help='Start VM after deployment')
parser_vcenter_deploy.add_argument('--prop', dest='deploy_prop', action="append", default=[], help='VApp properties (format "name:value")')

parser_vcenter_createpg = vcenter_subparsers.add_parser('create-portgroup', help='Create portgroup')
parser_vcenter_createpg.add_argument('--name', dest='dvswitch_pgname', required=True, help='Name of the portgroup')
parser_vcenter_createpg.add_argument('--dvswitch', dest='dvswitch_name', required=True, help='Name of the dvSwitch')
parser_vcenter_createpg.add_argument('--vlan', dest='dvswitch_vlanid', type=int, required=True, help='VLAN ID')

parser_vcenter_createdvswitch = vcenter_subparsers.add_parser('create-dvswitch', help='Create dvSwitch')
parser_vcenter_createdvswitch.add_argument('--name', dest='dvswitch_name', required=True, help='Name of the dvSwitch')
parser_vcenter_createdvswitch.add_argument('--nic', dest='dvswitch_nic', required=True, help='NIC name to connect as uplink')
parser_vcenter_createdvswitch_target = parser_vcenter_createdvswitch.add_mutually_exclusive_group(required=True)
parser_vcenter_createdvswitch_target.add_argument('--all-hosts', dest='dvswitch_allhosts', action='store_true', help='Create on all ESXi hosts')
parser_vcenter_createdvswitch_target.add_argument('--host', dest='dvswitch_host', action='append', default=[], help='Create on specified ESXi hosts')

parser_vcenter_extenddvswitch = vcenter_subparsers.add_parser('extend-dvswitch', help='Extend dvSwitch to the ESXi host')
parser_vcenter_extenddvswitch.add_argument('--name', dest='dvswitch_name', required=True, help='Name of the dvSwitch')
parser_vcenter_extenddvswitch.add_argument('--host', dest='dvswitch_host', required=True, help='Host to extend to')
parser_vcenter_extenddvswitch.add_argument('--nic', dest='dvswitch_nic', required=True, help='NIC name to connect as uplink')

parser_vcenter_clonevm = vcenter_subparsers.add_parser('clone-vm', help='Light clone VM')
parser_vcenter_clonevm.add_argument('--source', dest='clone_source', required=True, help='Name of the source VM')
parser_vcenter_clonevm.add_argument('--start', dest='clone_start', action='store_true', default=False, help='Start the new VM')
parser_vcenter_clonevm.add_argument('--name', dest='clone_name', action='append', required=True, help='Name of the new VM')

parser_vcenter_show = vcenter_subparsers.add_parser('show', help='Show MOIDs for various objects')
parser_vcenter_show.add_argument('--datacenter', dest='show_datacenter', action='store_true', default=False, help='Show datacenter ID')
parser_vcenter_show.add_argument('--cluster', dest='show_cluster', action='store_true', default=False, help='Show cluster ID')
parser_vcenter_show.add_argument('--portgroup', dest='show_portgroup', action='append', default=[], help='Show portgroup ID (format "dvswitch:pgname")')
parser_vcenter_show.add_argument('--datastore', dest='show_datastore', action='append', default=[], help='Show datastore ID')

parser_nsx = subparsers.add_parser('nsx', help='NSX Manager related commands')
parser_nsx.add_argument('--host', required=True, help='NSX hostname or IP')
parser_nsx.add_argument('--user', default='admin', help='NSX user, default "admin"')
parser_nsx.add_argument('--password', default='default', help='NSX password, default "default"')
parser_nsx.add_argument('--port', default=443, type=int, help='NSX API port')

nsx_subparsers = parser_nsx.add_subparsers(dest='action')

parser_nsx_createpolicy = nsx_subparsers.add_parser('create-policy', help='Create Security Policy')
parser_nsx_createpolicy.add_argument('--name', dest='createpolicy_name', required=True, help='Name of the new policy')
parser_nsx_createpolicy.add_argument('--direction', dest='createpolicy_direction', choices=['in', 'out', 'intra'], required=True, action='append', help='Direction of the policy, can be "in", "out" and "intra"')
parser_nsx_createpolicy.add_argument('--service', dest='createpolicy_service', required=True, help='VMX service name')
parser_nsx_createpolicy.add_argument('--vdom', dest='createpolicy_vdom', default='nsx', help='VMX VDOM name')
parser_nsx_createpolicy.add_argument('--logged', dest='createpolicy_logged', action='store_true', default=False, help='Enable logging')

parser_nsx_savepolicy = nsx_subparsers.add_parser('save-policy', help='Save Security Policies')
parser_nsx_savepolicy.add_argument('--file', dest='savepolicy_file', default=None, help='File name to save the data to, default stdout')
parser_nsx_savepolicy_action = parser_nsx_savepolicy.add_mutually_exclusive_group(required=True)
parser_nsx_savepolicy_action.add_argument('--all', dest='savepolicy_all', action='store_true', default=False, help='Save all visible policies')
parser_nsx_savepolicy_action.add_argument('--name', dest='savepolicy_name', action='append', default=None, help='Policy name to save')

parser_nsx_deletepolicy = nsx_subparsers.add_parser('delete-policy', help='Delete Security Policy')
parser_nsx_deletepolicy_action = parser_nsx_deletepolicy.add_mutually_exclusive_group(required=True)
parser_nsx_deletepolicy_action.add_argument('--all', dest='deletepolicy_all', action='store_true', default=False, help='Delete all visible policies')
parser_nsx_deletepolicy_action.add_argument('--name', dest='deletepolicy_name', action='append', default=None, help='Policy name to delete')

parser_nsx_restorepolicy = nsx_subparsers.add_parser('restore-policy', help='Restore Security Policy')
parser_nsx_restorepolicy.add_argument('--file', dest='restorepolicy_file', required=True, help='File with saved policies')
parser_nsx_restorepolicy_action = parser_nsx_restorepolicy.add_mutually_exclusive_group(required=True)
parser_nsx_restorepolicy_action.add_argument('--all', dest='restorepolicy_all', action='store_true', default=False, help='Restore all policies')
parser_nsx_restorepolicy_action.add_argument('--name', dest='restorepolicy_name', action='append', default=None, help='Policy name to restore')

parser_nsx_register = nsx_subparsers.add_parser('register', help='Register to vCenter')
parser_nsx_register.add_argument('--host', required=True, dest='register_host', help='vCenter hostname or IP')
parser_nsx_register.add_argument('--thumbprint', required=True, dest='register_thumbprint', help='vCenter ceritificate thumprint')
parser_nsx_register.add_argument('--user', default='administrator@vsphere.local', dest='register_user', help='vCenter admin username')
parser_nsx_register.add_argument('--password', default='fortinet', dest='register_password', help='vCenter admin password')

parser_nsx_prepare = nsx_subparsers.add_parser('prepare', help='Prepare ESXi hosts for NSX')
parser_nsx_prepare.add_argument('--cluster', required=True, dest='prepare_cluster', help='Cluster ID')

parser_nsx_deploy = nsx_subparsers.add_parser('deploy', help='Deploy NSX service')
parser_nsx_deploy.add_argument('--cluster', required=True, dest='deploy_cluster', help='Cluster ID')
parser_nsx_deploy.add_argument('--datastore', required=True, dest='deploy_datastore', help='Datastore ID')
parser_nsx_deploy.add_argument('--portgroup', required=True, dest='deploy_portgroup', help='Portgroup ID')
parser_nsx_deploy.add_argument('--service', required=True, dest='deploy_service', help='Service name')

parser_nsx_undeploy = nsx_subparsers.add_parser('undeploy', help='Delete NSX service')
parser_nsx_undeploy.add_argument('--cluster', required=True, dest='undeploy_cluster', help='Cluster ID')
parser_nsx_undeploy.add_argument('--service', required=True, dest='undeploy_service', help='Service name')


parser_fortigate = subparsers.add_parser('fortigate', help='FortiGate related commands')
parser_fortigate.add_argument('--host', required=True, help='FortiGate hostname or IP')
parser_fortigate.add_argument('--user', default='admin', help='FortiGate super-admin user, default "admin"')
parser_fortigate.add_argument('--password', default='', help='Password, default empty')
parser_fortigate.add_argument('--port', default=22, type=int, help='FortiGate SSH port')

fortigate_subparsers = parser_fortigate.add_subparsers(dest='action')
parser_fortigate_setiface = fortigate_subparsers.add_parser('set-interface', help='Configure the NIC parameters')
parser_fortigate_setiface.add_argument('--interface', dest='setif_interface', required=True, help='Interface name')
parser_fortigate_setiface.add_argument('--ip', dest='setif_ip', required=True, help='IP address without netmask')
parser_fortigate_setiface.add_argument('--netmask', dest='setif_netmask', required=True, help='Netmask in dotted format')
parser_fortigate_setiface.add_argument('--allow', dest='setif_allow', action='append', default=['ping', 'ssh', 'https'], help='Management protocols to allow')

parser_fortigate_cdhcp = fortigate_subparsers.add_parser('create-dhcp-server', help='Configure new DHCP server')
parser_fortigate_cdhcp.add_argument('--interface', dest='cdhcp_interface', required=True, help='Interface name')
parser_fortigate_cdhcp.add_argument('--start', dest='cdhcp_start', required=True, help='First IP to assign')
parser_fortigate_cdhcp.add_argument('--end', dest='cdhcp_end', required=True, help='Last IP to assign')
parser_fortigate_cdhcp.add_argument('--netmask', dest='cdhcp_netmask', required=True, help='Netmask in dotted format')
parser_fortigate_cdhcp.add_argument('--gateway', dest='cdhcp_gateway', required=True, help='Default gateway')

parser_fortigate_nsxc = fortigate_subparsers.add_parser('create-nsx-connector', help='Configure new NSX connector')
parser_fortigate_nsxc.add_argument('--nsx', dest='nsxc_nsx', required=True, help='NSX Manager IP or hostname')
parser_fortigate_nsxc.add_argument('--vmx-url', dest='nsxc_vmx_url', required=True, help='URL to FortiGate VMX .ovf file')
parser_fortigate_nsxc.add_argument('--service', dest='nsxc_service', default='labvmx', help='NSX service name')
parser_fortigate_nsxc.add_argument('--rest-password', dest='nsxc_rest_password', default='fortirest', help='NSX callback password')
parser_fortigate_nsxc.add_argument('--nsx-user', dest='nsxc_nsx_user', default='admin', help='NSX Manager user')
parser_fortigate_nsxc.add_argument('--nsx-password', dest='nsxc_nsx_password', default='default', help='NSX Manager password')

parser_fortigate_nsxservice = fortigate_subparsers.add_parser('nsx-install', help='Install the NSX service')

args = parser.parse_args()
#print args

if not args.check_certs:
	import requests
	from requests.packages.urllib3.exceptions import InsecureRequestWarning
	requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
	import ssl
	ssl._create_default_https_context = ssl._create_unverified_context
	context = ssl.create_default_context()
	context.check_hostname = False
	context.verify_mode = ssl.CERT_NONE
	

if args.section == 'esxi':
	esxi = ESXi(ip=args.host, user=args.user, password=args.password, api_port=args.port, ssh_port=args.sshport)
	if args.action == 'ssh':
		if args.status:
			s = esxi.is_ssh_enabled()
			if args.verbose: print "Current SSH service status on host %s:" % (args.host,),
			if s: print "enabled"
			else: print "disabled"

		elif args.enable:
			esxi.enable_ssh()
			if args.verbose: print "SSH enabled on ESXi host %s" % (args.host,)

		elif args.disable:
			esxi.disable_ssh()
			if args.verbose: print "SSH disabled on ESXi host %s" % (args.host,)

	elif args.action == 'thumbprint':
		thumbprint = esxi.get_thumbprint()
		if args.verbose: print "The ESXi SSL certificate thumbprint on %s is" % (args.host,),
		print thumbprint

	elif args.action == 'erase-mac':
		if args.phase == '1':
			err = esxi.ssh_execute_mac_phase_1()
		elif args.phase == '2':
			err = esxi.ssh_execute_mac_phase_2()
		elif args.phase == '?':
			phase = esxi.ssh_get_current_mac_phase()
			if args.verbose: print "The latest MAC removal phase finished on %s is" % (args.host,),
			print phase
	
	elif args.action == 'list-datastores':
		ds = esxi.list_datastores()
		for name in ds.keys():
			shared = 'no'
			if ds[name]['shared']: shared = 'yes'
			accessible = 'no'
			if ds[name]['accessible']: accessible = 'yes'
			if args.verbose:
				print "| %-16s | %-8s | %8s | %-3s | %-3s |" % ('Name', 'Type', 'Size', 'Accessible', 'Shared',)
				print "| %-16s | %-8s | %5.1f GB | %10s | %6s |" % (name, ds[name]['type'], float(ds[name]['capacity'])/1024/1024/1024, accessible, shared,)
			else:
				print "%s %s %i %s %s" % (name, ds[name]['type'], ds[name]['capacity'], accessible, shared,)

	elif args.action == 'delete-datastore':
		if args.locals:
			ds = esxi.list_datastores()
			for name in ds.keys():
				if not ds[name]['shared']:
					if args.verbose: print 'Deleting local datastore "%s"' % (name,)
					esxi.unmount_datastore(name)

	elif args.action == 'add-nfs-datastore':
		ds = esxi.mount_nfs_datastore(args.nfs_name, args.nfs_host, args.nfs_path)
		if ds == None:
			print >>sys.stderr, 'Error: cannot create NFS datastore from %s:%s' % (args.nfs_host, args.nfs_path,)
			sys.exit(1)
		if args.verbose: print 'Created NFS datastore "%s"' % (ds,)

elif args.section == 'vcenter':
	vcenter = vCenter(ip=args.host, user=args.user, password=args.password, api_port=args.port)

	if args.action == 'datacenter':
		if args.create:
			if args.verbose: print 'Creating datacenter "%s" on vCenter host %s' % (args.datacenter, args.host,)
			vcenter.create_datacenter(args.datacenter)

	datacenter = vcenter.get_datacenter(args.datacenter)
	if datacenter == None:
		print >>sys.stderr, 'Error: no such datacenter "%s"' % (args.datacenter,)
		sys.exit(1)

	if args.action == 'cluster':
		if args.create:
			if args.verbose: print 'Creating cluster "%s" on vCenter host %s' % (args.cluster, args.host,)
			vcenter.create_cluster(datacenter, args.cluster)

	cluster = vcenter.get_cluster(datacenter, args.cluster)

	if args.action == 'register':
		if args.verbose: print 'Registering ESXi host %s to vCenter %s' % (args.esxi, args.host,)
		vcenter.register_host(cluster, args.esxi, args.thumbprint, args.esxi_user, args.esxi_password, args.esxi_port)

	elif args.action == 'thumbprint':
		thumbprint = vcenter.get_thumbprint()
		if args.verbose: print "The vCenter SSL certificate thumbprint on %s is" % (args.host,),
		print thumbprint
	
	elif args.action == 'create-dvswitch':
		hostsdata = vcenter.get_hosts(cluster)
		use_hosts = []
		if args.dvswitch_allhosts:
			use_hosts = [ (hostsdata[h]['ref'], args.dvswitch_nic) for h in hostsdata.keys() ]
		else:
			for host in args.dvswitch_host:
				if host not in hostsdata.keys():
					print >>sys.stderr, 'Error: no such ESXi host "%s"' % (host,)
					sys.exit(1)
				else:
					use_hosts.append( (hostsdata[host]['ref'], args.dvswitch_nic) )

		if args.verbose: print 'Creating dvSwitch "%s"' % (args.dvswitch_name,)
		dvs = vcenter.create_dvswitch(datacenter, args.dvswitch_name, use_hosts)
			
	elif args.action == 'create-portgroup':
		dvs = vcenter.get_dvswitch(datacenter, args.dvswitch_name)
		if dvs == None:
			print >>sys.stderr, 'Error: no such dvSwitch "%s"' % (args.dvswitch_name,)
			sys.exit(1)

		net = vcenter.create_portgroup(dvs, args.dvswitch_pgname, args.dvswitch_vlanid)
		if args.verbose: print 'Created portgroup "%s"' % (net.name,)


	elif args.action == 'extend-dvswitch':
		dvs = vcenter.get_dvswitch(datacenter, args.dvswitch_name)
		if dvs == None:
			print >>sys.stderr, 'Error: no such dvSwitch name "%s" on vCenter %s' % (args.dvswitch_name, args.host,)
			sys.exit(1)

		host = vcenter.get_host(cluster, args.dvswitch_host)
		if host == None:
			print >>sys.stderr, 'Error: no such ESXi host name "%s" on vCenter %s' % (args.dvswitch_host, args.host,)
			sys.exit(1)

		vcenter.extend_dvswitch(cluster, dvs, host, args.dvswitch_nic)

	elif args.action == 'clone-vm':
		source = vcenter.get_vm(datacenter, args.clone_source)
		if source == None:
			print >>sys.stderr, 'Error: no such source VM "%s"' % (args.clone_vm,)
			sys.exit(1)

		vms = vcenter.clone_vm(source, datacenter.vmFolder, args.clone_name, start=args.clone_start, new_snapshot="ifneeded")
		if vms == None or len(vms) == 0:
			print >>sys.stderr, 'Error: cannot create VM'
			sys.exit(1)

		for vm in vms:
			if args.verbose: print 'Created VM "%s"' % (vm.name,)

	elif args.action == 'list-hosts':
		allhosts = vcenter.get_hosts(cluster)

		for host in allhosts.keys():
			if args.verbose: print 'Host "%s" has MOID "%s"' % (host, allhosts[host]['ref']._GetMoId(),)
			else: print "%s %s" % (host, allhosts[host]['ref']._GetMoId(),)

	elif args.action == 'deploy':
		ds = vcenter.get_datastore(datacenter, args.deploy_datastore)
		if ds == None:
			print >>sys.stderr, 'Error: no such datastore "%s"' % (args.deploy_datastore,)
			sys.exit(1)

		networks = []
		for n in args.deploy_dnet:
			tmp = n.split(':', 3)
			if len(tmp) != 3:
				print >>sys.stderr, 'Error: distributed network must be in the format "OVFname:dvSwitch:portgroup"'
				sys.exit(1)

			dvs = vcenter.get_dvswitch(datacenter, tmp[1])
			if dvs == None:
				print >>sys.stderr, 'Error: no such dvSwitch "%s"' % (tmp[1],)
				sys.exit(1)

			pg = vcenter.get_portgroup(dvs, tmp[2])
			if pg == None:
				print >>sys.stderr, 'Error: no such portgroup "%s" on dvSwitch "%s"' % (tmp[2], dvs.name,)
				sys.exit(1)

			networks.append( (tmp[0], pg) )

		for n in args.deploy_snet:
			tmp = n.split(':', 2)
			if len(tmp) != 2:
				print >>sys.stderr, 'Error: simple network must be in the format "OVFname:network"'
				sys.exit(1)

			network = vcenter.get_network(datacenter, tmp[1])
			if network == None:
				print >>sys.stderr, 'Error: no such network "%s"' % (tmp[1],)
				sys.exit(1)

			networks.append( (tmp[0], network) )

		properties = {}
		for p in args.deploy_prop:
			tmp = p.split(':', 2)
			if len(tmp) != 2:
				print >>sys.stderr, 'Error: property must be in the format "name:value"'
				sys.exit(1)

			properties[tmp[0]] = tmp[1]

		(svm, diskinfo) = vcenter.deploy_vm_from_ovf(args.deploy_name, args.deploy_ovf, args.deploy_disk, cluster.resourcePool, ds, datacenter.vmFolder, networks=networks, properties=properties)
		if svm == None:
			print >>sys.stderr, 'Error: unable to deploy VM'
			sys.exit(1)
		else:
			if args.verbose: print 'Deployed VM "%s"' % (svm.name,)

		if args.deploy_start:
			vcenter.start_vm(svm)
			if args.verbose: print 'Started VM "%s"' % (svm.name,)

	elif args.action == 'license':
		key = None
		if args.license_key != None: key = args.license_key
		elif args.license_file != None:
			with open(args.license_file, "r") as f: 
				key = f.read().strip()

		acted = False

		if args.license_add:
			if args.verbose: print "Adding license key to vCenter"
			if not vcenter.add_license(key):
				print >>sys.stderr, "Error: invalid license"
				sys.exit(1)
			acted = True

		if args.license_nsx:
			if args.verbose: print "Assigning license key to NSX Manager"
			if not vcenter.assign_nsx_license(key):
				print >>sys.stderr, "Error: invalid license"
				sys.exit(1)
			acted = True

		if not acted:
			print >>sys.stderr, "Error: no license action performed"
			sys.exit(1)


	elif args.action == 'show':
		if args.show_datacenter:
			if args.verbose: print 'Datacenter "%s":' % (datacenter.name,),
			print datacenter._GetMoId()

		if args.show_cluster:
			if args.verbose: print 'Cluster "%s":' % (cluster.name,),
			print cluster._GetMoId()
		
		for dvswitchpg in args.show_portgroup:
			tmp = dvswitchpg.split(':', 2)
			if len(tmp) != 2: 
				print >>sys.stderr, "Portgroup name must be in the format of 'dvswitch:portgroup'"
				sys.exit(1)
			(dvswitch_name, pg_name) = tmp
			
			dvs = vcenter.get_dvswitch(datacenter, dvswitch_name)
			if dvs == None: 
				print >>sys.stderr, 'Error: no such dvSwitch "%s"' % (dvswitch_name)
				sys.exit(1)

			net = vcenter.get_portgroup(dvs, pg_name)
			if net == None:
				print >>sys.stderr, 'Error: no such portgroup "%s"' % (pg_name)
				sys.exit(1)

			if args.verbose: print 'Portgroup "%s" on dvSwitch "%s":' % (net.name, dvs.name,),
			print net._GetMoId()

		for ds_name in args.show_datastore:
			ds = vcenter.get_datastore(datacenter, ds_name)	
			if ds == None:
				print >>sys.stderr, 'Error: no such datastore "%s"' % (ds_name,)
				sys.exit(1)

			if args.verbose: print 'Datastore "%s":' % (ds.name,),
			print ds._GetMoId()

elif args.section == 'nsx':
	nsx = NSX(ip=args.host, user=args.user, password=args.password, api_port=args.port)

	if args.action == 'create-policy':
		service = nsx.get_services(args.createpolicy_service)
		if service == None:
			print >>sys.stderr, 'Error: no such service "%s"' % (args.createpolicy_service,)
			sys.exit(1)
		
		service_profile = None
		for profile in service['profiles']:
			if profile['name'] == "%s_%s" % (args.createpolicy_service, args.createpolicy_vdom,):
				service_profile = profile['profileId']
				break
		if service_profile == None:
			print >>sys.stderr, 'Error: service "%s" does not have profile for VDOM "%s"' % (args.createpolicy_service, args.createpolicy_vdom,)
			sys.exit(1)
	
		if args.createpolicy_logged:
			logged = 'true'
		else:
			logged = 'false'
	
		rules = []
		for direction in args.createpolicy_direction:
			if direction == 'in':
				rules.append({
					'name'        : 'from outside',
					'description' : 'any -> protected VM',
					'direction'   : 'inbound',
					'logged'      : logged,
					'enabled'     : 'true',
					'service'     : service_profile,
				})

			elif direction == 'out':
				rules.append({
					'name'        : 'from protected VM',
					'description' : 'protected VM -> any',
					'direction'   : 'outbound',
					'logged'      : logged,
					'enabled'     : 'true',
					'service'     : service_profile,
				})

			elif direction == 'intra':
				rules.append({
					'name'        : 'between protected VMs',
					'description' : 'protected VM -> protected VM',
					'direction'   : 'intra',
					'logged'      : logged,
					'enabled'     : 'true',
					'service'     : service_profile,
				})

		nsx.create_security_policy(args.createpolicy_name, rules)
		if args.verbose: print 'Created Security Policy "%s"' % (args.createpolicy_name,)
		
	elif args.action == 'save-policy':
		policies = nsx.get_all_policies(no_dynamic=True)
		save = []
		for policy in policies:
			if args.savepolicy_name != None and policy['name'] not in args.savepolicy_name: continue
			if args.verbose: print 'Saving policy "%s"' % (policy['name'],)
			save.append(policy)

		out = json.dumps(save, indent=4)+"\n"

		if args.savepolicy_file == None:
			sys.stdout.write(out)
		else:
			with open(args.savepolicy_file, "w") as f:
				f.write(out)

	elif args.action == 'delete-policy':
		for policy in nsx.get_all_policies():
			if args.deletepolicy_name != None and policy['name'] not in args.deletepolicy_name: continue
			if args.verbose: print 'Deleting policy "%s"' % (policy['name'],)
			nsx.delete_policy(policy['id'])

	elif args.action == 'restore-policy':
		policies = json.load(open(args.restorepolicy_file, "r"))
		for policy in policies:
			if args.restorepolicy_name != None and policy['name'] not in args.restorepolicy_name: continue
			if args.verbose: print 'Restoring policy "%s"' % (policy['name'],)
			nsx.restore_policy(policy)
	
	elif args.action == 'register':
		nsx.register_to_vcenter(args.register_host, args.register_thumbprint, args.register_user, args.register_password)

	elif args.action == 'prepare':
		jobid = nsx.host_preparation(args.prepare_cluster)
		nsx.wait_for_job(jobid)
	
	elif args.action == 'deploy':
		service = nsx.get_services(args.deploy_service)
		if service == None:
			print >>sys.stderr, 'Error: no such service "%s"' % (service,)
			sys.exit(1)

		jobid = nsx.service_deploy(args.deploy_cluster, args.deploy_datastore, args.deploy_portgroup, service['serviceId'])
		nsx.wait_for_job(jobid)
	
	elif args.action == 'undeploy':
		service = nsx.get_services(args.undeploy_service)
		if service == None:
			print >>sys.stderr, 'Error: no such service "%s"' % (service,)
			sys.exit(1)

		jobid = nsx.service_delete(args.undeploy_cluster, service['serviceId'])
		nsx.wait_for_job(jobid)

elif args.section == 'fortigate':
	fgt = FortiGate(ip=args.host, user=args.user, password=args.password, ssh_port=args.port)

	if args.action == 'set-interface':
		fgt.set_static_ip(args.setif_interface, args.setif_ip, args.setif_netmask, " ".join(args.setif_allow))

	elif args.action == 'create-dhcp-server':
		fgt.create_dhcp_server(args.cdhcp_interface, args.cdhcp_start, args.cdhcp_end, args.cdhcp_netmask, args.cdhcp_gateway) 

	elif args.action == 'create-nsx-connector':
		fgt.create_nsx_connector(args.nsxc_nsx, args.nsxc_vmx_url, args.nsxc_service, args.nsxc_rest_password, args.nsxc_nsx_user, args.nsxc_nsx_password)

	elif args.action == 'nsx-install':
		fgt.install_nsx_service()
