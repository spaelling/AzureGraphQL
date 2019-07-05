import uvicorn
import requests 

import asyncio
import aiohttp

from ariadne import QueryType, gql, make_executable_schema, ObjectType, MutationType
from ariadne.asgi import GraphQL

# NOTE: This is an easy way to get the bearer token https://blog.jongallant.com/2017/11/azure-rest-apis-postman/

type_def = """
    type Query {
        ResourceGroups(subscriptionId: String!): [ResourceGroup]
        VirtualMachines(subscriptionId: String!): [VirtualMachine]
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
    }

    type NetworkInterface {
        id: String!
        name: String!
        ip: String
        pipid: String
        publicIP: PublicIP
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

# @query.field("ResourceGroups")
# def resolve_ResourceGroups(_, info, subscriptionId):  
#     request = info.context["request"]
#     apiVersion = '2017-05-10'
#     uri = 'https://management.azure.com/subscriptions/%s/resourcegroups?api-version=%s' % (subscriptionId, apiVersion)
#     Authorization = request.headers['Authorization']
#     headers={"Authorization": Authorization}
#     r = requests.get(uri, headers=headers)
#     return r.json()['value']

@query.field("ResourceGroups")
async def resolve_ResourceGroups(_, info, subscriptionId):  
    request = info.context["request"]
    apiVersion = '2017-05-10'
    uri = 'https://management.azure.com/subscriptions/%s/resourcegroups?api-version=%s' % (subscriptionId, apiVersion)
    Authorization = request.headers['Authorization']
    headers={"Authorization": Authorization}
    async with aiohttp.ClientSession() as session:
        async with session.get(uri, headers=headers) as resp:
            data = await resp.json()
    return data['value']

# @query.field("VirtualMachines")
# def resolve_VirtualMachines(_, info, subscriptionId):
#     request = info.context["request"]
#     apiVersion = '2019-03-01'
#     uri = 'https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/virtualMachines?api-version=%s' % (subscriptionId, apiVersion)
#     Authorization = request.headers['Authorization']
#     headers={"Authorization": Authorization}
#     r = requests.get(uri, headers=headers)
#     vms = []
#     for vm in r.json()['value']: 
#         vms.append({"id": vm['id'], "name": vm['name'], "location": vm['location'], "nicid": vm['properties']['networkProfile']['networkInterfaces'][0]['id']})
#     return vms

@query.field("VirtualMachines")
async def resolve_VirtualMachines(_, info, subscriptionId):
    request = info.context["request"]
    apiVersion = '2019-03-01'
    uri = 'https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/virtualMachines?api-version=%s' % (subscriptionId, apiVersion)
    Authorization = request.headers['Authorization']
    headers={"Authorization": Authorization}
    # r = requests.get(uri, headers=headers)
    async with aiohttp.ClientSession() as session:
        async with session.get(uri, headers=headers) as resp:
            data = await resp.json()
    vms = []
    for vm in data['value']: 
        vms.append({"id": vm['id'], "name": vm['name'], "location": vm['location'], "nicid": vm['properties']['networkProfile']['networkInterfaces'][0]['id']})
    return vms

@virtualMachine.field("nic")
async def resolve_followers(parent, info): 
    request = info.context["request"] 
    apiVersion = '2019-02-01'
    resourceId = parent['nicid']
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    Authorization = request.headers['Authorization']
    headers={"Authorization": Authorization}
    # r = requests.get(uri, headers=headers)
    async with aiohttp.ClientSession() as session:
        async with session.get(uri, headers=headers) as resp:
            nic = await resp.json()    
    # nic = r.json()
    return {"id": nic['id'], "name": nic['name'], "ip": nic['properties']['ipConfigurations'][0]['properties']['privateIPAddress'], "pipid": nic['properties']['ipConfigurations'][0]['properties']['publicIPAddress']['id']}

@networkInterface.field("publicIP")
async def resolve_publicIP(parent, info): 
    request = info.context["request"] 
    apiVersion = '2019-02-01'
    resourceId = parent['pipid']
    uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
    # print(uri)
    Authorization = request.headers['Authorization']
    headers={"Authorization": Authorization}
    # r = requests.get(uri, headers=headers)
    async with aiohttp.ClientSession() as session:
        async with session.get(uri, headers=headers) as resp:
            data = await resp.json()   
    pip =  {"id": data['id'], "name": data['name']}
    if 'ipAddress' in data['properties']:
        pip['ip'] = data['properties']['ipAddress']
    return pip

# @virtualMachine.field("nic")
# def resolve_followers(parent, info): 
#     request = info.context["request"] 
#     apiVersion = '2019-02-01'
#     resourceId = parent['nicid']
#     uri = 'https://management.azure.com%s?api-version=%s' % (resourceId, apiVersion)
#     Authorization = request.headers['Authorization']
#     headers={"Authorization": Authorization}
#     r = requests.get(uri, headers=headers)
#     nic = r.json()
#     return {"id": nic['id'], "name": nic['name'], "ip": nic['properties']['ipConfigurations'][0]['properties']['privateIPAddress']}

schema = make_executable_schema(type_def, [query, virtualMachine, networkInterface])
app = GraphQL(schema, debug=True)

if __name__ == "__main__":
    uvicorn.run(app)
