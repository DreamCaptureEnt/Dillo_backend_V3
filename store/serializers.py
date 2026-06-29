from decimal import Decimal
import os
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.files.storage import default_storage
from django.db.models import Q
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.text import slugify
from rest_framework import serializers
import datetime

from .models import (
    Address,
    Cart,
    CartItem,
    CustomerProfile,
    HomeScreenImage,
    OccasionCategory,
    Order,
    OrderItem,
    ProductInfoOption,
    ProductNameOption,
    Review,
    Saree,
    SareeCategory,
    SareeTypeOption,
    WishlistItem,
)

User = get_user_model()

MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_PRODUCT_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_PRODUCT_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
HOME_SCREEN_IMAGE_ROOTS = {
    'landscape': 'home_screen_images/landscape',
    'portrait': 'home_screen_images/portraits',
}


def _normalize_media_reference(value):
    if not isinstance(value, str):
        return value

    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    parsed = urlparse(value)
    path = parsed.path if parsed.scheme and parsed.netloc else value

    if path.startswith(media_url):
        return path[len(media_url):].lstrip('/')
    return value


def _build_image_url(request, value):
    if not isinstance(value, str) or not value:
        return value
    if value.startswith(('http://', 'https://', 'data:')):
        return value

    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    path = value if value.startswith(media_url) else f"{media_url}{value.lstrip('/')}"
    return request.build_absolute_uri(path) if request else path


