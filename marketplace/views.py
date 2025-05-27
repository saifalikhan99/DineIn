from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import UserProfile
from .context_processors import get_cart_counter, get_cart_amounts
from menu.models import Category, FoodItem

from vendor.models import OpeningHour, Vendor, Coupon
from vendor.forms import CouponApplicationForm
from django.db.models import Prefetch
from .models import Cart
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D # ``D`` is a shortcut for ``Distance``
from django.contrib.gis.db.models.functions import Distance

from datetime import date, datetime
from orders.forms import OrderForm


def marketplace(request):
    vendors = Vendor.objects.filter(is_approved=True, user__is_active=True)
    vendor_count = vendors.count()
    context = {
        'vendors': vendors,
        'vendor_count': vendor_count,
    }
    return render(request, 'marketplace/listings.html', context)


def vendor_detail(request, vendor_slug):
    vendor = get_object_or_404(Vendor, vendor_slug=vendor_slug)

    categories = Category.objects.filter(vendor=vendor).prefetch_related(
        Prefetch(
            'fooditems',
            queryset = FoodItem.objects.filter(is_available=True)
        )
    )

    opening_hours = OpeningHour.objects.filter(vendor=vendor).order_by('day', 'from_hour')
    
    # Check current day's opening hours.
    today_date = date.today()
    today = today_date.isoweekday()
    
    current_opening_hours = OpeningHour.objects.filter(vendor=vendor, day=today)
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user)
    else:
        cart_items = None
    context = {
        'vendor': vendor,
        'categories': categories,
        'cart_items': cart_items,
        'opening_hours': opening_hours,
        'current_opening_hours': current_opening_hours,
    }
    return render(request, 'marketplace/vendor_detail.html', context)


def add_to_cart(request, food_id):
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Check if the food item exists
            try:
                fooditem = FoodItem.objects.get(id=food_id)
                # Check if the user has already added that food to the cart
                try:
                    chkCart = Cart.objects.get(user=request.user, fooditem=fooditem)
                    # Increase the cart quantity
                    chkCart.quantity += 1
                    chkCart.save()
                    return JsonResponse({'status': 'Success', 'message': 'Increased the cart quantity', 'cart_counter': get_cart_counter(request), 'qty': chkCart.quantity, 'cart_amount': get_cart_amounts(request)})
                except:
                    chkCart = Cart.objects.create(user=request.user, fooditem=fooditem, quantity=1)
                    return JsonResponse({'status': 'Success', 'message': 'Added the food to the cart', 'cart_counter': get_cart_counter(request), 'qty': chkCart.quantity, 'cart_amount': get_cart_amounts(request)})
            except:
                return JsonResponse({'status': 'Failed', 'message': 'This food does not exist!'})
        else:
            return JsonResponse({'status': 'Failed', 'message': 'Invalid request!'})
        
    else:
        return JsonResponse({'status': 'login_required', 'message': 'Please login to continue'})


def decrease_cart(request, food_id):
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Check if the food item exists
            try:
                fooditem = FoodItem.objects.get(id=food_id)
                # Check if the user has already added that food to the cart
                try:
                    chkCart = Cart.objects.get(user=request.user, fooditem=fooditem)
                    if chkCart.quantity > 1:
                        # decrease the cart quantity
                        chkCart.quantity -= 1
                        chkCart.save()
                    else:
                        chkCart.delete()
                        chkCart.quantity = 0
                    return JsonResponse({'status': 'Success', 'cart_counter': get_cart_counter(request), 'qty': chkCart.quantity, 'cart_amount': get_cart_amounts(request)})
                except:
                    return JsonResponse({'status': 'Failed', 'message': 'You do not have this item in your cart!'})
            except:
                return JsonResponse({'status': 'Failed', 'message': 'This food does not exist!'})
        else:
            return JsonResponse({'status': 'Failed', 'message': 'Invalid request!'})
        
    else:
        return JsonResponse({'status': 'login_required', 'message': 'Please login to continue'})


@login_required(login_url = 'login')
def cart(request):
    cart_items = Cart.objects.filter(user=request.user).order_by('created_at')
    context = {
        'cart_items': cart_items,
    }
    return render(request, 'marketplace/cart.html', context)


def delete_cart(request, cart_id):
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                # Check if the cart item exists
                cart_item = Cart.objects.get(user=request.user, id=cart_id)
                if cart_item:
                    cart_item.delete()
                    return JsonResponse({'status': 'Success', 'message': 'Cart item has been deleted!', 'cart_counter': get_cart_counter(request), 'cart_amount': get_cart_amounts(request)})
            except:
                return JsonResponse({'status': 'Failed', 'message': 'Cart Item does not exist!'})
        else:
            return JsonResponse({'status': 'Failed', 'message': 'Invalid request!'})


