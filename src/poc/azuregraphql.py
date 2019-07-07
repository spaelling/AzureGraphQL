import uvicorn
import requests 
import asyncio
import aiohttp
from ariadne import QueryType, gql, make_executable_schema, ObjectType, MutationType
from ariadne.asgi import GraphQL

type_def = """
    type Query {
        ResourceGroups(subscriptionId: String!): [ResourceGroup]
        VirtualMachines(subscriptionId: String!): [VirtualMachine]
        Resources(subscriptionId: String!, resourceGroupName: String, resourceType: String): [Resource]
    }

    type Resource {
        id: String!
        name: String!
        type: String!        
        location: String!
        sku: Sku
    }

    type Sku {
        name: String!
        tier: String
    }

    type ResourceGroup {
        id: String!
        name: String!
        location: String!
    }

    type VirtualMachine {
        id: String!
        name: String!
        location: String!
        nic: NetworkInterface
        size: String!
        os: String!
    }

    type NetworkInterface {
        id: String!
        name: String!
        ip: String
        pipid: String
        publicIP: PublicIP
        allocationMethod: String!
        networkSecurityGroup: NetworkSecurityGroup
        subnet: Subnet
    }

    type Subnet {
        id: String!
        name: String!
        addressPrefix: String!
    }

    type NetworkSecurityGroup {
        name: String!
        id: String!
        rules: [SecurityRules]
    }

    type SecurityRules {
        name: String!
        id: String!
        protocol: String
        access: String!
    }

    type PublicIP {
        id: String!
        name: String!
        ip: String
    }
"""

query = ObjectType('Query')
virtualMachine = ObjectType('VirtualMachine')
networkInterface = ObjectType('NetworkInterface')
resource = ObjectType('Resource')

bindableSchemas = [query, virtualMachine, networkInterface, resource]

async def resolveRequest(info, uri):
    request = info.context["request"]
    authorization = request.headers['Authorization']
    headers = {"Authorization": authorization}
    async with aiohttp.ClientSession() as session:
        async with session.get(uri, headers = headers) as resp:
            data = await resp.json()
    if data.get('error'):
        print(data['error']['message']) # TODO: log error
        return None
    return data.get('value', data)

@query.field("Resources")
async def resolve_Resources(_, info, subscriptionId, resourceGroupName=None, resourceType=None):  
    apiVersion = '2018-05-01'
    if resourceGroupName:
        uri = 'https://management.azure.com/subscriptions/%s/resourcegroups/%s/resources?api-version=%s' % (subscriptionId, resourceGroupName, apiVersion)
    elif resourceType:
        None # TODO
    else:
        uri = 'https://management.azure.com/subscriptions/%s/resources?api-version=%s' % (subscriptionId, apiVersion)
    return await resolveRequest(info, uri)

@resource.field("sku")
def resolve_sku(parent, info):
    if 'sku' in parent:
        return parent['sku']

@query.field("ResourceGroups")
async def resolve_ResourceGroups(_, info, subscriptionId):
    apiVersion = '2017-05-10'
    uri = 'https://management.azure.com/subscriptions/%s/resourcegroups?api-version=%s' % (subscriptionId, apiVersion)
    return await resolveRequest(info, uri)

@query.field("VirtualMachines")
async def resolve_VirtualMachines(_, info, subscriptionId):
    apiVersion = '2019-03-01'
    uri = 'https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/virtualMachines?api-version=%s' % (subscriptionId, apiVersion)
    data = await resolveRequest(info, uri)
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
            'os': vm['properties']['storageProfile']['osDisk']['osType']
            }
        vms.append(d)
    return vms

@virtualMachine.field("nic")
async def resolve_networkInterface(parent, info): 
    apiVersion = '2019-02-01'
    resourceId = parent['_nicid']
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    nic = await resolveRequest(info, uri)
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
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    data = await resolveRequest(info, uri)
    pip =  {'id': data['id'], 'name': data['name'], 'ip': data['properties'].get('ipAddress')}
    return pip

@networkInterface.field("networkSecurityGroup")
async def resolve_nsg(parent, info):
    apiVersion = '2019-02-01'
    resourceId = parent.get('_nsgid')
    if resourceId == None:
        return None
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    data = await resolveRequest(info, uri)
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
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    data = await resolveRequest(info, uri)
    subnet =  {'id': data['id'], 'name': data['name'], 'addressPrefix': data['properties']['addressPrefix']}
    return subnet

schema = make_executable_schema(type_def, bindableSchemas)
app = GraphQL(schema, debug=True)

if __name__ == "__main__":    
    uvicorn.run(app)