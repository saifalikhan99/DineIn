from django.contrib import admin
from vendor.models import Vendor, OpeningHour, Coupon, CouponUsage


class VendorAdmin(admin.ModelAdmin):
    list_display = ('user', 'vendor_name', 'is_approved', 'created_at')
    list_display_links = ('user', 'vendor_name')
    list_editable = ('is_approved',)


class OpeningHourAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'day', 'from_hour', 'to_hour')


class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'vendor', 'discount_type', 'discount_value', 'is_active', 'valid_from', 'valid_until', 'times_used')
    list_filter = ('discount_type', 'is_active', 'vendor', 'created_at')
    search_fields = ('code', 'name', 'vendor__vendor_name')
    list_editable = ('is_active',)
    readonly_fields = ('times_used', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor', 'code', 'name', 'is_active')
        }),
        ('Discount Details', {
            'fields': ('discount_type', 'discount_value', 'minimum_order_amount', 'maximum_discount_amount')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_limit_per_user')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Statistics', {
            'fields': ('times_used', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def times_used(self, obj):
        return obj.times_used
    times_used.short_description = 'Times Used'


class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'order', 'discount_amount', 'used_at')
    list_filter = ('coupon__vendor', 'used_at', 'coupon__discount_type')
    search_fields = ('coupon__code', 'user__username', 'user__email', 'order__order_number')
    readonly_fields = ('used_at',)
    ordering = ('-used_at',)
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Prevent editing


admin.site.register(Vendor, VendorAdmin)
admin.site.register(OpeningHour, OpeningHourAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(CouponUsage, CouponUsageAdmin)