def search(request):
    if not 'address' in request.GET:
        return redirect('marketplace')
    else:
        address = request.GET['address']
        latitude = request.GET['lat']
        longitude = request.GET['lng']
        radius = request.GET['radius']
        keyword = request.GET['keyword']

        # get vendor ids that has the food item the user is looking for
        fetch_vendors_by_fooditems = FoodItem.objects.filter(food_title__icontains=keyword, is_available=True).values_list('vendor', flat=True)
        
        vendors = Vendor.objects.filter(Q(id__in=fetch_vendors_by_fooditems) | Q(vendor_name__icontains=keyword, is_approved=True, user__is_active=True))
        if latitude and longitude and radius:
            pnt = GEOSGeometry('POINT(%s %s)' % (longitude, latitude))

            vendors = Vendor.objects.filter(Q(id__in=fetch_vendors_by_fooditems) | Q(vendor_name__icontains=keyword, is_approved=True, user__is_active=True),
            user_profile__location__distance_lte=(pnt, D(km=radius))
            ).annotate(distance=Distance("user_profile__location", pnt)).order_by("distance")

            for v in vendors:
                v.kms = round(v.distance.km, 1)
        vendor_count = vendors.count()
        context = {
            'vendors': vendors,
            'vendor_count': vendor_count,
            'source_location': address,
        }


        return render(request, 'marketplace/listings.html', context)


@login_required(login_url='login')
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).order_by('created_at')
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('marketplace')
    
    user_profile = UserProfile.objects.get(user=request.user)
    default_values = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'phone': request.user.phone_number,
        'email': request.user.email,
        'address': user_profile.address,
        'country': user_profile.country,
        'state': user_profile.state,
        'city': user_profile.city,
        'pin_code': user_profile.pin_code,
    }
    form = OrderForm(initial=default_values)
    context = {
        'form': form,
        'cart_items': cart_items,
    }
    return render(request, 'marketplace/checkout.html', context)


# ============== COUPON APPLICATION VIEWS ==============

@login_required(login_url='login')
def apply_coupon(request):
    """Apply coupon code during checkout"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        coupon_code = request.POST.get('coupon_code', '').upper().strip()
        
        if not coupon_code:
            return JsonResponse({
                'status': 'error',
                'message': 'Please enter a coupon code.'
            })
        
        # Get user's cart items
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Your cart is empty.'
            })
        
        # Get vendors from cart items
        vendor_ids = list(cart_items.values_list('fooditem__vendor', flat=True).distinct())
        
        try:
            # Find the coupon
            coupon = Coupon.objects.get(
                code=coupon_code,
                vendor__in=vendor_ids,
                is_active=True
            )
            
            # Check if coupon is valid
            if not coupon.is_valid():
                return JsonResponse({
                    'status': 'error',
                    'message': 'This coupon is not valid or has expired.'
                })
            
            # Check if user can use this coupon
            if not coupon.can_be_used_by_user(request.user):
                return JsonResponse({
                    'status': 'error',
                    'message': 'You have already used this coupon the maximum number of times.'
                })
            
            # Calculate current cart amounts
            cart_amounts = get_cart_amounts(request)
            subtotal = float(cart_amounts['subtotal'])
            
            # Check minimum order amount
            if subtotal < float(coupon.minimum_order_amount):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Minimum order amount of ₹{coupon.minimum_order_amount} required for this coupon.'
                })
            
            # Calculate discount
            discount_amount = coupon.get_discount_amount(subtotal)
            new_total = subtotal + float(cart_amounts['tax']) - discount_amount
            
            # Store coupon info in session
            request.session['applied_coupon'] = {
                'code': coupon.code,
                'discount_amount': discount_amount,
                'coupon_id': coupon.id
            }
            
            return JsonResponse({
                'status': 'success',
                'message': f'Coupon applied! You saved ₹{discount_amount}',
                'discount_amount': discount_amount,
                'new_total': new_total,
                'coupon_code': coupon.code,
                'coupon_name': coupon.name
            })
            
        except Coupon.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid coupon code or coupon not applicable to items in your cart.'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Something went wrong. Please try again.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request!'
    })


@login_required(login_url='login')
def remove_coupon(request):
    """Remove applied coupon"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        try:
            # Remove coupon from session
            if 'applied_coupon' in request.session:
                del request.session['applied_coupon']
            
            # Recalculate cart amounts without coupon
            cart_amounts = get_cart_amounts(request)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Coupon removed successfully!',
                'new_total': float(cart_amounts['grand_total']),
                'subtotal': float(cart_amounts['subtotal']),
                'tax': float(cart_amounts['tax'])
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Something went wrong. Please try again.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request!'
    })