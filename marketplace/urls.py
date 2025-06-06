from django.urls import path
from . import views

urlpatterns = [
    path('', views.marketplace, name='marketplace'),
    

    # ADD TO CART
    path('add_to_cart/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
    # DECREASE CART
    path('decrease_cart/<int:food_id>/', views.decrease_cart, name='decrease_cart'),
    # DELETE CART ITEM
    path('delete_cart/<int:cart_id>/', views.delete_cart, name='delete_cart'),
    
    # Coupon Application URLs
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    
    # Vendor detail - keep this last to avoid conflicts
    path('<slug:vendor_slug>/', views.vendor_detail, name='vendor_detail'),
]