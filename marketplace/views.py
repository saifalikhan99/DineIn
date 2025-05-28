from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
import json

from accounts.models import UserProfile
from .context_processors import get_cart_counter, get_cart_amounts
from menu.models import Category, FoodItem

from vendor.models import OpeningHour, Vendor, Coupon
from vendor.forms import CouponApplicationForm
from django.db.models import Prefetch
from .models import Cart
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

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

# ...existing code...

@csrf_exempt
@login_required(login_url='login')
def apply_coupon(request):
    if request.method == 'POST':
        try:
            # Debug: Print raw request data
            print(f"DEBUG: request.body = {request.body}")
            print(f"DEBUG: request.content_type = {request.content_type}")
            print(f"DEBUG: request.POST = {request.POST}")
            
            # Try to parse JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # Handle form data
                data = {
                    'coupon_code': request.POST.get('coupon_code', ''),
                }
            
            coupon_code = data.get('coupon_code', '').strip().upper()
            print(f"DEBUG: coupon_code = '{coupon_code}'")
            
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
            
            # Get vendor from cart items
            vendor = cart_items.first().fooditem.vendor
            
            # Find the coupon
            try:
                coupon = Coupon.objects.get(
                    code__iexact=coupon_code,
                    vendor=vendor,
                    is_active=True
                )
            except Coupon.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'This coupon is not valid or has expired.'
                })
            
            # Check if coupon is valid using the model's is_valid method
            if not coupon.is_valid():
                return JsonResponse({
                    'status': 'error',
                    'message': 'This coupon is not valid or has expired.'
                })
            
            # Calculate cart total
            cart_total = sum(item.fooditem.price * item.quantity for item in cart_items)
            
            # Check minimum amount requirement
            if cart_total < coupon.minimum_order_amount:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Minimum order amount of ₹{coupon.minimum_order_amount} required for this coupon.'
                })
            
            # Calculate discount based on coupon type
            if coupon.discount_type == 'percentage':
                discount_amount = cart_total * (coupon.discount_value / 100)
                # Apply maximum discount limit if set
                if coupon.maximum_discount_amount:
                    discount_amount = min(discount_amount, coupon.maximum_discount_amount)
            else:  # fixed amount
                discount_amount = coupon.discount_value
            
            # Ensure discount doesn't exceed cart total
            discount_amount = min(discount_amount, cart_total)
            final_total = cart_total - discount_amount
            
            # Store coupon in session
            request.session['applied_coupon'] = {
                'id': coupon.id,
                'code': coupon.code,
                'discount_amount': float(discount_amount),
                'vendor_id': vendor.id
            }
            
            return JsonResponse({
                'status': 'success',
                'message': 'Coupon applied successfully!',
                'discount_amount': float(discount_amount),
                'cart_total': float(cart_total),
                'final_total': float(final_total),
                'coupon_code': coupon.code
            })
            
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decode error: {str(e)}")
            print(f"DEBUG: request.body = {request.body}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid data format.'
            })
        except Exception as e:
            print(f"Error applying coupon: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': 'Something went wrong. Please try again.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })

# ...existing code...

@csrf_exempt
@login_required(login_url='login')
def remove_coupon(request):
    if request.method == 'POST':
        try:
            # Remove coupon from session
            if 'applied_coupon' in request.session:
                del request.session['applied_coupon']
            
            # Recalculate cart total
            cart_items = Cart.objects.filter(user=request.user)
            cart_total = sum(item.fooditem.price * item.quantity for item in cart_items)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Coupon removed successfully!',
                'cart_total': float(cart_total),
                'final_total': float(cart_total)
            })
            
        except Exception as e:
            print(f"Error removing coupon: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Something went wrong. Please try again.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })