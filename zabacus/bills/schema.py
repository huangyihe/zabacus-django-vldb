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


class AddItemToBill(graphene.Mutation):
    bill = graphene.Field(BillType)

    class Arguments:
        bid = graphene.Int(required=True)
        iname = graphene.String(required=True)
        idesc = graphene.String(required=True)
        payor = graphene.Int(required=True)
        total = graphene.Float(required=True)
        assign = graphene.JSONString(required=True)

    def mutate(self, info, bid, iname, idesc, payor, total, assign):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not logged in!')
        try:
            bill = user.involved.get(id=bid)
        except ObjectDoesNotExist:
            raise GraphQLError('Bill not found.')

        # check validity of assignment JSON string
        user_assignments = []
        assign_total = 0.0
        for u, amount in assign.items():
            try:
                assigned_user = bill.people.get(username=u)
            except ObjectDoesNotExist:
                raise GraphQLError('Invalid weight assignment (user not involved).')
            assign_total += amount
            user_assignments.append((assigned_user, amount))
        if assign_total != total:
            raise GraphQLError('Invalid weight assignment (sum mismatch).')

        try:
            payor_user = bill.people.get(id=payor)
        except ObjectDoesNotExist:
            raise GraphQLError('Payor not involved.')

        datetime = tz.localtime(tz.now())
        new_item = BillItem.objects.create(
            name=iname,
            desc=idesc,
            date=datetime,
            edited=datetime,
            created_by=user,
            paid_by=payor_user,
            bill=bill,
            total=total
        )
        new_item.save()
        for (u, amount) in user_assignments:
            ass_rel = ItemWeightAssignment.objects.create(
                item=new_item,
                user=u,
                amount=amount
            )
            ass_rel.save()

        return AddItemToBill(bill=bill)


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
        bid = graphene.Int()

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


class DeleteBill(graphene.Mutation):
    result = graphene.String()

    class Arguments:
        bid = graphene.Int(required=True)

    def mutate(self, info, bid):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not logged in!')
        try:
            bill = user.created.get(id=bid)
        except ObjectDoesNotExist:
            raise GraphQLError('Target bill not found.')
        bill.delete()

        return DeleteBill(result='OK')


class Mutation(graphene.ObjectType):
    add_user_to_bill = AddUserToBill.Field()
    add_item_to_bill = AddItemToBill.Field()
    create_bill = CreateBill.Field()
    delete_bill = DeleteBill.Field()


class Query(graphene.ObjectType):
    list_bills = graphene.List(BillType)
    created_bills = graphene.List(BillType)
    show_bill = graphene.Field(BillType, bid=graphene.Int())

    def resolve_list_bills(self, info, **kwargs):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not logged in!')
        return user.involved.all()

    def resolve_created_bills(self, info, **kwargs):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not Logged in!')
        return user.created.all()

    def resolve_show_bill(self, info, bid):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError('Not Logged In!')
        return user.involved.get(id=bid)
