import os
import uvicorn
# ariadne
from ariadne import make_executable_schema, load_schema_from_path, ObjectType
from ariadne.asgi import GraphQL
# azuregraphql
from src.resolvers import bindableSchemas

rootpath = os.path.dirname(__file__)
schemaspath = os.path.join(rootpath, 'src/schemas/')
type_defs = load_schema_from_path(schemaspath)
schema = make_executable_schema(type_defs, bindableSchemas)
app = GraphQL(schema, debug=True)

if __name__ == "__main__":    
    uvicorn.run(app)