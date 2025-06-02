from enum import unique
from django.db import models
from accounts.models import User, UserProfile
from accounts.utils import send_notification
from datetime import time, date, datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Vendor(models.Model):
    user = models.OneToOneField(User, related_name='user', on_delete=models.CASCADE)
    user_profile = models.OneToOneField(UserProfile, related_name='userprofile', on_delete=models.CASCADE)
    vendor_name = models.CharField(max_length=50)
    vendor_slug = models.SlugField(max_length=100, unique=True)
    vendor_license = models.ImageField(upload_to='vendor/license')
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.vendor_name

    def is_open(self):
        # Check current day's opening hours.
        today_date = date.today()
        today = today_date.isoweekday()
        
        current_opening_hours = OpeningHour.objects.filter(vendor=self, day=today)
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")

        is_open = None
        for i in current_opening_hours:
            if not i.is_closed:
                start = str(datetime.strptime(i.from_hour, "%I:%M %p").time())
                end = str(datetime.strptime(i.to_hour, "%I:%M %p").time())
                if current_time > start and current_time < end:
                    is_open = True
                    break
                else:
                    is_open = False
        return is_open

    def save(self, *args, **kwargs):
        if self.pk is not None:
            # Update
            orig = Vendor.objects.get(pk=self.pk)
            if orig.is_approved != self.is_approved:
                mail_template = 'accounts/emails/admin_approval_email.html'
                context = {
                    'user': self.user,
                    'is_approved': self.is_approved,
                    'to_email': self.user.email,
                }
                if self.is_approved == True:
                    # Send notification email
                    mail_subject = "Congratulations! Your restaurant has been approved."
                    send_notification(mail_subject, mail_template, context)
                else:
                    # Send notification email
                    mail_subject = "We're sorry! You are not eligible for publishing your food menu on our marketplace."
                    send_notification(mail_subject, mail_template, context)
        return super(Vendor, self).save(*args, **kwargs)


DAYS = [
    (1, ("Monday")),
    (2, ("Tuesday")),
    (3, ("Wednesday")),
    (4, ("Thursday")),
    (5, ("Friday")),
    (6, ("Saturday")),
    (7, ("Sunday")),
]

HOUR_OF_DAY_24 = [(time(h, m).strftime('%I:%M %p'), time(h, m).strftime('%I:%M %p')) for h in range(0, 24) for m in (0, 30)]
class OpeningHour(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    day = models.IntegerField(choices=DAYS)
    from_hour = models.CharField(choices=HOUR_OF_DAY_24, max_length=10, blank=True)
    to_hour = models.CharField(choices=HOUR_OF_DAY_24, max_length=10, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ('day', '-from_hour')
        unique_together = ('vendor', 'day', 'from_hour', 'to_hour')

    def __str__(self):
        return self.get_day_display()


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=20, unique=True, help_text="Unique coupon code")
    name = models.CharField(max_length=100, help_text="Coupon name/description")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='PERCENTAGE')
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Discount percentage (0-100) or fixed amount"
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum order amount to apply coupon"
    )
    maximum_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.01)],
        help_text="Maximum discount amount (applicable for percentage discounts)"
    )
    usage_limit = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Maximum number of times this coupon can be used (leave blank for unlimited)"
    )
    usage_limit_per_user = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of times a single user can use this coupon"
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.code} - {self.vendor.vendor_name}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate discount value based on discount type
        if self.discount_type == 'PERCENTAGE':
            if self.discount_value > 100:
                raise ValidationError({'discount_value': 'Percentage discount cannot be more than 100%'})
        
        # Validate date range
        if self.valid_from >= self.valid_until:
            raise ValidationError({'valid_until': 'Valid until date must be after valid from date'})
    
    def is_valid(self):
        """Check if coupon is currently valid"""
        now = timezone.now()
        return (
            self.is_active and 
            self.valid_from <= now <= self.valid_until and
            (self.usage_limit is None or self.times_used < self.usage_limit)
        )
    
    @property
    def times_used(self):
        """Get total number of times this coupon has been used"""
        return self.usage_records.filter(order__is_ordered=True).count()
    
    def get_discount_amount(self, order_total):
        """Calculate discount amount for given order total"""
        if not self.is_valid():
            return 0
            
        if order_total < self.minimum_order_amount:
            return 0
            
        if self.discount_type == 'PERCENTAGE':
            discount = (self.discount_value / 100) * order_total
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
        else:  # FIXED
            discount = min(self.discount_value, order_total)
            
        return round(float(discount), 2)
    
    def can_be_used_by_user(self, user):
        """Check if user can use this coupon"""
        if not self.is_valid():
            return False
            
        user_usage_count = self.usage_records.filter(
            user=user, 
            order__is_ordered=True
        ).count()
        
        return user_usage_count < self.usage_limit_per_user


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usage_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-used_at']
        unique_together = ['coupon', 'order']  # One coupon per order
    
    def __str__(self):
        return f"{self.coupon.code} used by {self.user.username} - ₹{self.discount_amount}"
    usage_limit_per_user = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of times a single user can use this coupon"
    )
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.code} - {self.vendor.vendor_name}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate discount value based on discount type
        if self.discount_type == 'PERCENTAGE':
            if self.discount_value > 100:
                raise ValidationError({'discount_value': 'Percentage discount cannot be more than 100%'})
        
        # Validate date range
        if self.valid_from >= self.valid_until:
            raise ValidationError({'valid_until': 'Valid until date must be after valid from date'})
    
    def is_valid(self):
        """Check if coupon is currently valid"""
        now = timezone.now()
        return (
            self.is_active and 
            self.valid_from <= now <= self.valid_until and
            (self.usage_limit is None or self.times_used < self.usage_limit)
        )
    
    @property
    def times_used(self):
        """Get total number of times this coupon has been used"""
        return self.usage_records.filter(order__is_ordered=True).count()
    
    def get_discount_amount(self, order_total):
        """Calculate discount amount for given order total"""
        if not self.is_valid():
            return 0
            
        if order_total < self.minimum_order_amount:
            return 0
            
        if self.discount_type == 'PERCENTAGE':
            discount = (self.discount_value / 100) * order_total
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
        else:  # FIXED
            discount = min(self.discount_value, order_total)
            
        return round(float(discount), 2)
    
    def can_be_used_by_user(self, user):
        """Check if user can use this coupon"""
        if not self.is_valid():
            return False
            
        user_usage_count = self.usage_records.filter(
            user=user, 
            order__is_ordered=True
        ).count()
        
        return user_usage_count < self.usage_limit_per_user


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usage_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-used_at']
        unique_together = ['coupon', 'order']  # One coupon per order
    
    def __str__(self):
        return f"{self.coupon.code} used by {self.user.username} - ₹{self.discount_amount}"