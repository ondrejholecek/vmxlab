import os
import socket
import ssl

class VMwareNFCUpload:
	def __init__(self, urlmap, perc_callback=None):
		self.uploaded      = 0
		self.total_size    = 0
		self.urlmap        = urlmap
		self.perc_callback = perc_callback

		self.last_perc   = None

		self.calc_total_size()

	def calc_total_size(self):
		self.total_size = 0
		for url in self.urlmap.keys():
			e = self.urlmap[url]
			self.total_size += os.stat(e['local_file']).st_size
	
	def process_perc(self):
		perc = int((self.uploaded*100)/self.total_size)
		if self.last_perc != perc:
			if self.perc_callback != None:
				self.perc_callback(perc)
			self.last_perc = perc

	def connect_ssl(self, ip, port):
		sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
		sockfd.connect( (ip, port) )
		sslfd = ssl.wrap_socket(sockfd)
		return sslfd

	def upload_all(self):
		for url in self.urlmap.keys():
			self.upload_one(url)

	def upload_one(self, url):
		# get parameters from url
		if not url.startswith('https://'): raise Exception("Only HTTPs link are recognized")
		(host, path) = url[8:].split('/', 1)

		tmp = host.split(':', 1)
		if len(tmp) > 1:
			host = tmp[0]
			port = int(tmp[1])
		else:
			port = 443
			
		path = '/' + path

#		print url, host, port, path

		# local file params
		local_file = self.urlmap[url]['local_file']
		local_size = os.stat(local_file).st_size

		# connect
		s = self.connect_ssl(host, port)

		hdr  = "POST %s HTTP/1.1\r\n" % (path,)
		hdr += "Content-Type: application/x-vnd.vmware-streamVmdk\r\n"
		hdr += "Content-Length: %i\r\n" % (local_size,)
		hdr += "Connection: close\r\n"
		hdr += "\r\n"

#		print hdr
		s.send(hdr)

		# send
		f = open(local_file, "rb")
		while True:
			tmp = f.read(8192)
			if len(tmp) == 0: break
			s.send(tmp)
			self.uploaded += len(tmp)
			self.process_perc()

		# response
		resp = s.recv(10240)
		s.close()

		(tmp, code, message) = resp.split("\r\n")[0].split(" ", 3)
		self.urlmap[url]['response'] = {
			'code': int(code),
			'msg' : message,
		}


if __name__ == '__main__':
	nfc = VMwareNFCUpload({
		'https://192.168.1.106/nfc/52f688bd-d936-f3d4-fdec-e6ae5c8747ee/disk-0.vmdk': {
			'local_file': '/var/www/html/ovf/svm/v6b0231/fortios.vmdk',
		},
		'https://192.168.1.106/nfc/52f688bd-d936-f3d4-fdec-e6ae5c8747ee/disk-1.vmdk': {
			'local_file': '/var/www/html/ovf/svm/v6b0231/datadrive.vmdk',
		},
	})

	nfc.upload_all()
