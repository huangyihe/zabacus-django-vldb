#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zabacus.settings')
os.environ.setdefault('DJANGO_SECRET_KEY', '!2%a%fw)m((glocz!3y*wh8j_zb#)t65-q(5mqz&mczld8-4eb')
django.setup()

from django.core import management
from django.contrib.auth import get_user_model
from zabacus.bills.schema import CreateBill, AddBillItem, AddUserToBill
from zabacus.bills.schema import BenchmarkUpdateBillName, BenchmarkUpdateBillItemName
from abc import ABC, abstractmethod
import random
import time
from datetime import timedelta


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
    # Update the name of a bill after this many operations
    update_bill_name_every_x_ops = 505
    # Update the first bill item name in a bill after this many operations
    update_bill_item_name_every_x_ops = 505


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
        self.benchmark_runner.record_user_with_bill(self.creator_id)


class UpdateBillNameJob(Job):
    def __init__(self, creator_id, new_name):
        self.creator_id = creator_id
        self.new_name = new_name

    def run(self):
        BenchmarkUpdateBillName().mutate(user_info_by_id(self.creator_id), self.new_name)


class UpdateBillItemNameJob(Job):
    def __init__(self, creator_id, bill_id, new_item_name):
        self.creator_id = creator_id
        self.new_item_name = new_item_name

    def run(self):
        BenchmarkUpdateFirstBillItemInBill().mutate(user_info_by_id(self.creator_id), self.new_item_name)


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
        self.users_with_bill = set()
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

    def record_user_with_bill(self, user_id):
        self.users_with_bill.add(user_id)

    def pick_random_user_with_bill(self):
        return random.sample(self.users_with_bill, 1)[0]

    def pick_random_bill(self):
        return random.randint(1, self.bill_count)

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

        print('>>> Insert initial users.')
        for i in range(BenchParams.num_init_users):
            CreateUserJob(i + 1, self).run()
        assert self.user_count == BenchParams.num_init_users
        self.user_id_gen = self.user_count

        print('>>> Insert initial bills.')
        for i in range(BenchParams.num_init_bills):
            CreateBillJob(self.pick_random_user(), self.pick_num_users(), self.pick_num_items(), self).run()
        assert self.bill_count == BenchParams.num_init_bills

        # Drain the job queue
        print('>>> Insert initial user-bill relations and bill items.')
        while self.job_queue:
            if len(self.job_queue) % 100 == 0:
                print('>>>>> {} pre-population ops remaining.'.format(len(self.job_queue)))
            self.job_queue.pop(0).run()

    def benchmark(self, scenario):
        while self.op_count <= self.max_ops:
            if not self.job_queue:
                self.add_create_bill_job()
            # Pop job off run queue and run it
            self.job_queue.pop(0).run()

            if self.op_count % BenchParams.create_bill_every_x_ops == 0:
                self.op_count += 1
                print('>>> Queue CreateBill job at position={}.'.format(len(self.job_queue)))
                self.add_create_bill_job()
            if self.op_count % BenchParams.create_user_every_x_ops == 0:
                self.op_count += 1
                self.user_id_gen += 1
                print('>>> Queue CreateUser job at position={}.'.format(len(self.job_queue)))
                self.append_job(CreateUserJob(self.user_id_gen, self))

            if scenario == 1:
                if self.op_count % BenchParams.update_bill_name_every_x_ops == 0:
                    self.append_job(UpdateBillNameJob(self.pick_random_user_with_bill(), 'new random bill name'))
                    self.op_count += 1
            elif scenario == 2:
                if self.op_count % BenchParams.update_bill_item_name_every_x_ops == 0:
                    self.append_job(UpdateBillItemNameJob(self.pick_random_user_with_bill(), 'new random bill item name'))
                    self.op_count += 1


            if self.op_count % 50 == 0:
                print('>>> Completed {} operations.'.format(self.op_count))

    def run(self, scenario_no):
        time_begin_0 = time.time()
        print('Pre-populating database...')
        self.pre_populate()
        print('Done. Start benchmarking.')
        time_begin_1 = time.time()
        self.benchmark(scenario_no)
        time_end = time.time()
        elapsed0 = time_begin_1 - time_begin_0
        elapsed1 = time_end - time_begin_1
        print('Finished.')
        str_time = str(timedelta(seconds=round(elapsed0)))
        print('Pre-population time: {}.'.format(str_time))
        str_time = str(timedelta(seconds=round(elapsed1)))
        print('Elapsed time: {}.'.format(str_time))
        xput = BenchParams.max_operations / elapsed1
        print('Throughput: {0:.2f} operations/sec.'.format(xput))


if __name__ == '__main__':
    scenario_no = 0
    if len(sys.argv) >= 2:
        scenario_no = int(sys.argv[1])

    print('About to start benchmarking.')
    print('!!!WARNING!!! This operation will destroy the existing database.')
    confirmation = input('Continue? (y/n[n])')
    if confirmation not in ['y', 'Y']:
        print('Aborted.')
        exit()

    management.call_command('reset_db', '--noinput')
    management.call_command('migrate')

    print('Starting to execute benchmark, scenario {}.'.format(scenario_no))

    BenchmarkRunner().run(scenario_no)
