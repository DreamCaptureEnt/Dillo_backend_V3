from django.core.management.base import BaseCommand
from django.utils.text import slugify

from store.models import OccasionCategory, Saree, SareeCategory


SAREE_TYPES = [
    'Kanjivaram', 'Banarasi', 'Chanderi', 'Mysore Silk', 'Tussar',
    'Patola', 'Pochampally', 'Gadwal', 'Venkatagiri', 'Dharmavaram',
]

OCCASIONS = ['Wedding', 'Festival', 'Party', 'Casual', 'Office', 'Bridal']

PRODUCTS = [
    {
        'name': 'Kanjivaram Pure Silk Saree',
        'saree_type': 'Kanjivaram',
        'occasion': 'Wedding',
        'price': 12500,
        'original_price': 16000,
        'discount': 22,
        'colors': ['Red', 'Gold'],
        'stock_count': 8,
        'rating': 4.8,
        'review_count': 124,
        'is_featured': True,
        'is_bestseller': True,
        'description': 'Exquisite Kanjivaram pure silk saree with traditional zari work, temple borders, and a rich pallu.',
        'information': {'fabric': 'Pure Mulberry Silk', 'length': '6.5 meters', 'zari': 'Pure Gold Zari', 'care': 'Dry clean only'},
    },
    {
        'name': 'Banarasi Silk Saree',
        'saree_type': 'Banarasi',
        'occasion': 'Wedding',
        'price': 8900,
        'original_price': 11000,
        'discount': 19,
        'colors': ['Purple', 'Gold'],
        'stock_count': 12,
        'rating': 4.6,
        'review_count': 89,
        'is_new': True,
        'is_featured': True,
        'description': 'Luxurious Banarasi silk saree with intricate brocade work and fine gold thread weaving.',
        'information': {'fabric': 'Pure Banarasi Silk', 'length': '6.5 meters', 'zari': 'Silver and Gold Zari', 'care': 'Dry clean only'},
    },
    {
        'name': 'Chanderi Silk Cotton Saree',
        'saree_type': 'Chanderi',
        'occasion': 'Festival',
        'price': 4200,
        'original_price': 5500,
        'discount': 24,
        'colors': ['Pink', 'Gold'],
        'stock_count': 20,
        'rating': 4.5,
        'review_count': 67,
        'is_new': True,
        'is_bestseller': True,
        'description': 'Lightweight Chanderi silk cotton saree for festive occasions with delicate motifs.',
        'information': {'fabric': 'Silk-Cotton Blend', 'length': '6.3 meters', 'care': 'Gentle machine wash'},
    },
    {
        'name': 'Mysore Pure Silk Saree',
        'saree_type': 'Mysore Silk',
        'occasion': 'Party',
        'price': 6800,
        'original_price': 8200,
        'discount': 17,
        'colors': ['Blue', 'Gold'],
        'stock_count': 5,
        'rating': 4.7,
        'review_count': 45,
        'is_featured': True,
        'description': 'Classic Mysore silk saree known for soft texture and subtle sheen.',
        'information': {'fabric': 'Pure Mysore Silk', 'length': '6.5 meters', 'care': 'Dry clean only'},
    },
    {
        'name': 'Dharmavaram Silk Saree',
        'saree_type': 'Dharmavaram',
        'occasion': 'Bridal',
        'price': 9500,
        'original_price': 12000,
        'discount': 21,
        'colors': ['Maroon', 'Gold'],
        'stock_count': 4,
        'rating': 4.9,
        'review_count': 203,
        'is_featured': True,
        'is_bestseller': True,
        'description': 'Premium Dharmavaram silk saree with traditional motifs and heavy zari work.',
        'information': {'fabric': 'Pure Dharmavaram Silk', 'length': '6.5 meters', 'zari': 'Pure Gold Zari'},
    },
]


class Command(BaseCommand):
    help = 'Seed starter categories, occasions, and saree products.'

    def handle(self, *args, **options):
        category, _ = SareeCategory.objects.update_or_create(
            slug='sarees',
            defaults={'name': 'Sarees', 'icon': 'saree', 'is_active': True},
        )
        for index, name in enumerate(OCCASIONS):
            OccasionCategory.objects.update_or_create(
                slug=slugify(name),
                defaults={'name': name, 'sort_order': index, 'is_active': True},
            )

        images = [
            'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&q=80',
            'https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&q=80',
        ]
        for product in PRODUCTS:
            occasion = OccasionCategory.objects.get(name=product.pop('occasion'))
            Saree.objects.update_or_create(
                slug=slugify(product['name']),
                defaults={
                    **product,
                    'category': category,
                    'occasion': occasion,
                    'images': images,
                    'tags': [product['saree_type'].lower(), occasion.name.lower(), 'saree'],
                    'is_active': True,
                },
            )

        self.stdout.write(self.style.SUCCESS('Seeded store data.'))
