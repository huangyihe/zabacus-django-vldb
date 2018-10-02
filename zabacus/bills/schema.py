import graphene
from graphql import GraphQLError
from graphene_django.types import DjangoObjectType
from django.contrib.auth import get_user_model
from zabacus.bills.models import Bill, BillItem, ItemWeightAssignment


class DisplayUserType(DjangoObjectType):
    class Meta:
        model = get_user_model()
        only_fields = ('id', 'username', 'first_name', 'last_name')


class BillItemType(DjangoObjectType):
    class Meta:
        model = BillItem


class BillType(DjangoObjectType):
    class Meta:
        model = Bill


class ItemWeightAssignmentType(DjangoObjectType):
    class Meta:
        model = ItemWeightAssignment


class Query(object):
    list_bills = graphene.List(BillType)
    show_bill = graphene.Field(BillType, bid=graphene.Int())

    def resolve_list_bills(self, info, **kwargs):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not logged in!')
        return user.involved.all()

    def resolve_show_bill(self, info, bid):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not Logged In!')
        return user.involved.get(id=bid)
