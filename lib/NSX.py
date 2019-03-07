import requests
import xml.etree.ElementTree as ET
import json
import time

import ssl
import OpenSSL

class NSX:
	def __init__(self, ip, user="admin", password="default", api_port=443):
		self.ip       = ip
		self.user     = user
		self.password = password
		self.api_port = api_port

	###
	### certificate operations
	###
	def get_thumbprint(self):
		cert = ssl.get_server_certificate( (self.ip, self.api_port) )
		pem  = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
		return pem.digest('sha1').lower()


	###
	### REST API management
	###
	def request(self, url, postdata=None, putdata=None, delete=False, headers={}):
		if url[0] == '/': url = url[1:]

		if postdata != None:
			fce  = requests.post
			data = postdata
		elif putdata != None:
			fce  = requests.put
			data = putdata
		elif delete == True:
			fce  = requests.delete
			data = None
		else:
			fce  = requests.get
			data = None

		prepare_headers = {
			'Accept': 'application/xml',
			'Content-Type': 'application/xml',
		}
		prepare_headers.update(headers)

		r = fce('https://%s/%s' % (self.ip, url,), 
			auth=(self.user, self.password),
			headers = prepare_headers,
			verify = False,
			data = data,
		)

		return (r.status_code, r.text)

	###
	### user functions
	###
	def register_to_vcenter(self, ip, thumbprint, user="administrator@vsphere.local", password="fortinet"):
		xml = """
			<vcInfo>
				<ipAddress>%s</ipAddress>
				<userName>%s</userName>
				<password>%s</password>
				<certificateThumbprint>%s</certificateThumbprint>
				<assignRoleToUser>true</assignRoleToUser>
				<pluginDownloadServer></pluginDownloadServer>
				<pluginDownloadPort></pluginDownloadPort>
			</vcInfo>
		""" % (ip, user, password, thumbprint,)
		(status, text) = self.request('/api/2.0/services/vcconfig', putdata=xml)
		if (status < 200) or (status > 299): raise Exception(text)

	def host_preparation(self, cluster_moid):
		xml = """
			<nwFabricFeatureConfig>
				<resourceConfig>
					<resourceId>%s</resourceId>
				</resourceConfig>
			</nwFabricFeatureConfig>
		""" % (cluster_moid,)
		(status, text) = self.request('/api/2.0/nwfabric/configure', postdata=xml)
		if (status < 200) or (status > 299): raise Exception(text)
		return text
	

	def get_services(self, name=None):
		services = {}
		(status, text) = self.request('/api/2.0/si/serviceprofiles')
		root = ET.fromstring(text)
		for serviceprofile in root:
			if serviceprofile.tag != 'serviceProfile': continue

			profile_name = serviceprofile.find("name")
			profile_id   = serviceprofile.find("objectId")
			if profile_name == None or profile_id == None: continue

			service       = serviceprofile.find("service")
			if service == None: continue
			service_name  = service.find("name")
			service_id    = service.find("objectId")
			if service_name == None or service_id == None: continue

			# ok we have everything
			if service_name.text not in services: services[service_name.text] = {
				'serviceId' : service_id.text,
				'profiles'  : [],
			}
			services[service_name.text]['profiles'].append({
				'name'       : profile_name.text,
				'profileId'  : profile_id.text,
			})
			
		if name != None:
			if name not in services.keys():
				return None
			else:
				return services[name]

		else:
			return services

	def get_service_id2(self, service_name):
		(status, text) = self.request('/api/2.0/si/services')
		root = ET.fromstring(text)
		for service in root:
			if service.tag != 'service': continue
			name       = service.find("name")
			service_id = service.find("objectId")
			if name == None or service_id == None: continue
			if name.text == service_name:
				return service_id.text
		return None

	def service_deploy(self, cluster_moid, datastore_moid, portgroup_moid, service_id):
		xml = """
			<clusterDeploymentConfigs>
				<clusterDeploymentConfig>
					<clusterId>%s</clusterId>
					<datastore>%s</datastore>
					<services>
						<serviceDeploymentConfig>
							<serviceId>%s</serviceId>
							<dvPortGroup>%s</dvPortGroup>
						</serviceDeploymentConfig>
					</services>
				</clusterDeploymentConfig>
			</clusterDeploymentConfigs>
		""" % (cluster_moid, datastore_moid, service_id, portgroup_moid)
		(status, text) = self.request('/api/2.0/si/deploy', postdata=xml)
		return text
	
	def service_delete(self, cluster_moid, service_id):
		(status, text) = self.request('/api/2.0/si/deploy/service/%s?clusters=%s' % (service_id, cluster_moid,), delete=True)
		if (status < 200) or (status > 299): raise Exception("Unable to delete service: %s" % (text,))
		return text
	
	def get_all_security_groups(self):
		(status, text) = self.request('/api/2.0/services/securitygroup/scope/globalroot-0')
		root = ET.fromstring(text)
		if root.tag != 'list': raise Exception('Expect root tag to be "list" and not "%s"' % (root.tag,))

		groups = {}
		for group in root.findall("./securitygroup"):
			name = group.findtext("./name", default=None)
			objectId = group.findtext("./objectId", default=None)
			if name == None or objectId == None: continue

			groups[name] = {
				'id'  : objectId,
			}

		return groups
		

	def create_security_policy(self, name, actions, description='Created by API', precedence=5001, groups={}):
		xml_actions = ""
		for action in actions:
			xml_actions += """
					<action class="trafficSteeringSecurityAction">
						<name>%s</name>
						<description>%s</description>
						<category>traffic_steering</category>
						<direction>%s</direction>
						<isActionEnforced>false</isActionEnforced>
						<isEnabled>%s</isEnabled>
						<logged>%s</logged>
						<redirect>true</redirect>
						<serviceProfile>
							<objectId>%s</objectId>
						</serviceProfile>
					</action>
			""" % (action['name'], action['description'], action['direction'], action['enabled'],
			       action['logged'], action['service'],)

		xml_groups = ""
		for group in groups:
			xml_groups += """
				<securityGroupBinding>
					<objectId>%s</objectId>
				</securityGroupBinding>
			""" % (group['id'],)

		xml = """
			<securityPolicy>
				<name>%s</name>
				<description>%s</description>
				<precedence>%i</precedence>

				 <actionsByCategory>
					<category>traffic_steering</category>
					%s
				</actionsByCategory>
				%s

			</securityPolicy>
		""" % (name, description, precedence, xml_actions, xml_groups,)
		(status, text) = self.request('/api/2.0/services/policy/securitypolicy', postdata=xml)
		if (status < 200) or (status > 299): raise Exception("Unable to create security policy: %s" % (text,))

	def get_all_policies(self, no_dynamic=False):
		(status, text) = self.request('/api/2.0/services/policy/securitypolicy/all')
		root = ET.fromstring(text)
		if root.tag != 'securityPolicies': raise Exception('Root tag expected to be "securityPolicies" but it is "%s" instead' % (root.tag,))

		policies = []
		for p in root.findall('./securityPolicy'):

			isHidden = False
			for ea in p.findall('./extendedAttributes/extendedAttribute'):
				if ea.findtext('./name') == 'isHidden' and bool(ea.findtext('./value')) == True:
					isHidden = True
					break
			if isHidden: continue

			policy = {
				'name'        : p.findtext('./name', default=''),
				'description' : p.findtext('./description', default=''),
				'precedence'  : int(p.findtext('./precedence', default='0')),
			}

			if not no_dynamic:
				policy['id'] = p.findtext('./objectId', default='')

			actions = []
			for a in p.findall('./actionsByCategory/[category="traffic_steering"]/action[@class="trafficSteeringSecurityAction"]'):
				actions.append({
					'name': a.findtext('./name', default=''),
					'description': a.findtext('./description', default=''),
					'category': a.findtext('./category', default=''),
					'order': int(a.findtext('./executionOrder', default=0)),
					'enabled': a.findtext('./isEnabled', default=False),
					'logged': a.findtext('./logged', default=False),
					'redirect': a.findtext('./redirect', default=False),
					'direction': a.findtext('./direction'),
					'service profile': a.findtext('./serviceProfile/name'),
					'service': a.findtext('./serviceProfile/service/name'),
				})

			groups = []
			for g in p.findall('./securityGroupBinding/[name]'):
				groups.append({
					'name': g.findtext('name'),
	#				'description': g.findtext('description'),
				})

			policy['actions'] = actions
			policy['groups']  = groups

			policies.append(policy)

		return policies

	def restore_policy(self, policy):
		actions = []
		for action in policy['actions']:
			actions.append({	
				'name'        : action['name'],
				'description' : action['description'],
				'direction'   : action['direction'],
				'logged'      : str(action['logged']),
				'enabled'     : str(action['enabled']),
			})

			service = self.get_services(name=action['service'])
			if service == None: raise Exception('Cannot find service name "%s"' % (action['service'],))
			profile = None
			for p in service['profiles']:
				if p['name'] == action['service profile']:
					profile = p['profileId']
					break
			if profile == None: raise Exception('Cannot find profile name "%s" in existing service "%s"' % (action['service profile'], action['service'],))
	
			actions[-1]['service'] = profile

		allgroups = self.get_all_security_groups()
		groups = []
		for group in policy['groups']:
			if group['name'] not in allgroups.keys(): continue
			group_id = allgroups[group['name']]['id']
			groups.append({'id' : group_id})

		self.create_security_policy(policy['name'], actions, policy['description'], policy['precedence'], groups)

	def delete_policy(self, policy_id):
		(status, text) = self.request('/api/2.0/services/policy/securitypolicy/%s?force=true' % (policy_id,), delete=True)
		if (status < 200) or (status > 299): raise Exception('Unable to delete policy "%s": %s"' % (policy_id, text,))
	
	def delete_policy_by_name(self, name):
		policy_id = None
		for policy in self.get_all_policies():
			if policy['name'] == name:
				policy_id = policy['id']
				break
		if not policy_id: raise Exception('No such policy name "%s"' % (name,))

		self.delete_policy(policy_id)
		
	###
	### jobs
	###
	def get_job_status(self, jobid):
		(status, text) = self.request('/api/2.0/services/taskservice/job/%s' % (jobid,))
		return text

	def wait_for_job(self, jobid):
		while True:
			text = self.get_job_status(jobid)
			root = ET.fromstring(text)
			if root.tag != 'jobInstances': raise Exception('Root tag expected to be "jobInstances" but it is "%s" instead' % (root.tag,))
			results = []
			for ji in root.findall('jobInstance'):
				results.append({
					'id' : ji.findtext('id'),
					'name' : ji.findtext('name'),
					'status': ji.findtext('status'),
				})

			all_done = True
			for result in results:
				if result['status'] not in ('COMPLETED',):
					all_done = False

			if all_done: return True

			time.sleep(1)
				


if __name__ == '__main__':
	# Yeah, the certificates are invalid, stop being a babysitter
	from requests.packages.urllib3.exceptions import InsecureRequestWarning
	requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

	import ssl
	ssl._create_default_https_context = ssl._create_unverified_context
	context = ssl.create_default_context()
	context.check_hostname = False
	context.verify_mode = ssl.CERT_NONE

	nsx = NSX("10.109.80.28")
	#print nsx.get_thumbprint()

	#nsx.request('/api/2.0/services/vcconfig')
	#nsx.register_to_vcenter("192.168.1.103", "94:f5:2e:3d:1c:5a:aa:6a:06:5c:bf:ff:a1:2b:48:79:fe:d8:4f:99")
	#jobid = nsx.host_preparation('domain-c7')

#	print "jobid:" + jobid
#	import time
#	while True:
#		nsx.get_job_status(jobid)
#		time.sleep(10)
		
#	service = nsx.get_services('labvmx')
#	print service

#	print json.dumps(nsx.get_all_policies(), indent=4)
#	nsx.delete_policy_by_name('Security Policy')

#	print nsx.service_deploy('domain-c7', 'datastore-11', 'dvportgroup-110', service['serviceId'])

#	nsx.create_security_policy('LabPolicy', [
#		{	
#			'name'        : 'from outside',
#			'description' : 'any -> protected VM',
#			'direction'   : 'inbound',
#			'logged'      : 'false',
#			'enabled'     : 'true',
#			'service'     : service['profiles'][0]['profileId'],
#		},
#		{	
#			'name'        : 'from VMs',
#			'description' : 'protected VM -> any',
#			'direction'   : 'outbound',
#			'logged'      : 'false',
#			'enabled'     : 'true',
#			'service'     : service['profiles'][0]['profileId'],
#		},
#	])
