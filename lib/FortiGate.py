import paramiko

class FortiGate:
	STATUS_OFFLINE = "offline"
	STATUS_ONLINE  = "online"

	def __init__(self, ip, user="admin", password="", ssh_port=22):
		self.ip       = ip
		self.user     = user
		self.password = password
		self.ssh_port = ssh_port

		self.ssh_status   = self.STATUS_OFFLINE
		self.ssh          = None
	
	###
	### direct SSH access
	###

	def ssh_connect(self):
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		client.connect(self.ip, port=self.ssh_port, username=self.user, password=self.password)

		self.ssh        = client
		self.ssh_status = self.STATUS_ONLINE
	
	def ssh_disconnect(self):
		if self.ssh != None and self.ssh_status != self.STATUS_OFFLINE:
			self.ssh.close()

		self.ssh        = None
		self.ssh_status = self.STATUS_OFFLINE

	def ssh_command(self, command):
		if self.ssh_status != self.STATUS_ONLINE:
			self.ssh_connect()

		stdin, stdout, stderr = self.ssh.exec_command(command)
		return (stdout.read(), stderr.read())
	
	###
	### User functions
	###
	def set_static_ip(self, iface, ip, mask, allowaccess="ping"):
		cmd = """
			config global
				config system interface
					edit %s
						set mode static
						set ip %s %s
						set allowaccess %s
					next
				end
			end
		""" % (iface, ip, mask, allowaccess,)
		self.ssh_command(cmd)

	def create_dhcp_server(self, iface, ip_start, ip_end, netmask, gateway):
		cmd = """
			config vdom
				edit root
					config system dhcp server
						edit 1
							set dns-service default
							set default-gateway %s
							set netmask %s
							set interface "%s"
							config ip-range
								edit 1
									set start-ip %s
									set end-ip %s
								next
							end
						next
					end
				next
			end
		""" % (gateway, netmask, iface, ip_start, ip_end,)
		self.ssh_command(cmd)

	def create_nsx_connector(self, ip, vmx_url, service_name='labvmx', rest_password="fortirest", user='admin', password='default'):
		cmd = """
			config global
				config system sdn-connector
					edit "nsx"
						set type nsx
						set server "%s"
						set username "%s"
						set password "%s"
						set vmx-service-name "%s"
						set vmx-image-url "%s"
						set rest-password "%s"
					next
				end
			end
		""" % (ip, user, password, service_name, vmx_url, rest_password,)
		self.ssh_command(cmd)
	
	def install_nsx_service(self):
		cmd = """
			config global
				execute nsx service add
			end
		"""
		self.ssh_command(cmd)

if __name__ == "__main__":
	fgt = FortiGate("192.168.1.118")
	self.set_static_ip('sync', '192.168.255.254', '255.255.255.0')
	self.create_dhcp_server('sync', '192.168.255.1', '192.168.255.99', '255.255.255.0', '192.168.255.254')
	self.create_nsx_connector('192.168.1.101', 'http://192.168.1.1/ovf/vmx/v6b0231/FortiGate-VMX.ovf')
	self.install_nsx_service()
