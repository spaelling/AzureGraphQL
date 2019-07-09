import requests 
import asyncio
import aiohttp
from ariadne import QueryType, gql, ObjectType, MutationType

# TODO: drop the annotation and do set_field
query = ObjectType('Query')
virtualMachine = ObjectType('VirtualMachine')
networkInterface = ObjectType('NetworkInterface')
resource = ObjectType('Resource')
resourceGroup = ObjectType('ResourceGroup')

bindableSchemas = [query, virtualMachine, networkInterface, resource, resourceGroup]

import urllib.parse

async def resolveRequest(info, baseuri, params):
    request = info.context["request"]
    authorization = request.headers['Authorization']
    headers = {"Authorization": authorization}
    async with aiohttp.ClientSession() as session:
        query = urllib.parse.urlencode(params)
        uri = "%s?%s" % (baseuri, query)
        # print(uri)
        async with session.get(uri, headers = headers) as resp:
            # print(resp.status)
            # assert resp.status == 200
            data = await resp.json()
    if data.get('error'):
        print(data['error']['message']) # TODO: log error
        return None
    return data.get('value', data)

@query.field("Resources")
async def resolve_Resources(_, info, subscriptionId, resourceGroupName=None, resourceType=None):  
    apiVersion = '2018-05-01'
    if resourceGroupName:
        baseuri = 'https://management.azure.com/subscriptions/%s/resourcegroups/%s/resources' % (subscriptionId, resourceGroupName)
    elif resourceType:
        None # TODO
    else:
        baseuri = 'https://management.azure.com/subscriptions/%s/resources' % subscriptionId
    params = {'api-version': apiVersion}    
    data = await resolveRequest(info, baseuri, params)
    return data

@resource.field("sku")
def resolve_sku(parent, info):
    if 'sku' in parent:
        return parent['sku']

@query.field("ResourceGroups")
async def resolve_ResourceGroups(_, info, subscriptionId):
    apiVersion = '2017-05-10'
    baseuri = 'https://management.azure.com/subscriptions/%s/resourcegroups' % subscriptionId    
    params = {'api-version': apiVersion}    
    data = await resolveRequest(info, baseuri, params)
    return data

@resourceGroup.field("consumption")
async def resolve_RGConsumption(resourceGroup, info):
    apiVersion = '2019-01-01'
    rgName = resourceGroup['name']
    subscriptionId = resourceGroup['id'].split('/')[2]
    baseuri = 'https://management.azure.com/subscriptions/%s/providers/Microsoft.Consumption/usageDetails' % subscriptionId
    params = {'api-version': apiVersion, '$filter': ("properties/resourceGroup eq '%s'" % rgName)}    
    data = await resolveRequest(info, baseuri, params)
    if not data or len(data) == 0:
        return {'usage': 0.0, 'currency': 'N/A'}
    sum = 0.0
    currency = 'DKK' # TODO    
    for usage in data:
        sum += usage['properties'].get('usageQuantity',0.0) * usage['properties'].get('pretaxCost',0.0)
    return {'usage': sum, 'currency': currency}

@query.field("VirtualMachines")
async def resolve_VirtualMachines(_, info, subscriptionId):
    apiVersion = '2019-03-01'
    baseuri = 'https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/virtualMachines' % subscriptionId    
    params = {'expand': 'instanceView', 'api-version': apiVersion}    
    data = await resolveRequest(info, baseuri, params)
    if data == None:
        return None
    vms = []
    for vm in data: 
        d = {
            'id': vm['id'],
            'name': vm['name'],
            'size': vm['properties']['hardwareProfile']['vmSize'],
            'location': vm['location'],
            '_nicid': vm['properties']['networkProfile']['networkInterfaces'][0]['id'],
            'os': vm['properties']['storageProfile']['osDisk']['osType'],
            '_vmid': vm['id']
            }
        vms.append(d)
    return vms

@virtualMachine.field("instanceView")
async def resolve_vmInstanceView(parent, info): 
    apiVersion = '2019-03-01'
    resourceId = parent['_vmid']
    baseuri = 'https://management.azure.com%s/instanceview' % resourceId
    params = {'api-version': apiVersion}    
    data = await resolveRequest(info, baseuri, params)
    return {
        'vmStatus': data['statuses'][1]['code']
        }

@virtualMachine.field("nic")
async def resolve_networkInterface(parent, info): 
    apiVersion = '2019-02-01'
    resourceId = parent['_nicid']
    baseuri = 'https://management.azure.com%s' % resourceId
    params = {'api-version': apiVersion}    
    nic = await resolveRequest(info, baseuri, params)
    return {
        "id": nic['id'], 
        "name": nic['name'], 
        "ip": nic['properties']['ipConfigurations'][0]['properties']['privateIPAddress'],         
        'allocationMethod' : nic['properties']['ipConfigurations'][0]['properties']['privateIPAllocationMethod'],
        "_pipid": nic['properties']['ipConfigurations'][0]['properties'].get('publicIPAddress',{}).get('id'),
        "_subnetid": nic['properties']['ipConfigurations'][0]['properties'].get('subnet',{}).get('id'),
        "_nsgid": nic['properties'].get('networkSecurityGroup', {}).get('id')
        }

@networkInterface.field("publicIP")
async def resolve_publicIP(parent, info):
    apiVersion = '2019-02-01'
    resourceId = parent['_pipid']
    if resourceId == None:
        return None    
    baseuri = 'https://management.azure.com%s' % resourceId
    params = {'api-version': apiVersion}
    data = await resolveRequest(info, baseuri, params)
    pip =  {'id': data['id'], 'name': data['name'], 'ip': data['properties'].get('ipAddress')}
    return pip

@networkInterface.field("networkSecurityGroup")
async def resolve_nsg(parent, info):
    apiVersion = '2019-02-01'
    resourceId = parent.get('_nsgid')
    if resourceId == None:
        return None
    baseuri = 'https://management.azure.com%s' % resourceId
    params = {'api-version': apiVersion}
    data = await resolveRequest(info, baseuri, params)
    nsg =  {'id': data['id'], 'name': data['name'], 'rules': []}
    for rule in data['properties']['securityRules']:
        p = rule['properties']
        nsg['rules'].append({
            'name': rule['name'],
            'id': rule['id'],
            'protocol': p['protocol'],
            'access': p['access']
        })
    return nsg

@networkInterface.field("subnet")
async def resolve_subnet(parent, info):
    apiVersion = '2019-02-01'
    resourceId = parent.get('_subnetid')
    if resourceId == None:
        return None
    baseuri = 'https://management.azure.com%s' % resourceId
    params = {'api-version': apiVersion}
    data = await resolveRequest(info, baseuri, params)
    subnet =  {'id': data['id'], 'name': data['name'], 'addressPrefix': data['properties']['addressPrefix']}
    return subnet