def _validate_product_image(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_PRODUCT_IMAGE_EXTENSIONS:
        raise serializers.ValidationError(
            'Only JPG, JPEG, PNG, and WebP product images are allowed.'
        )
    if file_obj.size > MAX_PRODUCT_IMAGE_SIZE:
        raise serializers.ValidationError('Each product image must be less than 5 MB.')

    content_type = getattr(file_obj, 'content_type', '')
    if content_type and content_type not in ALLOWED_PRODUCT_IMAGE_TYPES:
        raise serializers.ValidationError(
            'Only JPG, JPEG, PNG, and WebP product images are allowed.'
        )


def _save_product_image(saree, file_obj):
    _validate_product_image(file_obj)

    category = slugify(getattr(saree.category, 'slug', '') or saree.category.name) or 'category'
    saree_type = slugify(saree.saree_type) or 'subcategory'
    product = slugify(saree.slug or saree.name) or f'product-{saree.pk}'
    ext = os.path.splitext(file_obj.name)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    path = f"products/{category}/{saree_type}/{product}/{filename}"

    return default_storage.save(path, file_obj)


def _validate_home_screen_image(file_obj):
    _validate_product_image(file_obj)


def _save_home_screen_image(file_obj, orientation):
    _validate_home_screen_image(file_obj)
    ext = os.path.splitext(file_obj.name)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    root = HOME_SCREEN_IMAGE_ROOTS[orientation]
    saved_path = default_storage.save(f"{root}/{filename}", file_obj)
    return os.path.basename(saved_path)


def _build_home_screen_image_url(request, filename, orientation):
    if not filename:
        return ''
    if filename.startswith(('http://', 'https://', 'data:')):
        return filename
    root = HOME_SCREEN_IMAGE_ROOTS[orientation]
    return _build_image_url(request, f"{root}/{filename}")


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source='profile.phone', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'is_staff', 'is_active', 'date_joined']
        read_only_fields = ['id', 'is_staff', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    phone = serializers.CharField(write_only=True, max_length=32)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'password']

    def validate_phone(self, value):
        phone = value.strip()
        if not phone:
            raise serializers.ValidationError('Phone number is required.')
        if CustomerProfile.objects.filter(phone__iexact=phone).exists():
            raise serializers.ValidationError('This phone number is already registered.')
        return phone

    def validate_email(self, value):
        email = (value or '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('This email is already registered.')
        return email

    def create(self, validated_data):
        password = validated_data.pop('password')
        phone = validated_data.pop('phone')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        CustomerProfile.objects.create(user=user, phone=phone)
        Cart.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    identifier = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = (attrs.get('identifier') or attrs.get('username') or '').strip()
        if not identifier:
            raise serializers.ValidationError('Enter your username, email, or phone number.')

        user_obj = (
            User.objects
            .filter(Q(username__iexact=identifier) | Q(email__iexact=identifier) | Q(profile__phone__iexact=identifier))
            .first()
        )
        username = user_obj.username if user_obj else identifier
        user = authenticate(username=username, password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid login details or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account is inactive.')
        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs['identifier'].strip()
        user = (
            User.objects
            .filter(Q(username__iexact=identifier) | Q(email__iexact=identifier) | Q(profile__phone__iexact=identifier))
            .first()
        )
        attrs['user'] = user
        attrs['identifier'] = identifier
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError('Invalid password reset link.')

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError('Invalid or expired password reset link.')
        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['password'])
        user.save(update_fields=['password'])
        return user


class HomeScreenImageSerializer(serializers.ModelSerializer):
    landscape_url = serializers.SerializerMethodField()
    portrait_url = serializers.SerializerMethodField()

    class Meta:
        model = HomeScreenImage
        fields = [
            'id', 'title', 'title_ta', 'subtitle', 'badge', 'cta_label', 'cta_url',
            'landscape_image', 'portrait_image', 'landscape_url', 'portrait_url',
            'caption_label', 'caption_subtitle', 'sort_order', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['landscape_url', 'portrait_url', 'created_at', 'updated_at']

    def get_landscape_url(self, obj):
        return _build_home_screen_image_url(self.context.get('request'), obj.landscape_image, 'landscape')

    def get_portrait_url(self, obj):
        return _build_home_screen_image_url(self.context.get('request'), obj.portrait_image, 'portrait')

    def _attach_uploaded_images(self, instance):
        landscape_file = self.context.get('landscape_file')
        portrait_file = self.context.get('portrait_file')
        update_fields = []
        if landscape_file:
            instance.landscape_image = _save_home_screen_image(landscape_file, 'landscape')
            update_fields.append('landscape_image')
        if portrait_file:
            instance.portrait_image = _save_home_screen_image(portrait_file, 'portrait')
            update_fields.append('portrait_image')
        if update_fields:
            instance.save(update_fields=[*update_fields, 'updated_at'])
        return instance

    def create(self, validated_data):
        instance = super().create(validated_data)
        return self._attach_uploaded_images(instance)

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return self._attach_uploaded_images(instance)


class SareeCategorySerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(source='sarees.count', read_only=True)

    class Meta:
        model = SareeCategory
        fields = ['id', 'name', 'slug', 'name_ta', 'icon', 'is_active', 'sort_order', 'count']


class OccasionCategorySerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(source='sarees.count', read_only=True)

    class Meta:
        model = OccasionCategory
        fields = ['id', 'name', 'slug', 'is_active', 'sort_order', 'count']


class ProductNameOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductNameOption
        fields = ['id', 'name', 'name_ta', 'slug', 'is_active', 'sort_order', 'created_at', 'updated_at']


class SareeTypeOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SareeTypeOption
        fields = ['id', 'name', 'name_ta', 'slug', 'is_active', 'sort_order', 'created_at', 'updated_at']


class ProductInfoOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductInfoOption
        fields = ['id', 'label', 'value', 'is_active', 'sort_order', 'created_at', 'updated_at']


class SareeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    occasion_name = serializers.CharField(source='occasion.name', read_only=True)
    occasion_slug = serializers.CharField(source='occasion.slug', read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    images = serializers.SerializerMethodField()
    image_paths = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Saree
        fields = [
            'id', 'product_code', 'name', 'name_ta', 'slug', 'category', 'category_name', 'category_slug',
            'occasion', 'occasion_name', 'occasion_slug', 'saree_type', 'description',
            'information', 'tags', 'colors', 'images', 'image_paths', 'video_url', 'price', 'original_price',
            'discount', 'stock_count', 'in_stock', 'rating', 'review_count', 'is_new',
            'is_featured', 'is_bestseller', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['product_code']

    def get_images(self, obj):
        request = self.context.get('request')
        return [_build_image_url(request, item) for item in (obj.images or [])]

    def validate_image_paths(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Images must be a list.')

        normalized = []
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError('Each image must be a URL or media path.')
            if item.startswith('data:'):
                raise serializers.ValidationError('Image files must be uploaded, not saved as base64 data.')
            normalized.append(_normalize_media_reference(item))
        return normalized

    def _attach_uploaded_images(self, saree):
        uploaded_images = self.context.get('uploaded_images') or []
        if not uploaded_images:
            return saree

        paths = list(saree.images or [])
        for file_obj in uploaded_images:
            paths.append(_save_product_image(saree, file_obj))
        saree.images = paths
        saree.save(update_fields=['images', 'updated_at'])
        return saree

    def create(self, validated_data):
        image_paths = validated_data.pop('image_paths', [])
        saree = super().create({**validated_data, 'images': image_paths})
        return self._attach_uploaded_images(saree)

    def update(self, instance, validated_data):
        image_paths = validated_data.pop('image_paths', None)
        saree = super().update(instance, validated_data)
        if image_paths is not None:
            saree.images = image_paths
            saree.save(update_fields=['images', 'updated_at'])
        return self._attach_uploaded_images(saree)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'address', 'landmark', 'city', 'state', 'pincode', 'is_default']

    def create(self, validated_data):
        return Address.objects.create(user=self.context['request'].user, **validated_data)


class CartItemSerializer(serializers.ModelSerializer):
    saree_detail = SareeSerializer(source='saree', read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'saree', 'saree_detail', 'selected_color', 'selected_size', 'quantity', 'line_total']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'subtotal']

    def get_subtotal(self, obj):
        return sum((item.line_total for item in obj.items.select_related('saree')), Decimal('0'))


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'saree', 'product_snapshot', 'selected_color', 'selected_size', 'quantity', 'price', 'line_total']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_detail = UserSerializer(source='user', read_only=True)
    ip_address = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=45)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_detail', 'status', 'payment_method',
            'payment_status', 'shipping_address', 'subtotal', 'discount', 'shipping',
            'total', 'notes', 'order_source', 'device_info', 'ip_address',
            'coupon_code', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['order_number', 'user']


class CreateOrderItemSerializer(serializers.Serializer):
    saree = serializers.PrimaryKeyRelatedField(queryset=Saree.objects.filter(is_active=True))
    selected_color = serializers.CharField(required=False, allow_blank=True)
    selected_size = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    items = CreateOrderItemSerializer(many=True)
    shipping_address = serializers.JSONField()
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES, default='cod')
    order_source = serializers.ChoiceField(choices=Order.SOURCE_CHOICES, default='website')
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = serializers.CharField(required=False, allow_blank=True, max_length=40)
    device_info = serializers.CharField(required=False, allow_blank=True, max_length=200)
    notes = serializers.CharField(required=False, allow_blank=True)


class ReviewSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'saree', 'user', 'user_detail', 'rating', 'title', 'content', 'is_approved', 'created_at']
        read_only_fields = ['user', 'is_approved']

    def create(self, validated_data):
        return Review.objects.create(user=self.context['request'].user, **validated_data)


class WishlistItemSerializer(serializers.ModelSerializer):
    saree_detail = SareeSerializer(source='saree', read_only=True)

    class Meta:
        model = WishlistItem
        fields = ['id', 'saree', 'saree_detail', 'created_at']

    def create(self, validated_data):
        item, _ = WishlistItem.objects.get_or_create(user=self.context['request'].user, **validated_data)
        return item


class VideoShoppingBookingSerializer(serializers.ModelSerializer):
    time_slot_display = serializers.ReadOnlyField()
 
    class Meta:
        from store.models import VideoShoppingBooking  # lazy import for standalone snippet
        model = VideoShoppingBooking
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "date",
            "time_slot",
            "time_slot_display",
            "note",
            "meet_link",
            "status",
            "attendee_name",
            "created_at",
        ]
        read_only_fields = ["id", "meet_link", "status", "created_at", "time_slot_display"]
 
    # ── Validation ────────────────────────────────────────────────────────────
 
    def validate_date(self, value):
        today = datetime.date.today()
        if value <= today:
            raise serializers.ValidationError("Please choose a future date (from tomorrow onwards).")
        return value
 
    def validate_time_slot(self, value):
        """Accept only valid 30-min slots between 09:00 and 20:30."""
        valid_slots = set()
        h, m = 9, 0
        while h < 20 or (h == 20 and m <= 30):
            valid_slots.add(f"{h:02d}:{m:02d}")
            m += 30
            if m >= 60:
                m = 0
                h += 1
        if value not in valid_slots:
            raise serializers.ValidationError(
                f"Invalid slot '{value}'. Must be a 30-minute interval between 09:00 and 20:30."
            )
        return value
 
    def validate(self, attrs):
        from store.models import VideoShoppingBooking
        date = attrs.get("date")
        time_slot = attrs.get("time_slot")
        if date and time_slot:
            if VideoShoppingBooking.objects.filter(date=date, time_slot=time_slot).exists():
                raise serializers.ValidationError(
                    {"time_slot": "This slot is already booked. Please choose a different time."}
                )
        return attrs


class AdminVideoShoppingBookingSerializer(VideoShoppingBookingSerializer):
    class Meta(VideoShoppingBookingSerializer.Meta):
        fields = VideoShoppingBookingSerializer.Meta.fields + ["updated_at"]
        read_only_fields = [
            "id",
            "name",
            "email",
            "phone",
            "date",
            "time_slot",
            "time_slot_display",
            "note",
            "meet_link",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        status_value = attrs.get("status")
        attendee_name = attrs.get("attendee_name")
        existing_attendee_name = getattr(self.instance, "attendee_name", "")

        if status_value == "completed" and not (attendee_name or existing_attendee_name).strip():
            raise serializers.ValidationError(
                {"attendee_name": "Please enter the attendee name before marking completed."}
            )
        return attrs
