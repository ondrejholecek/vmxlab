
from VMwareCommon import VMwareCommon
from pyVmomi import vim

class ESXi(VMwareCommon):

	def __init__(self, ip, user="root", password="fortinet", api_port=443, ssh_port=22):
		self.ip       = ip
		self.user     = user
		self.password = password
		self.api_port = api_port
		self.ssh_port = ssh_port

		self.post_init()

	###
	### services
	###
	def is_ssh_enabled(self):
		(policy, running) = self.is_service_enabled('TSM-SSH')
		if policy != 'on' or running != True: return False
		else: return True

	def enable_ssh(self):
		self.set_service_status('TSM-SSH', True)

	def disable_ssh(self):
		self.set_service_status('TSM-SSH', False)

	def is_service_enabled(self, service_name):
		for service in self.si.RetrieveContent().rootFolder.childEntity[0].hostFolder.childEntity[0].host[0].configManager.serviceSystem.serviceInfo.service:
			if service.key != service_name: continue
			else: return (service.policy, service.running)
		return (None, None)

	def set_service_status(self, service_name, enabled):
		serviceSystem = self.si.RetrieveContent().rootFolder.childEntity[0].hostFolder.childEntity[0].host[0].configManager.serviceSystem
		if enabled:
			serviceSystem.UpdateServicePolicy(id=service_name, policy='on')
			serviceSystem.StartService(service_name)
		else:
			serviceSystem.StopService(service_name)
			serviceSystem.UpdateServicePolicy(id=service_name, policy='off')
	
	###
	### datastores
	###
	def list_datastores(self):
		datastores = {}

		datastoreSystem = self.si.RetrieveContent().rootFolder.childEntity[0].hostFolder.childEntity[0].host[0].configManager.datastoreSystem
		for ds in datastoreSystem.datastore:
			summary = ds.summary
			datastores[summary.name] = {
				'shared'    : None,
				'capacity'  : summary.capacity,
				'accessible': summary.accessible,
				'type'      : summary.type,
			}

			if summary.type in ('NFS', 'NFS41'):
				datastores[summary.name]['shared'] = True
			else:
				datastores[summary.name]['shared'] = False

		return datastores

	def mount_nfs_datastore(self, name, host, path):
		nas_spec = vim.HostNasVolumeSpec(
			accessMode = 'readWrite',
			remoteHost = host,
			remotePath = path,
			type       = 'NFS',
			localPath  = name,
		)

		datastoreSystem = self.si.RetrieveContent().rootFolder.childEntity[0].hostFolder.childEntity[0].host[0].configManager.datastoreSystem
		ds = datastoreSystem.CreateNasDatastore(nas_spec)
		if ds == None: return None
		else: return ds.name
	
	def unmount_datastore(self, name):
		datastoreSystem = self.si.RetrieveContent().rootFolder.childEntity[0].hostFolder.childEntity[0].host[0].configManager.datastoreSystem
		for ds in datastoreSystem.datastore:
			if ds.name != name: continue
			datastoreSystem.RemoveDatastore(ds)
			return True
		return False
	
	def unmount_local_datastores(self):
		count = 0
		datastores = self.list_datastores()
		for ds in datastores:
			if not datastores[ds]['shared']:
				self.unmount_datastore(ds)
				count += 1
		return count

	def ssh_get_current_mac_phase(self):
		(stdout, stderr) = self.ssh_command('cat /store/oho_mac_phase')
		if len(stdout) == 0: return 0
		else: 
			try:
				return int(stdout)
			except:
				return 0

	def ssh_set_current_mac_phase(self, phase):
		(stdout, stderr) = self.ssh_command('echo %i >/store/oho_mac_phase' % (phase,))
		if len(stderr) != 0: return stderr
		return None
	
	def ssh_execute_mac_phase_1(self):
		(stdout, stderr) = self.ssh_command(r"""sed -i '/\/mac =/d' /etc/vmware/esx.conf""")
		if len(stderr) != 0: return "1/1:" + stderr
		(stdout, stderr) = self.ssh_command(r"""sed -i '/\/virtualMac =/d' /etc/vmware/esx.conf""")
		if len(stderr) != 0: return "1/2:" + stderr
		self.ssh_set_current_mac_phase(1)
		(stdout, stderr) = self.ssh_command(r"""reboot""")
		if len(stderr) != 0: return "1/3:" + stderr
		self.ssh_disconnect()
	
	def ssh_execute_mac_phase_2(self):
		(stdout, stderr) = self.ssh_command(r"""esxcfg-vmknic -l | grep ^vmk0 | head -1 | sed 's/^.*\s\(00:50:56:[0-9a-f]*:[0-9a-f]*:[0-9a-f]*\)\s.*$/\1/' >/tmp/current""")
		if len(stderr) != 0: return "1/1:" + stderr
		(stdout, stderr) = self.ssh_command(r"""cat /etc/vmware/esx.conf | grep '/net/pnic/child\[0000\]/mac =' | sed 's/^.* = \"\([0-9a-f:]*\)\"/\1/' >/tmp/first""")
		if len(stderr) != 0: return "1/2:" + stderr
		(stdout, stderr) = self.ssh_command(r"""sed -i "s/`cat /tmp/current`/`cat /tmp/first`/g" /etc/vmware/esx.conf""")
		if len(stderr) != 0: return "1/3:" + stderr
		self.ssh_set_current_mac_phase(2)
		(stdout, stderr) = self.ssh_command(r"""reboot""")
		if len(stderr) != 0: return "1/4:" + stderr
		self.ssh_disconnect()
	
	def ssh_execute_mac(self):
		if esxi.ssh_get_current_mac_phase() == 0:
			err = self.ssh_execute_mac_phase_1()
			if err != None: print err
			return 0
		elif esxi.ssh_get_current_mac_phase() == 1:
			err = self.ssh_execute_mac_phase_2()
			if err != None: print err
			return 1
		elif esxi.ssh_get_current_mac_phase() == 2:
			return 2
		else:
			return None

		


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

	esxi = ESXi("192.168.1.106")
	print esxi.get_thumbprint()
	#print esxi.is_ssh_enabled()
	#esxi.enable_ssh()
	#print esxi.is_ssh_enabled()

	#print esxi.list_datastores()
	#esxi.mount_nfs_datastore('test', '192.168.1.1', '/export')
	#print esxi.unmount_local_datastores()
	#print esxi.list_datastores()

	#esxi.ssh_connect()
	#print esxi.ssh_get_current_mac_phase()
	#esxi.ssh_execute_mac()
