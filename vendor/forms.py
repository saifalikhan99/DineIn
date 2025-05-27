from django import forms
from .models import Vendor, OpeningHour, Coupon
from accounts.validators import allow_only_images_validator
from django.utils import timezone
from datetime import timedelta


class VendorForm(forms.ModelForm):
    vendor_license = forms.FileField(widget=forms.FileInput(attrs={'class': 'btn btn-info'}), validators=[allow_only_images_validator])
    class Meta:
        model = Vendor
        fields = ['vendor_name', 'vendor_license']


class OpeningHourForm(forms.ModelForm):
    class Meta:
        model = OpeningHour
        fields = ['day', 'from_hour', 'to_hour', 'is_closed']


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code', 'name', 'discount_type', 'discount_value', 
            'minimum_order_amount', 'maximum_discount_amount',
            'usage_limit', 'usage_limit_per_user', 'valid_from', 
            'valid_until', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter coupon code (e.g., SAVE20)',
                'style': 'text-transform: uppercase;'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter coupon description'
            }),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter discount value',
                'min': '0.01',
                'step': '0.01'
            }),
            'minimum_order_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minimum order amount',
                'min': '0',
                'step': '0.01',
                'value': '0'
            }),
            'maximum_discount_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Maximum discount (optional)',
                'min': '0.01',
                'step': '0.01'
            }),
            'usage_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Total usage limit (optional)',
                'min': '1'
            }),            'usage_limit_per_user': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1'
            }),            'valid_from': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'valid_until': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'  
            }, format='%Y-%m-%dT%H:%M'),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set input formats for datetime fields
        self.fields['valid_from'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['valid_until'].input_formats = ['%Y-%m-%dT%H:%M']
        
        # Set default values for new coupons
        if not self.instance.pk:
            now = timezone.now()
            # Format datetime for datetime-local input
            self.fields['valid_from'].initial = now.strftime('%Y-%m-%dT%H:%M')
            self.fields['valid_until'].initial = (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper().strip()
            # Check for uniqueness excluding current instance
            existing_coupon = Coupon.objects.filter(code=code)
            if self.instance.pk:
                existing_coupon = existing_coupon.exclude(pk=self.instance.pk)
            if existing_coupon.exists():
                raise forms.ValidationError("A coupon with this code already exists.")
        return code
    
    def clean_discount_value(self):
        discount_value = self.cleaned_data.get('discount_value')
        discount_type = self.cleaned_data.get('discount_type')
        
        if discount_value is not None:
            if discount_value <= 0:
                raise forms.ValidationError("Discount value must be greater than 0.")
            
            if discount_type == 'PERCENTAGE' and discount_value > 100:
                raise forms.ValidationError("Percentage discount cannot be more than 100%.")
        
        return discount_value
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')
        
        if valid_from and valid_until:
            if valid_from >= valid_until:
                raise forms.ValidationError("Valid until date must be after valid from date.")
        
        return cleaned_data


class CouponApplicationForm(forms.Form):
    """Form for applying coupon codes during checkout"""
    coupon_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter coupon code',
            'style': 'text-transform: uppercase;'
        })
    )
    
    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if code:
            return code.upper().strip()
        return code