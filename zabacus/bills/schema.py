import graphene
from graphene_django.types import DjangoObjectType
from django.contrib.auth import get_user_model
from zabacus.bills.models import Bill, BillItem, Involvement, ItemWeightAssignment

class UserType(DjangoObjectType):
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
    bills = graphene.List(BillType, uid=graphene.Int())

    def resolve_bills(self, info, **kwargs):
        uid = kwargs.get('uid')
        return Bill.objects.filter(people=uid)
