import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import RoleChoices, User
from apps.delivery_runs.models import DeliveryRun, RunStatus
from apps.delivery_stops.models import DeliveryStop, StopStatus
from apps.drivers.models import Driver, DriverStatus
from apps.orders.models import Order, OrderPriority, OrderStatus


class Command(BaseCommand):
    help = 'Seed the database with realistic demo data for all apps.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all data (including users and drivers) before seeding.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing all data...')
        else:
            self.stdout.write('Clearing transactional data...')

        DeliveryStop.objects.all().delete()
        DeliveryRun.objects.all().delete()
        Order.objects.all().delete()

        if options['clear']:
            Driver.objects.all().delete()
            User.objects.filter(is_superuser=False).exclude(username='admin').delete()
            self.stdout.write(self.style.WARNING('Cleared all data.'))
        else:
            self.stdout.write('  Cleared orders, runs, and stops.')

        self.stdout.write('Seeding database...\n')

        users = self._create_users()
        drivers = self._create_drivers(users)
        orders = self._create_orders(drivers)
        self._create_delivery_runs(drivers, orders)

        self.stdout.write(self.style.SUCCESS('\nDone! Database seeded successfully.'))
        self._print_summary()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def _create_users(self):
        self.stdout.write('  Creating users...')
        users = {}

        # Manager
        u, _ = User.objects.update_or_create(
            username='manager',
            defaults={
                'email': 'manager@brainwise.com',
                'first_name': 'Sarah',
                'last_name': 'Chen',
                'role': RoleChoices.MANAGER,
                'is_staff': True,
            },
        )
        u.set_password('password123')
        u.save()
        users['manager'] = u

        # Dispatchers
        dispatcher_data = [
            ('dispatcher', 'James', 'Wilson', 'dispatcher@brainwise.com'),
            ('dispatcher2', 'Nadia', 'Saleh', 'dispatcher2@brainwise.com'),
        ]
        for uname, first, last, email in dispatcher_data:
            u, _ = User.objects.update_or_create(
                username=uname,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'role': RoleChoices.DISPATCHER,
                },
            )
            u.set_password('password123')
            u.save()
            users[uname] = u

        # Drivers
        driver_data = [
            ('ahmed', 'Ahmed', 'Hassan', 'ahmed@brainwise.com'),
            ('mona', 'Mona', 'Farouk', 'mona@brainwise.com'),
            ('omar', 'Omar', 'Khaled', 'omar@brainwise.com'),
            ('layla', 'Layla', 'Ibrahim', 'layla@brainwise.com'),
            ('youssef', 'Youssef', 'Nabil', 'youssef@brainwise.com'),
            ('nour', 'Nour', 'El-Din', 'nour@brainwise.com'),
            ('hany', 'Hany', 'Mostafa', 'hany@brainwise.com'),
            ('dalal', 'Dalal', 'Fawzy', 'dalal@brainwise.com'),
        ]
        for uname, first, last, email in driver_data:
            u, _ = User.objects.update_or_create(
                username=uname,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'role': RoleChoices.DRIVER,
                },
            )
            u.set_password('password123')
            u.save()
            users[uname] = u

        self.stdout.write(f'    Created {len(users)} users')
        return users

    # ------------------------------------------------------------------
    # Drivers
    # ------------------------------------------------------------------
    def _create_drivers(self, users):
        self.stdout.write('  Creating driver profiles...')
        drivers = []
        specs = [
            ('ahmed',    '+20-100-234-5678', 10, DriverStatus.AVAILABLE),
            ('mona',     '+20-101-345-6789',  8, DriverStatus.ON_RUN),
            ('omar',     '+20-102-456-7890', 12, DriverStatus.AVAILABLE),
            ('layla',    '+20-103-567-8901',  6, DriverStatus.AVAILABLE),
            ('youssef',  '+20-104-678-9012',  8, DriverStatus.INACTIVE),
            ('nour',     '+20-105-789-0123', 10, DriverStatus.AVAILABLE),
            ('hany',     '+20-106-890-1234',  9, DriverStatus.AVAILABLE),
            ('dalal',    '+20-107-901-2345',  7, DriverStatus.AVAILABLE),
        ]
        for uname, phone, max_stops, status in specs:
            d, _ = Driver.objects.update_or_create(
                user=users[uname],
                defaults={
                    'name': f'{users[uname].first_name} {users[uname].last_name}',
                    'phone_number': phone,
                    'active': (status != DriverStatus.INACTIVE),
                    'max_stops_per_run': max_stops,
                    'status': status,
                },
            )
            drivers.append(d)

        self.stdout.write(f'    Created {len(drivers)} driver profiles')
        return drivers

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def _create_orders(self, drivers):
        self.stdout.write('  Creating orders...')
        orders = []

        customers = [
            ('Fatma Ali',        '+20-111-222-3333'),
            ('Mohamed Salah',    '+20-222-333-4444'),
            ('Hana Youssef',     '+20-333-444-5555'),
            ('Karim Adel',       '+20-444-555-6666'),
            ('Salma Mostafa',    '+20-555-666-7777'),
            ('Tarek Nabil',      '+20-666-777-8888'),
            ('Dina Samir',       '+20-777-888-9999'),
            ('Amr Hussein',      '+20-888-999-0000'),
            ('Mai Ashraf',       '+20-999-000-1111'),
            ('Khaled Omar',      '+20-111-000-2222'),
            ('Rana Mahmoud',     '+20-222-111-3333'),
            ('Hossam Gamal',     '+20-333-222-4444'),
            ('Nada Sherif',      '+20-444-333-5555'),
            ('Walid Reda',       '+20-555-444-6666'),
            ('Yasmin Adel',      '+20-666-555-7777'),
            ('Mahmoud Fathi',    '+20-777-666-8888'),
            ('Heba Khaled',      '+20-888-777-9999'),
            ('Ali Mansour',      '+20-999-888-0000'),
            ('Reem Ashraf',      '+20-112-334-5566'),
            ('Basma Yehia',      '+20-223-445-6677'),
            ('Tamer Rashed',     '+20-334-556-7788'),
            ('Menna Abdelaziz',  '+20-445-667-8899'),
            ('Yasser Ibrahim',   '+20-556-778-9900'),
            ('Sara Hamdy',       '+20-667-889-0011'),
            ('Fady Magdy',       '+20-778-990-1122'),
            ('Nesma Kamal',      '+20-889-001-2233'),
            ('Essam Lotfy',      '+20-990-112-3344'),
            ('Hala Sherif',      '+20-101-223-4455'),
            ('Mostafa Omar',     '+20-202-334-5566'),
            ('Rania Adel',       '+20-303-445-6677'),
        ]

        addresses = [
            '15 El-Tahrir St, Dokki, Giza',
            '42 Nile St, Zamalek, Cairo',
            '7 El-Merghani St, Heliopolis, Cairo',
            '23 El-Thawra St, Shubra, Cairo',
            '8 El-Fath St, Nasr City, Cairo',
            '31 El-Galaa St, Boulaq, Cairo',
            '12 El-Bahr St, Azhar, Cairo',
            '55 El-Maadi St, Maadi, Cairo',
            '3 El-Marghany St, Garden City, Cairo',
            '19 El-Sheikh Zayed St, 6th October',
            '27 El-Mohandesen St, Giza',
            '9 El-Haram St, Faisal, Giza',
            '14 El-Ahram St, Mohandessin, Giza',
            '38 El-Gameaa St, Ain Shams, Cairo',
            '6 El-Khalifa El-Maamoun St, Abbaseya',
            '21 El-Salam St, El-Salam City, Cairo',
            '44 El-Mostakbal St, New Cairo',
            '11 El-Sadat St, Downtown Cairo',
            '2 El-Orman St, Giza',
            '33 El-Batal Ahmed Abd El-Aziz St, Mohandessin',
            '16 El-Thawra St, Heliopolis',
            '50 El-Nasr Rd, Nasr City',
            '8 El-Porch St, Zamalek',
            '26 El-Behoos St, Dokki',
            '4 El-Malek El-Saleh St, Sayeda Zeinab',
            '18 Shagara St, Shubra',
            '39 Abbas El-Akkad St, Nasr City',
            '7 El-Orouba St, Heliopolis',
            '22 Kornish El-Nil, Boulaq',
            '10 El-Madina El-Monawara St, Heliopolis',
        ]

        priorities = list(OrderPriority.values)
        now = timezone.now()

        def _make_order(i, status, driver=None, **kw):
            name, phone = customers[i % len(customers)]
            o = Order(
                customer_name=name,
                customer_phone=phone,
                address=addresses[i % len(addresses)],
                cash_amount=Decimal(str(round(random.uniform(100, 3000), 2))),
                priority=random.choice(priorities),
                status=status,
                assigned_driver=driver,
                **kw,
            )
            o.save()
            orders.append(o)
            return o

        # OPEN — 8 orders waiting to be assigned
        for i in range(8):
            _make_order(i, OrderStatus.OPEN)

        # ASSIGNED — 5 orders assigned to available drivers
        avail = [d for d in drivers if d.status == DriverStatus.AVAILABLE]
        for i in range(5):
            _make_order(8 + i, OrderStatus.ASSIGNED, driver=avail[i % len(avail)])

        # EN_ROUTE — 4 orders on an active run
        active_driver = [d for d in drivers if d.status == DriverStatus.ON_RUN][0]
        for i in range(4):
            _make_order(13 + i, OrderStatus.EN_ROUTE, driver=active_driver)

        # DELIVERED — 6 orders delivered in the past few days
        for i in range(6):
            _make_order(
                17 + i, OrderStatus.DELIVERED,
                driver=drivers[i % len(drivers)],
                delivered_at=now - timedelta(hours=random.randint(2, 72)),
            )

        # FAILED — 3 orders
        for i in range(3):
            _make_order(
                23 + i, OrderStatus.FAILED,
                driver=drivers[i % len(drivers)],
            )

        # CASH_BANKED — 4 orders fully reconciled
        for i in range(4):
            _make_order(
                26 + i, OrderStatus.CASH_BANKED,
                driver=drivers[i % len(drivers)],
                delivered_at=now - timedelta(days=random.randint(2, 5)),
            )

        self.stdout.write(f'    Created {len(orders)} orders')
        return orders

    # ------------------------------------------------------------------
    # Delivery Runs
    # ------------------------------------------------------------------
    def _create_delivery_runs(self, drivers, orders):
        self.stdout.write('  Creating delivery runs...')
        now = timezone.now()
        avail = [d for d in drivers if d.status != DriverStatus.INACTIVE]

        # --- Run 1: DRAFT (no stops yet) ---
        r = DeliveryRun(driver=avail[0], status=RunStatus.DRAFT, total_cash_collected=0)
        r.save()
        self.stdout.write(f'    Run #{r.id} (DRAFT) - {avail[0].name} - 0 stops')

        # --- Run 2: DRAFT with stops ---
        r = DeliveryRun(driver=avail[2], status=RunStatus.DRAFT, total_cash_collected=0)
        r.save()
        open_orders = [o for o in orders if o.status == OrderStatus.OPEN][:3]
        for idx, order in enumerate(open_orders, 1):
            DeliveryStop.objects.create(
                delivery_run=r, order=order, stop_sequence=idx,
                customer_name=order.customer_name, address=order.address,
                cash_amount=order.cash_amount, status=StopStatus.ASSIGNED,
            )
            order.status = OrderStatus.ASSIGNED
            order.assigned_driver = avail[2]
            order.save()
        self.stdout.write(f'    Run #{r.id} (DRAFT) - {avail[2].name} - {len(open_orders)} stops')

        # --- Run 3: ASSIGNED (built, not started) ---
        r = DeliveryRun(driver=avail[3], status=RunStatus.ASSIGNED, total_cash_collected=0)
        r.save()
        assigned_orders = [o for o in orders if o.status == OrderStatus.ASSIGNED][:3]
        for idx, order in enumerate(assigned_orders, 1):
            DeliveryStop.objects.create(
                delivery_run=r, order=order, stop_sequence=idx,
                customer_name=order.customer_name, address=order.address,
                cash_amount=order.cash_amount, status=StopStatus.ASSIGNED,
            )
        self.stdout.write(f'    Run #{r.id} (ASSIGNED) - {avail[3].name} - {len(assigned_orders)} stops')

        # --- Run 4: EN_ROUTE (in progress, some stops delivered) ---
        active_driver = [d for d in drivers if d.status == DriverStatus.ON_RUN][0]
        r = DeliveryRun(
            driver=active_driver, status=RunStatus.EN_ROUTE,
            total_cash_collected=0, started_at=now - timedelta(hours=3),
        )
        r.save()
        en_route_orders = [o for o in orders if o.status == OrderStatus.EN_ROUTE]
        total_cash = Decimal('0')
        for idx, order in enumerate(en_route_orders, 1):
            delivered = idx <= 1
            ds = StopStatus.DELIVERED if delivered else StopStatus.EN_ROUTE
            da = now - timedelta(hours=2) if delivered else None
            if delivered:
                total_cash += order.cash_amount
            DeliveryStop.objects.create(
                delivery_run=r, order=order, stop_sequence=idx,
                customer_name=order.customer_name, address=order.address,
                cash_amount=order.cash_amount, status=ds, delivered_at=da,
            )
        r.total_cash_collected = total_cash
        r.save()
        self.stdout.write(f'    Run #{r.id} (EN_ROUTE) - {active_driver.name} - {len(en_route_orders)} stops')

        # --- Run 5: COMPLETED (all stops done, cash not banked) ---
        driver5 = avail[4] if len(avail) > 4 else avail[0]
        r = DeliveryRun(
            driver=driver5, status=RunStatus.COMPLETED,
            total_cash_collected=0,
            started_at=now - timedelta(days=1, hours=8),
            completed_at=now - timedelta(hours=20),
        )
        r.save()
        delivered_orders = [o for o in orders if o.status == OrderStatus.DELIVERED][:4]
        total_cash = sum(o.cash_amount for o in delivered_orders)
        r.total_cash_collected = total_cash
        r.save()
        for idx, order in enumerate(delivered_orders, 1):
            DeliveryStop.objects.create(
                delivery_run=r, order=order, stop_sequence=idx,
                customer_name=order.customer_name, address=order.address,
                cash_amount=order.cash_amount, status=StopStatus.DELIVERED,
                delivered_at=now - timedelta(hours=22 + idx),
            )
        self.stdout.write(f'    Run #{r.id} (COMPLETED) - {driver5.name} - {len(delivered_orders)} stops')

        # --- Run 6: CASH_BANKED (fully reconciled) ---
        driver6 = avail[5] if len(avail) > 5 else avail[1]
        r = DeliveryRun(
            driver=driver6, status=RunStatus.CASH_BANKED,
            total_cash_collected=0,
            started_at=now - timedelta(days=4),
            completed_at=now - timedelta(days=3, hours=6),
            cash_banked_at=now - timedelta(days=3),
            cash_banked_location='Main Branch - Nile Street',
        )
        r.save()
        banked_orders = [o for o in orders if o.status == OrderStatus.CASH_BANKED]
        total_cash = sum(o.cash_amount for o in banked_orders)
        r.total_cash_collected = total_cash
        r.save()
        for idx, order in enumerate(banked_orders, 1):
            DeliveryStop.objects.create(
                delivery_run=r, order=order, stop_sequence=idx,
                customer_name=order.customer_name, address=order.address,
                cash_amount=order.cash_amount, status=StopStatus.DELIVERED,
                delivered_at=now - timedelta(days=3, hours=8 + idx),
            )
        self.stdout.write(f'    Run #{r.id} (CASH_BANKED) - {driver6.name} - {len(banked_orders)} stops')

        # --- Run 7: CASH_BANKED (second reconciled run) ---
        driver7 = avail[6] if len(avail) > 6 else avail[0]
        r = DeliveryRun(
            driver=driver7, status=RunStatus.CASH_BANKED,
            total_cash_collected=0,
            started_at=now - timedelta(days=6),
            completed_at=now - timedelta(days=5, hours=10),
            cash_banked_at=now - timedelta(days=5),
            cash_banked_location='Heliopolis Branch',
        )
        r.save()
        # Reuse some delivered orders for this historical run
        extra_orders = [o for o in orders if o.status == OrderStatus.DELIVERED][2:4]
        total_cash = sum(o.cash_amount for o in extra_orders)
        r.total_cash_collected = total_cash
        r.save()
        for idx, order in enumerate(extra_orders, 1):
            DeliveryStop.objects.create(
                delivery_run=r, order=order, stop_sequence=idx,
                customer_name=order.customer_name, address=order.address,
                cash_amount=order.cash_amount, status=StopStatus.DELIVERED,
                delivered_at=now - timedelta(days=5, hours=12 + idx),
            )
        self.stdout.write(f'    Run #{r.id} (CASH_BANKED) - {driver7.name} - {len(extra_orders)} stops')

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def _print_summary(self):
        self.stdout.write('\n' + '=' * 55)
        self.stdout.write(self.style.SUCCESS('  SEED DATA SUMMARY'))
        self.stdout.write('=' * 55)
        self.stdout.write(f'  Users:      {User.objects.count()}')
        self.stdout.write(f'  Drivers:    {Driver.objects.count()}')
        self.stdout.write(f'  Orders:     {Order.objects.count()}')
        self.stdout.write(f'  Runs:       {DeliveryRun.objects.count()}')
        self.stdout.write(f'  Stops:      {DeliveryStop.objects.count()}')
        self.stdout.write('=' * 55)
        self.stdout.write('\n  Login credentials (all passwords: password123):')
        self.stdout.write('  ' + '-' * 51)
        self.stdout.write('  Manager:     manager@brainwise.com')
        self.stdout.write('  Dispatcher:  dispatcher@brainwise.com')
        self.stdout.write('  Dispatcher2: dispatcher2@brainwise.com')
        self.stdout.write('')
        self.stdout.write('  Drivers:')
        for u in User.objects.filter(role=RoleChoices.DRIVER).order_by('username'):
            self.stdout.write(f'    {u.email:<30} ({u.first_name} {u.last_name})')
        self.stdout.write('=' * 55 + '\n')
