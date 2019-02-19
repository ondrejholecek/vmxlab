
from VMwareCommon import VMwareCommon
from pyVmomi import vim
import time
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
import os
from VMwareNFCUpload import VMwareNFCUpload


class vCenter(VMwareCommon):

	def __init__(self, ip, user="administrator@vsphere.local", password="fortinet", api_port=443, ssh_port=22):
		self.ip       = ip
		self.user     = user
		self.password = password
		self.api_port = api_port
		self.ssh_port = ssh_port

		self.post_init()

	###
	### Folders
	###

	def get_datacenter(self, name=None):
		for child in self.si.RetrieveContent().rootFolder.childEntity:
			if type(child) == vim.Datacenter:
				if name == None: return child
				elif name == child.name: return child
		return None
	
	def create_datacenter(self, name):
		return self.si.RetrieveContent().rootFolder.CreateDatacenter(name)

	def get_cluster(self, dc, name=None):
		if dc == None: return None

		for child in dc.hostFolder.childEntity:
			if type(child) == vim.ClusterComputeResource:
				if name == None: return child
				elif name == child.name: return child
		return None

	def create_cluster(self, dc, name):
		cluster_spec = vim.ClusterConfigSpecEx()

		return dc.hostFolder.CreateClusterEx(name, cluster_spec)
	
	def get_host(self, cluster, name):
		if cluster == None: return None

		for host in cluster.host:
			if host.name == name: return host
		return None

	###
	### ESXi hosts
	###
	def get_hosts(self, cluster):
		hosts = {}
		for host in cluster.host:
			if type(host) != vim.HostSystem: continue
			c = host.summary.config
			hosts[c.name] = {
				'config': c,
				'ref'   : host,
			}
		return hosts
			
	def register_host(self, cluster, ip, thumbprint, user="root", password="fortinet", port=443):
		hc_spec = vim.HostConnectSpec(
			force         = False,
			hostName      = ip,
			password      = password,
			port          = port,
			sslThumbprint = thumbprint,
			userName      = user,
		)

		cluster.AddHost(hc_spec, asConnected=True)
	
	###
	### Licenses
	###
	def get_licenses(self):
		licenses = {}
		for lic in self.si.RetrieveContent().licenseManager.licenses:
			licenses[lic.licenseKey] = {
				'name'   : lic.name,
				'total'  : lic.total,
				'used'   : lic.used,
			}
		return licenses
	
	def add_license(self, key):
		r = self.si.RetrieveContent().licenseManager.AddLicense(licenseKey=key)
		if r.licenseKey == '': return False
		return True

	def assign_nsx_license(self, key):
		#print self.si.RetrieveContent().licenseManager.licenseAssignmentManager.QueryAssignedLicenses()
		#print self.si.RetrieveContent().extensionManager.extensionList
		#nsx_ext = self.si.RetrieveContent().extensionManager.FindExtension(extensionKey='com.vmware.vShieldManager')
		#if (nsx_ext == None) or (nsx_ext.description.label != 'NSX Manager'): return False
		r = self.si.RetrieveContent().licenseManager.licenseAssignmentManager.UpdateAssignedLicense(
			entity     = 'nsx-netsec',
			licenseKey = key,
		)
		if r.licenseKey == '': return False
		return True

	###
	### Networking
	###
	def create_dvswitch(self, dc, name, hosts):
		h = []
		for host, nic_name in hosts:
			h.append(vim.DistributedVirtualSwitchHostMemberConfigSpec(
				host      = host,
				backing   = vim.DistributedVirtualSwitchHostMemberPnicBacking(pnicSpec = [
					vim.DistributedVirtualSwitchHostMemberPnicSpec(pnicDevice = nic_name),
				]),
				operation = 'add',
			))

		task = dc.networkFolder.CreateDVS_Task(spec = vim.DVSCreateSpec(
				configSpec = vim.DVSConfigSpec(
					name = name,
					host = h,
				),
			),
		)

		return self.handle_task(task)

	def create_portgroup(self, dvswitch, name, vlanid):
		task = dvswitch.CreateDVPortgroup_Task(spec = vim.DVPortgroupConfigSpec(
			name = name,
			type = 'earlyBinding',
			defaultPortConfig = vim.VMwareDVSPortSetting(
				vlan = vim.VmwareDistributedVirtualSwitchVlanIdSpec(vlanId=vlanid),
			),
		))

		return self.handle_task(task)

	def get_dvswitch(self, dc, name):
		for dvs in dc.networkFolder.childEntity:
			if type(dvs) != vim.dvs.VmwareDistributedVirtualSwitch: continue
			if dvs.config.name == name: return dvs
		return None

	def get_portgroup(self, dvs, name):
		for pg in dvs.portgroup:
			if pg.config.name == name: return pg
		return None

	def get_network(self, dc, name):
		for net in dc.networkFolder.childEntity:
			if type(net) != vim.Network: continue
			if net.name == name: return net
		return None

	def extend_dvswitch(self, cluster, dvs, host, nic_name):
		spec = vim.DVSConfigSpec(
			configVersion = dvs.config.configVersion,
			name          = dvs.config.name,
			host = [
				vim.DistributedVirtualSwitchHostMemberConfigSpec(
					host      = host,
					operation = 'add',
					backing   = vim.DistributedVirtualSwitchHostMemberPnicBacking(
						pnicSpec = [ vim.DistributedVirtualSwitchHostMemberPnicSpec(
							pnicDevice = nic_name,
						) ],
					),
				),
			],
		)

		task = dvs.ReconfigureDvs_Task(spec)
		return self.handle_task(task)

	###
	### Tasks
	###
	def handle_task(self, task):
		while True:
			if task.info.state == 'success':
				break

			elif task.info.state == 'error':
				break

			else:
				time.sleep(1)

		if task.info.state == 'error':
			raise Exception("Error: %s" % (task.info.error.msg,))

		return task.info.result

	###
	### Datastores
	###
	def get_datastores(self, dc, shared_with=None):
		# get all possible datastores in dc
		datastores = {}
		for ds in dc.datastoreFolder.childEntity:
			#
			hosts = []
			for host in ds.host:
				hosts.append(host.key.summary.config.name)

			#
			if ds.summary.type in ('NFS', 'NFS41'):
				shared = True
			else:
				shared = False

			#
			datastores[ds.info.name] = {
				'hosts'  : hosts,
				'shared' : shared,
				'ref'    : ds,
			}
	
		if shared_with == None: return datastores

		# if shared_with is not None, remove the datastores not shared with all the specified hosts
		shared_datastores = {}
		for ds in datastores.keys():
			if not datastores[ds]['shared']: continue

			missing = False
			for h in shared_with:
				if h not in datastores[ds]['hosts']: missing = True

			if missing: continue

			shared_datastores[ds] = datastores[ds]

		return shared_datastores

	def get_datastore(self, dc, name):
		datastores = self.get_datastores(dc)
		if name in datastores: return datastores[name]['ref']
		else: return None

	###
	### VMs
	###
	def get_vm(self, dc, name):
		for vm in dc.vmFolder.childEntity:
			if type(vm) != vim.VirtualMachine: continue
			if vm.config.name == name: return vm
		return None

	def get_last_snapshot(self, vm):
		if vm.snapshot == None: return None
		return vm.snapshot.currentSnapshot

	def clone_vm(self, vm, folder, clones, start=False, new_snapshot="ifneeded"):

		snapshot = self.get_last_snapshot(vm)
		
		if (new_snapshot == True) or (snapshot == None and new_snapshot == "ifneeded"):
			task = vm.CreateSnapshot_Task("autosnaphot-%i" % (int(time.time()),), memory=False, quiesce=False)
			snapshot = self.handle_task(task)
		elif snapshot == None: 
			raise Exception("Snapshot is necessary but there is none")
	
		vms = []
		for clone in clones:
			task = vm.CloneVM_Task(folder, clone, spec=vim.VirtualMachineCloneSpec(
				location = vim.VirtualMachineRelocateSpec(
					pool         = vm.resourcePool,
					diskMoveType = 'createNewChildDiskBacking',
				),
				snapshot = snapshot, 
			))
			
			r = self.handle_task(task)
			if start: self.start_vm(r)
			vms.append(r)

		return vms

	def start_vm(self, vm):
		task = vm.PowerOnVM_Task()
		return self.handle_task(task)

	def deploy_vm_from_ovf(self, name, ovffile, diskfiles, resource_pool, datastore, folder, template=False, networks=None, snapshot=None, properties={}):
		f = open(ovffile, "rb")
		ovf = f.read()
		f.close()

		#
		if networks != None:
			network_mapping = []
			for (ovf_name, real_network) in networks:
				network_mapping.append( vim.OvfNetworkMapping(
					name = ovf_name,
					network = real_network,
				))

		else:
			network_mapping = None
			
		#
		propertyMapping = []
		for prop in properties.keys():
			propertyMapping.append(vim.KeyValue(key=prop, value=properties[prop]))
			
		#
		ispec = self.si.RetrieveContent().ovfManager.CreateImportSpec(
			ovfDescriptor = ovf,
			resourcePool  = resource_pool,
			datastore     = datastore,
			cisp          = vim.OvfCreateImportSpecParams(
				diskProvisioning = 'thin',
				entityName       = name,
				propertyMapping  = propertyMapping,
				networkMapping   = network_mapping,
			),
		)

		lease = resource_pool.ImportVApp(ispec.importSpec, folder)
		urlmap = {}

		while True:
			if lease.state == vim.HttpNfcLease.State.initializing:
				time.sleep(1)
				continue

			elif lease.state == vim.HttpNfcLease.State.ready:
				for disk_no in range(len(lease.info.deviceUrl)):
					remote = lease.info.deviceUrl[disk_no]
					local  = diskfiles[disk_no]
					urlmap[remote.url] = {
						'local_file': "%s" % (local,),
					}
				
				nfc = VMwareNFCUpload(urlmap, perc_callback=lease.HttpNfcLeaseProgress)
				nfc.upload_all()
				lease.HttpNfcLeaseComplete()

			elif lease.state == vim.HttpNfcLease.State.done:
				break

			else:
				break

		
		if lease.state == vim.HttpNfcLease.State.error:
			raise Exception("Unable to start deploying the VM:" + str(lease.error))

		# return info
		r = {}
		for diskfile in diskfiles:
			fullpath = "%s" % (diskfile,)

			r[diskfile] = {
				'status': 'error',
				'msg'   : 'unknown error'
			}

			for url in urlmap.keys():
				if fullpath == urlmap[url]['local_file']:
					r[diskfile]['msg'] = urlmap[url]['response']['msg']
					if urlmap[url]['response']['code'] in range(200, 300):
						r[diskfile]['status'] = 'ok'
					else:
						r[diskfile]['status'] = 'error'

		if snapshot != None:
			task = lease.info.entity.CreateSnapshot_Task(snapshot, memory=False, quiesce=False)
			snapshot = vcenter.handle_task(task)

		if template:
			lease.info.entity.MarkAsTemplate()

		return (lease.info.entity, r)
		

