from pyVim import connect
import paramiko

import ssl
import OpenSSL

class VMwareCommon:
	STATUS_OFFLINE = "offline"
	STATUS_ONLINE  = "online"

	def __init__(self, **args):
		raise Exception("Abstract class")

	def post_init(self):
		self.api_status   = self.STATUS_OFFLINE
		self.si           = None

		self.ssh_status   = self.STATUS_OFFLINE
		self.ssh          = None
	
		self.connect()

	def disconnect(self):
		if self.si != None and self.api_status != self.STATUS_OFFLINE:
			connect.Disconnect(self.si)

		self.si         = None
		self.api_status = self.STATUS_OFFILINE 

	def connect(self):
		if self.api_status != self.STATUS_OFFLINE:
			self.disconnect()

		self.si = connect.SmartConnect(host=self.ip, user=self.user, pwd=self.password, port=self.api_port)
		self.api_status = self.STATUS_ONLINE

	###
	### certificate operations
	###
	def get_thumbprint(self):
		cert = ssl.get_server_certificate( (self.ip, self.api_port) )
		pem  = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
		return pem.digest('sha1').lower()

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
	
