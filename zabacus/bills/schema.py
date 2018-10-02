import graphene
from graphql import GraphQLError
from graphene_django.types import DjangoObjectType
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
import django.utils.timezone as tz
from django.contrib.auth import get_user_model
from zabacus.bills.models import Bill, BillItem, Involvement, ItemWeightAssignment, BillStatus


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


class AddUserToBill(graphene.Mutation):
    bill = graphene.Field(BillType)

    class Arguments:
        bid = graphene.Int(required=True)
        uid = graphene.Int(required=True)

    def mutate(self, info, bid, uid):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not logged in!')
        try:
            bill = user.involved.get(id=bid)
        except ObjectDoesNotExist:
            raise GraphQLError('Can not find bill.')
        try:
            target_user = get_user_model().objects.get(id=uid)
        except ObjectDoesNotExist:
            raise GraphQLError('Target user does not exist.')
        if bill.people.filter(id=uid).exists():
            raise GraphQLError('User already in bill.')

        new_rel = Involvement.objects.create(bill=bill, user=target_user)
        new_rel.save()

        return AddUserToBill(bill=bill)


class CreateBill(graphene.Mutation):
    bill = graphene.Field(BillType)

    class Arguments:
        name = graphene.String(required=True)
        bid = graphene.Int(required=False)

    def mutate(self, info, name, **kwargs):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not logged in!')
        datetime = tz.localtime(tz.now())
        new_bill = Bill.objects.create(
            name=name,
            date=datetime,
            edited=datetime,
            created_by=user,
            status=BillStatus.OPN.name
        )
        new_bill.save()
        bid = kwargs.get('bid')
        if bid is not None:
            try:
                bill = user.involved.get(id=bid)
            except ObjectDoesNotExist:
                raise GraphQLError('Template source bill not found.')
            for p in bill.people.all():
                new_rel = Involvement.objects.create(bill=new_bill, user=p)
                new_rel.save()
        else:
            new_rel = Involvement.objects.create(bill=new_bill, user=user)
            new_rel.save()

        return CreateBill(bill=new_bill)


class Mutation(graphene.ObjectType):
    add_user_to_bill = AddUserToBill.Field()
    create_bill = CreateBill.Field()


class Query(graphene.ObjectType):
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