if __name__ == '__main__':
	# Yeah, the certificates are invalid, stop being a babysitter
	import requests
	from requests.packages.urllib3.exceptions import InsecureRequestWarning
	requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
	
	import ssl
	ssl._create_default_https_context = ssl._create_unverified_context
	context = ssl.create_default_context()
	context.check_hostname = False
	context.verify_mode = ssl.CERT_NONE

	vcenter = vCenter("1.2.3.4")
	print vcenter.get_thumbprint()

	dc = vcenter.get_datacenter()
	if dc == None:
		print "No datacenter found, creating 'datacenter'"
		dc = vcenter.create_datacenter("datacenter")
	else:
		print "Datacenter '%s' found" % (dc.name,)
	
	cluster = vcenter.get_cluster(dc)
	if cluster == None:
		print "No cluster found in datacenter '%s', creating 'cluster'" % (dc.name,)
		cluster = vcenter.create_cluster(dc, "cluster")
	else:
		print "Cluster '%s' found in datacenter '%s'" % (cluster.name, dc.name,)
	
	print "Cluster MOID is %s" % (cluster._GetMoId(),)

	hostsdata = vcenter.get_hosts(cluster)

	hosts = hostsdata.keys()
	print "Registered hosts (%i):" % (len(hosts),)
	for host in hosts: print "- %s" % (host,)

	print "Datastores shared with all hosts:"
	datastores = vcenter.get_datastores(dc, shared_with=hosts)
	for ds in datastores.keys():
		print "- %s : %s" % (ds, datastores[ds]['ref']._GetMoId(),)

	#vcenter.register_host(cluster, '192.168.1.108', 'b7:f2:9d:e5:6a:04:8c:73:e3:79:c6:c4:fb:36:41:35:23:5f:5c:92')
	#vcenter.register_host(cluster, '192.168.1.106', 'c6:18:87:42:79:8c:5d:a4:d0:ca:4a:6f:05:6c:a6:6c:d0:f9:a1:59')
	#print vcenter.get_licenses()
	#vcenter.add_license('XXXXX-XXXXX-XXXXX-XXXXX-XXXXX')
	#vcenter.assign_nsx_license('XXXXX-XXXXX-XXXXX-XXXXX-XXXXX')


	#dvs = vcenter.create_dvswitch(dc, "lab", hosts=[ (hostsdata[h]['ref'], 'vmnic1') for h in hostsdata.keys() ])
	#print dvs
	#print vcenter.create_portgroup(dvs, "vmxsync", 111)
	#print vcenter.create_portgroup(dvs, "shared-vlan-4", 4)

	#dvs = vcenter.get_dvswitch(dc, "lab")
	#net_sync = vcenter.get_portgroup(dvs, "vmxsync")
	##net_dhcp = vcenter.get_portgroup(dvs, "shared-vlan-4")
	#net_dhcp = vcenter.get_portgroup(dvs, "dhcp")
	#net_mgmt = vcenter.get_network(dc, "VM Network")

	#print "Sync network MOID is %s" % (net_sync._GetMoId(),)
	#(svm, diskinfo) = vcenter.deploy_vm_from_ovf('FortiGate-Service-Manager', '/var/www/html/ovf/svm/v6b0231', 'FortiGate-VMX-Service-Manager.ovf', ['fortios.vmdk', 'datadrive.vmdk'], cluster.resourcePool, vcenter.get_datastores(dc, shared_with=hosts).items()[0][1]['ref'], dc.vmFolder, networks=[('Agent Sync Network', net_sync), ('Management Network', net_mgmt)])
	#vcenter.start_vm(svm)
	
	#(linux, diskinfo) = vcenter.deploy_vm_from_ovf('debian-template', '/var/www/html/ovf/debian', 'debian-template.ovf', ['debian-template-1.vmdk',], cluster.resourcePool, vcenter.get_datastores(dc, shared_with=hosts).items()[0][1]['ref'], dc.vmFolder, networks=[('eth0', net_dhcp)], snapshot="initial_state")
	#(linux, diskinfo) = vcenter.deploy_vm_from_ovf('debian-template', '/Users/oho/ISO/debian/ovf', 'debian-template.ovf', ['debian-template-1.vmdk',], cluster.resourcePool, vcenter.get_datastores(dc).items()[0][1]['ref'], dc.vmFolder, networks=[('eth0', net_dhcp)], snapshot="initial_state")


	#template = vcenter.get_vm(dc, 'debian-template')
	#print vcenter.clone_vm(template, dc.vmFolder, ("Linux-A-1", "Linux-A-2", "Linux-B-1", "Linux-B-2"), start=True)
