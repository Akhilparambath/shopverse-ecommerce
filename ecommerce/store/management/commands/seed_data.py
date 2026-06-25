from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from store.models import Category, Product, UserProfile, Order, OrderItem, Cart
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seeds the database with categories, products, admin, and a test customer'

    def handle(self, *args, **kwargs):
        self.stdout.write("Flushing existing data...")
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Cart.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        UserProfile.objects.all().delete()
        
        # Keep superusers or recreate admin? Let's delete existing ones to avoid duplicates
        User.objects.filter(username__in=['admin', 'customer']).delete()

        self.stdout.write("Creating Users...")
        # Create Admin User
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@shop.com',
            password='admin123',
            first_name='Admin',
            last_name='ShopVerse'
        )
        UserProfile.objects.create(
            user=admin_user,
            phone='9876543210',
            address='Admin Headquarters, Suite 101',
            city='Mumbai',
            state='Maharashtra',
            pincode='400001'
        )
        self.stdout.write("Admin User created (admin@shop.com / admin123)")

        # Create Customer User
        customer_user = User.objects.create_user(
            username='customer',
            email='customer@shop.com',
            password='customer123',
            first_name='John',
            last_name='Doe'
        )
        UserProfile.objects.create(
            user=customer_user,
            phone='9876543211',
            address='123 Green Street, Apartment 4B',
            city='Bengaluru',
            state='Karnataka',
            pincode='560001'
        )
        self.stdout.write("Customer User created (customer@shop.com / customer123)")

        # Categories
        categories_data = [
            {'name': 'Electronics', 'description': 'Gadgets, smartphones, smartwatches, and audio equipment.'},
            {'name': 'Fashion', 'description': 'Sleek jackets, casual shirts, and sportswear.'},
            {'name': 'Home & Living', 'description': 'Comfortable furniture, lamps, and study accessories.'},
            {'name': 'Books', 'description': 'Self-help, business, and software engineering books.'},
        ]

        categories = {}
        for cat_data in categories_data:
            cat = Category.objects.create(
                name=cat_data['name'],
                description=cat_data['description'],
                slug=slugify(cat_data['name'])
            )
            categories[cat_data['name']] = cat
            self.stdout.write(f"Category '{cat.name}' created.")

        # Products
        products_data = [
            # Electronics
            {
                'name': 'Smartphone SV-10',
                'description': 'A premium smartphone with 120Hz OLED display, 108MP camera, and 5G connectivity.',
                'category': 'Electronics',
                'price': 49999.00,
                'stock': 15,
            },
            {
                'name': 'Wireless Noise Cancelling Headphones',
                'description': 'Studio-grade sound quality with active noise cancellation and 40-hour battery life.',
                'category': 'Electronics',
                'price': 14999.00,
                'stock': 25,
            },
            {
                'name': 'Smartwatch Series X',
                'description': 'Track your health, fitness goals, and notifications with a sleek titanium smartwatch.',
                'category': 'Electronics',
                'price': 9999.00,
                'stock': 10,
            },
            # Fashion
            {
                'name': 'Classic Leather Jacket',
                'description': 'Genuine dark brown leather jacket with robust zippers and a timeless vintage fit.',
                'category': 'Fashion',
                'price': 5999.00,
                'stock': 8,
            },
            {
                'name': 'Cotton Casual Shirt',
                'description': 'Breathable, lightweight linen-cotton blend shirt perfect for semi-formal and casual wear.',
                'category': 'Fashion',
                'price': 1499.00,
                'stock': 50,
            },
            {
                'name': 'Running Sports Shoes',
                'description': 'High-performance running shoes with responsive foam cushioning and breathable mesh.',
                'category': 'Fashion',
                'price': 3499.00,
                'stock': 30,
            },
            # Home & Living
            {
                'name': 'Ergonomic Office Chair',
                'description': 'High-back mesh office chair with lumbar support, 3D armrests, and synchro-tilt mechanism.',
                'category': 'Home & Living',
                'price': 12999.00,
                'stock': 12,
            },
            {
                'name': 'Minimalist Desk Lamp',
                'description': 'Dimmable LED desk lamp with adjustable arm, wireless charging base, and color temp controls.',
                'category': 'Home & Living',
                'price': 1999.00,
                'stock': 20,
            },
            {
                'name': 'Ceramic Coffee Mug Set',
                'description': 'Handcrafted ceramic mugs (set of 4) in organic earth tones. Microwave and dishwasher safe.',
                'category': 'Home & Living',
                'price': 999.00,
                'stock': 40,
            },
            # Books
            {
                'name': 'The Pragmatic Programmer',
                'description': 'Your journey to mastery. One of the most significant books on software engineering.',
                'category': 'Books',
                'price': 2999.00,
                'stock': 15,
            },
            {
                'name': 'Atomic Habits',
                'description': 'An easy and proven way to build good habits and break bad ones by James Clear.',
                'category': 'Books',
                'price': 799.00,
                'stock': 100,
            },
            {
                'name': 'Zero to One',
                'description': 'Notes on Startups, or How to Build the Future by Peter Thiel.',
                'category': 'Books',
                'price': 699.00,
                'stock': 50,
            },
        ]

        for prod_data in products_data:
            cat = categories[prod_data['category']]
            prod = Product.objects.create(
                name=prod_data['name'],
                description=prod_data['description'],
                category=cat,
                price=prod_data['price'],
                stock=prod_data['stock']
            )
            self.stdout.write(f"Product '{prod.name}' added to '{cat.name}'.")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
