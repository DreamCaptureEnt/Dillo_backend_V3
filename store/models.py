from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        abstract = True
 
 
# ── Taxonomy ──────────────────────────────────────────────────────────────────
 
class SareeCategory(TimeStampedModel):
    name      = models.CharField(max_length=120)
    name_ta   = models.CharField(max_length=160, blank=True, default='')
    slug      = models.SlugField(max_length=140, unique=True)
    icon      = models.CharField(max_length=24, blank=True, default='')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
 
    class Meta:
        ordering = ['sort_order', 'name']
 
    def __str__(self):
        return self.name
 
 
class OccasionCategory(TimeStampedModel):
    name      = models.CharField(max_length=120, unique=True)
    slug      = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
 
    class Meta:
        ordering = ['sort_order', 'name']
 
    def __str__(self):
        return self.name


class ProductNameOption(TimeStampedModel):
    name = models.CharField(max_length=180, unique=True)
    name_ta = models.CharField(max_length=220, blank=True, default='')
    slug = models.SlugField(max_length=220, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class SareeTypeOption(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    name_ta = models.CharField(max_length=160, blank=True, default='')
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ProductInfoOption(TimeStampedModel):
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=220)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'label', 'value']
        unique_together = ('label', 'value')

    def __str__(self):
        return f"{self.label}: {self.value}"


class CustomerProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return f"{self.user.username} profile"


class HomeScreenImage(TimeStampedModel):
    title = models.CharField(max_length=180, blank=True, default='')
    title_ta = models.CharField(max_length=220, blank=True, default='')
    subtitle = models.CharField(max_length=240, blank=True, default='')
    badge = models.CharField(max_length=120, blank=True, default='')
    cta_label = models.CharField(max_length=80, blank=True, default='')
    cta_url = models.CharField(max_length=180, blank=True, default='/products')
    landscape_image = models.CharField(max_length=180, blank=True, default='')
    portrait_image = models.CharField(max_length=180, blank=True, default='')
    caption_label = models.CharField(max_length=120, blank=True, default='')
    caption_subtitle = models.CharField(max_length=160, blank=True, default='')
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title or self.caption_label or f'Home screen image {self.pk}'
 
 
# ── Product ───────────────────────────────────────────────────────────────────
 
class Saree(TimeStampedModel):
    category       = models.ForeignKey(SareeCategory, on_delete=models.PROTECT)
    occasion       = models.ForeignKey(OccasionCategory, on_delete=models.PROTECT)
    product_code   = models.CharField(max_length=32, unique=True, blank=True, null=True)
    name           = models.CharField(max_length=180)
    name_ta        = models.CharField(max_length=220, blank=True, default='')
    slug           = models.SlugField(max_length=220, unique=True)
    saree_type     = models.CharField(max_length=120, blank=True, default='')
    description    = models.TextField(blank=True, default='')
    information    = models.JSONField(default=dict)
    tags           = models.JSONField(default=list)
    colors         = models.JSONField(default=list)
    images         = models.JSONField(default=list)
    video_url      = models.URLField(max_length=200, blank=True, default='')
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount       = models.PositiveIntegerField(default=0)
    stock_count    = models.PositiveIntegerField(default=0)
    rating         = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count   = models.PositiveIntegerField(default=0)
    is_new         = models.BooleanField(default=False)
    is_featured    = models.BooleanField(default=False)
    is_bestseller  = models.BooleanField(default=False)
    is_active      = models.BooleanField(default=True)
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return self.name

    @staticmethod
    def make_product_code(pk):
        return f"DILLO-{pk:05d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.product_code and self.pk:
            self.product_code = self.make_product_code(self.pk)
            super().save(update_fields=['product_code', 'updated_at'])
 
 
# ── Cart ──────────────────────────────────────────────────────────────────────
 
