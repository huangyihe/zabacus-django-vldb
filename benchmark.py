#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zabacus.settings")
django.setup()

from django.core import management
from django.contrib.auth import get_user_model
from zabacus.bills.schema import CreateBill, AddBillItem, AddUserToBill
from abc import ABC, abstractmethod
import random
import time


class BenchParams:
    max_operations = 10000
    # Number of initial users in the database
    # User names are assumed to be 'user00001' to 'user00100'
    # IDs are 1-100
    num_init_users = 100
    # Number of initial bills in the database
    # IDs are 1-1000
    num_init_bills = 1000
    # Range of number of users per bill, [min, max]
    num_users_per_bill = (3, 6)
    # Range of number of bill items per bill, [min, max]
    # Each bill item involve all users in the bill
    num_items_per_bill = (5, 15)
    # Create a new user after executing this many operations
    create_user_every_x_ops = 500
    # Create a new bill after executing this many operations
    create_bill_every_x_ops = 100


def user_info_by_id(user_id):
    build_obj = lambda **kwargs: type("Object", (), kwargs)
    return build_obj(context=build_obj(user=get_user_model().objects.get(id=str(user_id))))


def anonymous_user_info():
    build_obj = lambda **kwargs: type("Object", (), kwargs)
    return build_obj(context=build_obj(user=build_obj(is_anonymous=True)))


def username_from_id(user_id):
    return 'user{:05d}'.format(user_id)


class Job(ABC):
    @abstractmethod
    def run(self):
        assert False, 'Abstract method called.'


class CreateBillJob(Job):
    def __init__(self, creator_id, num_users, num_items, benchmark_runner):
        self.creator_id = creator_id
        self.num_users = num_users
        self.num_items = num_items
        self.benchmark_runner = benchmark_runner

    def run(self):
        new_bill_id = CreateBill().mutate(user_info_by_id(self.creator_id), 'Example Bill',
                                          desc='Blah blah blah').bill.id
        self.benchmark_runner.incr_bill_count()
        bill_users = set()
        bill_users.add(self.creator_id)
        for i in range(self.num_users - 1):
            while True:
                rand_user = random.randint(1, self.benchmark_runner.current_user_count())
                if rand_user not in bill_users:
                    bill_users.add(rand_user)
                    break
        for rand_user in bill_users:
            if rand_user == self.creator_id:
                continue
            self.benchmark_runner.append_job(
                AddUserToBillJob(self.creator_id, new_bill_id, username_from_id(rand_user)))
        for i in range(self.num_items):
            self.benchmark_runner.append_job(AddBillItemJob(new_bill_id, bill_users))


class AddUserToBillJob(Job):
    def __init__(self, creator_id, bill_id, username):
        self.creator_id = creator_id
        self.bill_id = bill_id
        self.username = username

    def run(self):
        AddUserToBill().mutate(user_info_by_id(self.creator_id), self.bill_id, self.username)


class AddBillItemJob(Job):
    def __init__(self, bill_id, bill_users):
        self.bill_id = bill_id
        self.bill_users = bill_users

    def run(self):
        weights = {}
        for uid in self.bill_users:
            weights[username_from_id(uid)] = 10.00
        payer_id = random.sample(self.bill_users, 1)[0]
        AddBillItem().mutate(user_info_by_id(payer_id), self.bill_id, 'random_item_name', 'random_description',
                             payer_id, 10.00 * len(self.bill_users), weights)


class CreateUserJob(Job):
    def __init__(self, new_user_id, benchmark_runner):
        self.username = username_from_id(new_user_id)
        self.benchmark_runner = benchmark_runner

    def run(self):
        user = get_user_model()(
            username=self.username,
            first_name=self.username + 'First',
            last_name=self.username + 'Last',
            email='first.last@example.com'
        )
        user.set_password('1234567')
        user.save()

        self.benchmark_runner.incr_user_count()


class BenchmarkRunner:
    def __init__(self):
        self.op_count = 0
        self.user_count = 0
        self.user_id_gen = 0
        self.bill_count = 0
        self.max_ops = BenchParams.max_operations
        self.job_queue = list()

    def current_user_count(self):
        return self.user_count

    def incr_bill_count(self):
        self.bill_count += 1

    def incr_user_count(self):
        self.user_count += 1

    def append_job(self, job):
        self.job_queue.append(job)

    def pick_random_user(self):
        return random.randint(1, self.user_count)

    @staticmethod
    def pick_num_users():
        return random.randint(*BenchParams.num_users_per_bill)

    @staticmethod
    def pick_num_items():
        return random.randint(*BenchParams.num_items_per_bill)

    def add_create_bill_job(self):
        self.append_job(CreateBillJob(self.pick_random_user(), self.pick_num_users(), self.pick_num_items(), self))

    def pre_populate(self):
        # Prepopulate users and bills
        for i in range(BenchParams.num_init_users):
            CreateUserJob(i + 1, self).run()
        assert self.user_count == BenchParams.num_init_users
        self.user_id_gen = self.user_count

        for i in range(BenchParams.num_init_bills):
            CreateBillJob(self.pick_random_user(), self.pick_num_users(), self.pick_num_items(), self).run()
        assert self.bill_count == BenchParams.num_init_bills

    def benchmark(self):
        while self.op_count <= self.max_ops:
            if not self.job_queue:
                self.add_create_bill_job()
            # Pop job off run queue and run it
            job = self.job_queue.pop(0)
            job.run()

            self.op_count += 1
            if self.op_count % BenchParams.create_bill_every_x_ops == 0:
                self.add_create_bill_job()
            if self.op_count % BenchParams.create_user_every_x_ops == 0:
                self.user_id_gen += 1
                self.append_job(CreateUserJob(self.user_id_gen, self))

            if self.op_count % 50 == 0:
                print('Completed {} operations.'.format(self.op_count))

    def run(self):
        print('Pre-populating database...')
        self.pre_populate()
        print('Done. Start benchmarking.')
        time_begin = time.time()
        self.benchmark()
        time_end = time.time()
        print('Done. Elapsed time: {}.'.format(str(time_end - time_begin)))


if __name__ == '__main__':
    print('About to start benchmarking. Please make sure the connected database is empty.')
    input('Press any key to continue...')
    management.call_command('migrate')

    BenchmarkRunner().run()
