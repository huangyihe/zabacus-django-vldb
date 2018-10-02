import graphene
import zabacus.bills.schema

class Query(zabacus.bills.schema.Query, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query)
