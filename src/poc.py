import uvicorn
import requests 

import asyncio
import aiohttp

from ariadne import QueryType, gql, make_executable_schema, ObjectType, MutationType
from ariadne.asgi import GraphQL

# NOTE: This is an easy way to get the bearer token https://blog.jongallant.com/2017/11/azure-rest-apis-postman/

# add resource type to resources query
type_def = """
    type Query {
        ResourceGroups(subscriptionId: String!): [ResourceGroup]
        VirtualMachines(subscriptionId: String!): [VirtualMachine]
        Resources(subscriptionId: String!, resourceGroupName: String): [Resource]
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
    }

    type PublicIP {
        id: String!
        name: String!
        ip: String
    }
"""

query = ObjectType("Query")
virtualMachine = ObjectType("VirtualMachine")
networkInterface = ObjectType("NetworkInterface")
resource = ObjectType("Resource")

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
async def resolve_Resources(_, info, subscriptionId, resourceGroupName=None):  
    apiVersion = '2018-05-01'
    if resourceGroupName:
        uri = 'https://management.azure.com/subscriptions/%s/resourcegroups/%s/resources?api-version=%s' % (subscriptionId, resourceGroupName, apiVersion)
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
    vms = []
    for vm in data: 
        d = {
            'id': vm['id'],
            'name': vm['name'],
            'size': vm['properties']['hardwareProfile']['vmSize'],
            'location': vm['location'],
            'nicid': vm['properties']['networkProfile']['networkInterfaces'][0]['id'],
            'os': vm['properties']['storageProfile']['osDisk']['osType']
            }
        vms.append(d)
    return vms

@virtualMachine.field("nic")
async def resolve_networkInterface(parent, info): 
    apiVersion = '2019-02-01'
    resourceId = parent['nicid']
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    nic = await resolveRequest(info, uri)
    return {
        "id": nic['id'], 
        "name": nic['name'], 
        "ip": nic['properties']['ipConfigurations'][0]['properties']['privateIPAddress'], 
        "pipid": nic['properties']['ipConfigurations'][0]['properties']['publicIPAddress']['id'],
        'allocationMethod' : nic['properties']['ipConfigurations'][0]['properties']['privateIPAllocationMethod']
        }

@networkInterface.field("publicIP")
async def resolve_publicIP(parent, info):
    apiVersion = '2019-02-01'
    resourceId = parent['pipid']
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    data = await resolveRequest(info, uri)
    pip =  {'id': data['id'], 'name': data['name'], 'ip': data['properties'].get('ipAddress')}
    return pip

schema = make_executable_schema(type_def, bindableSchemas)
app = GraphQL(schema, debug=True)

if __name__ == "__main__":
    uvicorn.run(app)
