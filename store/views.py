from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import filters, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import datetime
from django.conf import settings

from .models import (
    Address,
    Cart,
    CartItem,
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
    VideoShoppingBooking,
    WishlistItem,
)
from .permissions import IsAdminOrReadOnly, IsAdminUserOnly
from .serializers import (
    AddressSerializer,
    CartItemSerializer,
    CartSerializer,
    CreateOrderSerializer,
    LoginSerializer,
    OccasionCategorySerializer,
    OrderSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProductInfoOptionSerializer,
    ProductNameOptionSerializer,
    RegisterSerializer,
    ReviewSerializer,
    SareeCategorySerializer,
    SareeSerializer,
    SareeTypeOptionSerializer,
    UserSerializer,
    WishlistItemSerializer,
    AdminVideoShoppingBookingSerializer,
    HomeScreenImageSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        Cart.objects.get_or_create(user=user)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get('user')
        if user and user.email:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
            reset_url = f"{frontend_url}/account?reset=1&uid={uid}&token={token}"
            send_mail(
                subject='Reset your Dillo password',
                message=(
                    f"Hi {user.first_name or user.username},\n\n"
                    f"Use this link to reset your Dillo password:\n{reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        return Response({'detail': 'If we found an account with email enabled, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Password has been reset. You can login now.'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class SareeCategoryViewSet(viewsets.ModelViewSet):
    queryset = SareeCategory.objects.all()
    serializer_class = SareeCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ta', 'slug']
    ordering_fields = ['name', 'sort_order', 'created_at']


class OccasionCategoryViewSet(viewsets.ModelViewSet):
    queryset = OccasionCategory.objects.all()
    serializer_class = OccasionCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    filterset_fields = ['is_active']
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'sort_order', 'created_at']


class ProductNameOptionViewSet(viewsets.ModelViewSet):
    queryset = ProductNameOption.objects.all()
    serializer_class = ProductNameOptionSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ta', 'slug']
    ordering_fields = ['name', 'sort_order', 'created_at']


class SareeTypeOptionViewSet(viewsets.ModelViewSet):
    queryset = SareeTypeOption.objects.all()
    serializer_class = SareeTypeOptionSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    filterset_fields = ['is_active']
    search_fields = ['name', 'name_ta', 'slug']
    ordering_fields = ['name', 'sort_order', 'created_at']


class ProductInfoOptionViewSet(viewsets.ModelViewSet):
    queryset = ProductInfoOption.objects.all()
    serializer_class = ProductInfoOptionSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['is_active']
    search_fields = ['label', 'value']
    ordering_fields = ['label', 'value', 'sort_order', 'created_at']


class SareeViewSet(viewsets.ModelViewSet):
    serializer_class = SareeSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product_code', 'name', 'name_ta', 'saree_type', 'description', 'tags']
    ordering_fields = ['price', 'rating', 'discount', 'created_at', 'stock_count']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['uploaded_images'] = self.request.FILES.getlist('uploaded_images')
        return context

    def _request_data(self, request):
        if 'payload' not in request.data:
            return request.data
        try:
            return json.loads(request.data.get('payload') or '{}')
        except json.JSONDecodeError:
            return {'payload': request.data.get('payload')}

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self._request_data(request))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=self._request_data(request), partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def get_queryset(self):
        qs = Saree.objects.select_related('category', 'occasion')
        user = self.request.user
        if not (user and user.is_staff):
            qs = qs.filter(is_active=True)

        category = self.request.query_params.get('category')
        occasion = self.request.query_params.get('occasion')
        saree_type = self.request.query_params.get('type')
        color = self.request.query_params.get('color')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        in_stock = self.request.query_params.get('in_stock')
        featured = self.request.query_params.get('featured')
        new = self.request.query_params.get('new')
        bestseller = self.request.query_params.get('bestseller')

        if category:
            qs = qs.filter(Q(category__slug=category) | Q(category__name__iexact=category))
        if occasion:
            qs = qs.filter(Q(occasion__slug=occasion) | Q(occasion__name__iexact=occasion))
        if saree_type:
            qs = qs.filter(saree_type__iexact=saree_type)
        if color:
            qs = qs.filter(colors__icontains=color)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if in_stock in ['true', '1']:
            qs = qs.filter(stock_count__gt=0)
        if featured in ['true', '1']:
            qs = qs.filter(is_featured=True)
        if new in ['true', '1']:
            qs = qs.filter(is_new=True)
        if bestseller in ['true', '1']:
            qs = qs.filter(is_bestseller=True)
        return qs


class HomeScreenImageViewSet(viewsets.ModelViewSet):
    serializer_class = HomeScreenImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'subtitle', 'badge', 'caption_label']
    ordering_fields = ['sort_order', 'created_at', 'updated_at']

    def get_queryset(self):
        qs = HomeScreenImage.objects.all()
        user = self.request.user
        if not (user and user.is_staff):
            qs = qs.filter(is_active=True)
        is_active = self.request.query_params.get('is_active')
        if is_active in ['true', '1']:
            qs = qs.filter(is_active=True)
        elif is_active in ['false', '0']:
            qs = qs.filter(is_active=False)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['landscape_file'] = self.request.FILES.get('landscape_image_file')
        context['portrait_file'] = self.request.FILES.get('portrait_image_file')
        return context

    def _request_data(self, request):
        if 'payload' not in request.data:
            return request.data
        try:
            return json.loads(request.data.get('payload') or '{}')
        except json.JSONDecodeError:
            return {'payload': request.data.get('payload')}

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self._request_data(request))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=self._request_data(request), partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            saree=data['saree'],
            selected_color=data.get('selected_color', ''),
            selected_size=data.get('selected_size', ''),
            defaults={'quantity': data.get('quantity', 1)},
        )
        if not created:
            item.quantity += data.get('quantity', 1)
            item.save(update_fields=['quantity', 'updated_at'])
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        item = CartItem.objects.get(id=request.data.get('id'), cart__user=request.user)
        item.quantity = max(1, int(request.data.get('quantity', item.quantity)))
        item.save(update_fields=['quantity', 'updated_at'])
        return Response(CartItemSerializer(item).data)

    @action(detail=False, methods=['post'])
    def remove(self, request):
        CartItem.objects.filter(id=request.data.get('id'), cart__user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        CartItem.objects.filter(cart__user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    filterset_fields = ['status', 'payment_status', 'payment_method']
    search_fields = ['order_number', 'user__username', 'user__email']
    ordering_fields = ['created_at', 'total', 'status']

    def get_permissions(self):
        if self.action in ['list', 'partial_update', 'update', 'destroy']:
            return [IsAdminUserOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Order.objects.select_related('user').prefetch_related('items')
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def _get_client_ip(self, request):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            subtotal = Decimal('0')

            for item_data in data['items']:
                saree = item_data['saree']
                quantity = item_data['quantity']
                if saree.stock_count < quantity:
                    return Response(
                        {"detail": f"{saree.name} has only {saree.stock_count} item(s) in stock."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            order = Order.objects.create(
                user=request.user,
                order_number=f'DILLO{timezone.now().strftime("%y%m%d%H%M%S%f")[:16]}',
                shipping_address=data['shipping_address'],
                payment_method=data.get('payment_method', 'cod'),
                payment_status='pending',
                subtotal=0,
                discount=data.get('discount', Decimal('0')),
                shipping=data.get('shipping', Decimal('0')),
                total=0,
                notes=data.get('notes', ''),
                order_source=data.get('order_source', 'website'),
                device_info=(data.get('device_info') or request.META.get('HTTP_USER_AGENT', ''))[:200],
                ip_address=self._get_client_ip(request),
                coupon_code=data.get('coupon_code', ''),
            )

            for item_data in data['items']:
                saree = item_data['saree']
                quantity = item_data['quantity']
                subtotal += saree.price * quantity

                OrderItem.objects.create(
                    order=order,
                    saree=saree,
                    product_snapshot=SareeSerializer(saree).data,
                    selected_color=item_data.get('selected_color', ''),
                    selected_size=item_data.get('selected_size', ''),
                    quantity=quantity,
                    price=saree.price,
                )

                Saree.objects.filter(id=saree.id).update(stock_count=F('stock_count') - quantity)

            order.subtotal = subtotal
            order.total = subtotal - data.get('discount', Decimal('0')) + data.get('shipping', Decimal('0'))
            order.save()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WishlistItem.objects.filter(user=self.request.user).select_related('saree')


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    filterset_fields = ['saree', 'is_approved']
    ordering_fields = ['created_at', 'rating']

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUserOnly()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Review.objects.select_related('user', 'saree')
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_approved=True)
        return qs


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUserOnly]
    filterset_fields = ['is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username', 'email']


class AdminVideoShoppingBookingViewSet(viewsets.ModelViewSet):
    serializer_class = AdminVideoShoppingBookingSerializer
    permission_classes = [IsAdminUserOnly]
    http_method_names = ['get', 'patch', 'head', 'options']
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'phone', 'attendee_name', 'note']
    ordering_fields = ['date', 'time_slot', 'status', 'created_at']

    def get_queryset(self):
        qs = VideoShoppingBooking.objects.all()
        status_filter = self.request.query_params.get('status')
        date_filter = self.request.query_params.get('date')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if date_filter:
            qs = qs.filter(date=date_filter)
        return qs


@api_view(['GET'])
@permission_classes([IsAdminUserOnly])
def dashboard_summary(request):
    revenue = Order.objects.exclude(status='cancelled').aggregate(total=Sum('total'))['total'] or Decimal('0')
    low_stock = Saree.objects.filter(stock_count__lte=5, is_active=True).count()
    recent_orders = Order.objects.select_related('user').prefetch_related('items')[:6]
    top_products = (
        OrderItem.objects.values('saree__id', 'saree__name')
        .annotate(quantity=Sum('quantity'))
        .order_by('-quantity')[:5]
    )
    orders_by_status = Order.objects.values('status').annotate(count=Count('id')).order_by('status')

    return Response({
        'totals': {
            'products': Saree.objects.count(),
            'active_products': Saree.objects.filter(is_active=True).count(),
            'users': User.objects.count(),
            'orders': Order.objects.count(),
            'revenue': revenue,
            'low_stock': low_stock,
        },
        'recent_orders': OrderSerializer(recent_orders, many=True).data,
        'top_products': list(top_products),
        'orders_by_status': list(orders_by_status),
    })

# Create your views here.




def _format_time_slot(time_slot: str) -> str:
    """Convert '09:00' → '9:00 AM', '13:30' → '1:30 PM'."""
    hour, minute = map(int, time_slot.split(":"))
    ampm = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {ampm}"
 
 
def _make_dummy_meet_link() -> str:
    """
    Generate a dummy Google Meet-style link.
    Replace this with a real Google Calendar / Meet API call when ready.
    """
    code = uuid.uuid4().hex[:10]
    part1, part2, part3 = code[:3], code[3:7], code[7:]
    return f"https://meet.google.com/{part1}-{part2}-{part3}"
 
 
def _send_confirmation_email(booking):
    """
    Send a confirmation email to the customer with the Meet link.
    Uses Django's EMAIL_* settings (configure with Gmail SMTP — see settings snippet).
    """
    date_str = booking.date.strftime("%A, %d %B %Y")   # e.g. "Monday, 16 June 2025"
    time_str = _format_time_slot(booking.time_slot)
 
    subject = f"✅ Your Video Shopping Session is Confirmed — {date_str} at {time_str}"
 
    text_body = (
        f"Hi {booking.name},\n\n"
        f"Your 30-minute video shopping session with Dillo Sarees is confirmed!\n\n"
        f"📅 Date   : {date_str}\n"
        f"🕐 Time   : {time_str}\n"
        f"🔗 Meet   : {booking.meet_link}\n\n"
        f"Just click the link above at the scheduled time — no app download needed.\n\n"
        f"Our stylist will walk you through the collection and help you find the perfect saree.\n\n"
        f"Need to reschedule? Email us at hello@dillo.in with your booking ID: {booking.id}\n\n"
        f"See you soon!\n"
        f"— The Dillo Team"
    )
 
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
 
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#0f3460 100%);padding:36px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:-0.3px;">Dillo Sarees</h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.6);font-size:13px;">Video Shopping</p>
            </td>
          </tr>
 
          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 8px;color:#1a1a2e;font-size:20px;">Your session is confirmed ✅</h2>
              <p style="margin:0 0 28px;color:#666;font-size:14px;line-height:1.6;">
                Hi {booking.name}, we're looking forward to your video shopping session!
              </p>
 
              <!-- Details card -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#f8f8f8;border-radius:12px;padding:0;overflow:hidden;border:1px solid #ebebeb;">
                <tr>
                  <td style="padding:20px 24px;border-bottom:1px solid #ebebeb;">
                    <p style="margin:0;color:#999;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Date</p>
                    <p style="margin:4px 0 0;color:#1a1a2e;font-size:15px;font-weight:600;">{date_str}</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 24px;border-bottom:1px solid #ebebeb;">
                    <p style="margin:0;color:#999;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Time</p>
                    <p style="margin:4px 0 0;color:#1a1a2e;font-size:15px;font-weight:600;">{time_str} &nbsp;·&nbsp; 30 minutes</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0;color:#999;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Google Meet Link</p>
                    <a href="{booking.meet_link}" style="display:inline-block;margin-top:10px;background:#1a1a2e;color:#ffffff;text-decoration:none;padding:10px 20px;border-radius:8px;font-size:14px;font-weight:600;">
                      Join Meeting →
                    </a>
                    <p style="margin:8px 0 0;color:#aaa;font-size:11px;">{booking.meet_link}</p>
                  </td>
                </tr>
              </table>
 
              <p style="margin:28px 0 0;color:#666;font-size:13px;line-height:1.7;">
                Need to cancel or reschedule? Email us at
                <a href="mailto:hello@dillo.in" style="color:#1a1a2e;font-weight:600;">hello@dillo.in</a>
                with your booking ID: <code style="background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:12px;">{booking.id}</code>
              </p>
            </td>
          </tr>
 
          <!-- Footer -->
          <tr>
            <td style="background:#f8f8f8;padding:20px 40px;text-align:center;">
              <p style="margin:0;color:#bbb;font-size:12px;">
                © Dillo Sarees &nbsp;·&nbsp; Puducherry, India<br/>
                You received this because you booked a video shopping session.
              </p>
            </td>
          </tr>
 
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
 
    send_mail(
        subject=subject,
        message=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.email],
        html_message=html_body,
        fail_silently=False,
    )
 
 
# ─── Views ────────────────────────────────────────────────────────────────────
 
@api_view(["GET"])
@permission_classes([AllowAny])
def video_shopping_booked_slots(request):
    """
    GET /api/video-shopping/booked-slots/?date=YYYY-MM-DD
    Returns the list of already-booked time slots for a given date.
    """
    from .models import VideoShoppingBooking
 
    date_str = request.query_params.get("date")
    if not date_str:
        return Response({"error": "date query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
 
    try:
        date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
 
    booked = list(
        VideoShoppingBooking.objects
        .filter(date=date, status__in=["pending", "confirmed"])
        .values_list("time_slot", flat=True)
    )
    return Response({"date": date_str, "booked_slots": booked})
 
@csrf_exempt 
@api_view(["POST"])
@permission_classes([AllowAny])
def video_shopping_book(request):
    """
    POST /api/video-shopping/book/
    Body: { date, time_slot, name, email, phone?, note? }
    Creates a booking and emails the customer a Google Meet link.
    """
    from .models import VideoShoppingBooking
    from .serializers import VideoShoppingBookingSerializer
 
    serializer = VideoShoppingBookingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
 
    # Generate a meet link (replace with real Google API call later)
    meet_link = _make_dummy_meet_link()
 
    booking = serializer.save(meet_link=meet_link, status="pending")
 
    # Send confirmation email (errors here are logged but don't fail the booking)
    try:
        _send_confirmation_email(booking)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Failed to send confirmation email: %s", exc)
 
    return Response(VideoShoppingBookingSerializer(booking).data, status=status.HTTP_201_CREATED)
 
 
@api_view(["GET", "PATCH"])
@permission_classes([])   # restrict to IsAdminUserOnly in urls.py
def video_shopping_admin_list(request):
    """
    GET  /api/admin/video-shopping/         — list all bookings (admin only)
    """
    from .models import VideoShoppingBooking
    from .serializers import VideoShoppingBookingSerializer
    from .permissions import IsAdminUserOnly
 
    if not request.user.is_staff:
        return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
 
    date_filter = request.query_params.get("date")
    qs = VideoShoppingBooking.objects.all()
    if date_filter:
        qs = qs.filter(date=date_filter)
 
    return Response(VideoShoppingBookingSerializer(qs, many=True).data)

import uuid, logging
from django.core.mail import send_mail

def _format_slot(time_slot):
    hour, minute = map(int, time_slot.split(":"))
    return f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"

def _dummy_meet_link():
    c = uuid.uuid4().hex[:10]
    return f"https://meet.google.com/{c[:3]}-{c[3:7]}-{c[7:]}"

def _send_email(booking):
    date_str = booking.date.strftime("%A, %d %B %Y")
    time_str = _format_slot(booking.time_slot)
    send_mail(
        subject=f"✅ Video Shopping Confirmed — {date_str} at {time_str}",
        message=(
            f"Hi {booking.name},\n\nYour session is confirmed!\n\n"
            f"Date: {date_str}\nTime: {time_str}\nMeet: {booking.meet_link}\n\n"
            f"Booking ID: {booking.id}\n\nSee you soon!\n— The Dillo Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.email],
        fail_silently=False,
    )