class Cart(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
 
    def __str__(self):
        return f"Cart of {self.user.username}"
 
 
class CartItem(TimeStampedModel):
    cart           = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    saree          = models.ForeignKey(Saree, on_delete=models.CASCADE)
    selected_color = models.CharField(max_length=80, blank=True, default='')
    selected_size  = models.CharField(max_length=80, blank=True, default='')
    quantity       = models.PositiveIntegerField(default=1)
 
    class Meta:
        unique_together = ('cart', 'saree', 'selected_color', 'selected_size')
 
 
# ── Order ─────────────────────────────────────────────────────────────────────
 
class Order(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('packed',    'Packed'),
        ('shipped',   'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cod',    'Cash on Delivery'),
        ('upi',    'UPI'),
        ('card',   'Card'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Wallet'),
        ('other',  'Other'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('paid',     'Paid'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ]
    SOURCE_CHOICES = [
        ('website',       'Website'),
        ('video_shopping','Video Shopping'),
        ('live_show',     'Live Show'),
        ('whatsapp',      'WhatsApp'),
        ('phone',         'Phone'),
        ('other',         'Other'),
    ]
 
    user             = models.ForeignKey(User, on_delete=models.PROTECT)
    order_number     = models.CharField(max_length=32, unique=True)
    status           = models.CharField(max_length=24, choices=STATUS_CHOICES, default='pending')
    payment_method   = models.CharField(max_length=40, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status   = models.CharField(max_length=24, choices=PAYMENT_STATUS_CHOICES, default='pending')
    shipping_address = models.JSONField(default=dict)
    subtotal         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes            = models.TextField(blank=True, default='')
    # New fields for order source tracking
    order_source     = models.CharField(max_length=40, choices=SOURCE_CHOICES, default='website')
    device_info      = models.CharField(max_length=200, blank=True, default='')
    ip_address       = models.GenericIPAddressField(null=True, blank=True)
    coupon_code      = models.CharField(max_length=40, blank=True, default='')
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return self.order_number
 
 
class OrderItem(TimeStampedModel):
    order            = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    saree            = models.ForeignKey(Saree, on_delete=models.SET_NULL, null=True)
    product_snapshot = models.JSONField(default=dict)
    selected_color   = models.CharField(max_length=80, blank=True, default='')
    selected_size    = models.CharField(max_length=80, blank=True, default='')
    quantity         = models.PositiveIntegerField(default=1)
    price            = models.DecimalField(max_digits=10, decimal_places=2)
 
    def __str__(self):
        return f"{self.quantity}x {self.product_snapshot.get('name','?')} in {self.order.order_number}"
 
 
# ── Review ────────────────────────────────────────────────────────────────────
 
class Review(TimeStampedModel):
    saree       = models.ForeignKey(Saree, on_delete=models.CASCADE, related_name='reviews')
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    rating      = models.PositiveSmallIntegerField()
    title       = models.CharField(max_length=160, blank=True, default='')
    content     = models.TextField(blank=True, default='')
    is_approved = models.BooleanField(default=False)
 
    class Meta:
        unique_together = ('saree', 'user')
 
 
# ── Wishlist ──────────────────────────────────────────────────────────────────
 
class WishlistItem(TimeStampedModel):
    user  = models.ForeignKey(User, on_delete=models.CASCADE)
    saree = models.ForeignKey(Saree, on_delete=models.CASCADE)
 
    class Meta:
        unique_together = ('user', 'saree')
 
 
# ── Address ───────────────────────────────────────────────────────────────────
 
class Address(TimeStampedModel):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=80)
    last_name  = models.CharField(max_length=80)
    email      = models.EmailField()
    phone      = models.CharField(max_length=32)
    address    = models.TextField()
    landmark   = models.CharField(max_length=180, blank=True, default='')
    city       = models.CharField(max_length=100)
    state      = models.CharField(max_length=100)
    pincode    = models.CharField(max_length=12)
    is_default = models.BooleanField(default=False)
 
 
# ── Video Shopping Slot ───────────────────────────────────────────────────────
 
class VideoShoppingSlot(TimeStampedModel):
    """A 30-minute video shopping appointment booked by a customer."""
    STATUS_CHOICES = [
        ('pending',   'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show',   'No Show'),
    ]
 
    name         = models.CharField(max_length=180)
    email        = models.EmailField()
    phone        = models.CharField(max_length=32, blank=True, default='')
    slot_date    = models.DateField()
    slot_time    = models.TimeField()          # start time; 30 min duration implied
    status       = models.CharField(max_length=24, choices=STATUS_CHOICES, default='pending')
    # Meet link sent to customer
    meet_link    = models.URLField(max_length=300, blank=True, default='')
    # Internal notes from admin
    notes        = models.TextField(blank=True, default='')
    # Confirmation email sent flag
    email_sent   = models.BooleanField(default=False)
    # Optional: linked user account
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
 
    class Meta:
        ordering = ['slot_date', 'slot_time']
        unique_together = ('slot_date', 'slot_time')  # prevent double-booking
 
    def __str__(self):
        return f"{self.name} — {self.slot_date} {self.slot_time}"


# Add this to backend/store/models.py  (append to the bottom of the file)

class VideoShoppingBooking(TimeStampedModel):
    """A 30-minute video-shopping slot booked by a customer."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    name = models.CharField(max_length=180)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    date = models.DateField()
    time_slot = models.CharField(max_length=5)   # "HH:MM"  e.g. "09:00"
    note = models.TextField(blank=True)
    meet_link = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    attendee_name = models.CharField(max_length=180, blank=True, default="")

    class Meta:
        # Prevent double-booking the same slot
        unique_together = ("date", "time_slot")
        ordering = ["date", "time_slot"]

    def __str__(self):
        return f"{self.name} — {self.date} {self.time_slot}"

    @property
    def time_slot_display(self):
        """Return a human-readable label such as '9:00 AM'."""
        hour, minute = map(int, self.time_slot.split(":"))
        ampm = "AM" if hour < 12 else "PM"
        h12 = hour % 12 or 12
        return f"{h12}:{minute:02d} {ampm}"
