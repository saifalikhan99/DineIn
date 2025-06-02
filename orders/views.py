from urllib import response
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from marketplace.models import Cart, Tax
from marketplace.context_processors import get_cart_amounts
from menu.models import FoodItem
from .forms import OrderForm
from .models import Order, OrderedFood, Payment
import simplejson as json
from .utils import generate_order_number, order_total_by_vendor
from accounts.utils import send_notification
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY



@login_required(login_url='login')
def place_order(request):
    # Debug: Print request method and data
    print(f"DEBUG: place_order called with method: {request.method}")
    print(f"DEBUG: POST data: {request.POST}")
    print(f"DEBUG: User: {request.user}")
    
    cart_items = Cart.objects.filter(user=request.user).order_by('created_at')
    cart_count = cart_items.count()
    if cart_count <= 0:
        print("DEBUG: No cart items, redirecting to marketplace")
        return redirect('marketplace')

    vendors_ids = []
    for i in cart_items:
        if i.fooditem.vendor.id not in vendors_ids:
            vendors_ids.append(i.fooditem.vendor.id)
    
    # {"vendor_id":{"subtotal":{"tax_type": {"tax_percentage": "tax_amount"}}}}
    get_tax = Tax.objects.filter(is_active=True)
    subtotal = 0
    total_data = {}
    k = {}
    for i in cart_items:
        fooditem = FoodItem.objects.get(pk=i.fooditem.id, vendor_id__in=vendors_ids)
        v_id = fooditem.vendor.id
        if v_id in k:
            subtotal = k[v_id]
            subtotal += (fooditem.price * i.quantity)
            k[v_id] = subtotal
        else:
            subtotal = (fooditem.price * i.quantity)
            k[v_id] = subtotal
    
        # Calculate the tax_data
        tax_dict = {}
        for i in get_tax:
            tax_type = i.tax_type
            tax_percentage = i.tax_percentage
            tax_amount = round((tax_percentage * subtotal)/100, 2)
            tax_dict.update({tax_type: {str(tax_percentage) : str(tax_amount)}})        # Construct total data
        total_data.update({fooditem.vendor.id: {str(subtotal): str(tax_dict)}})
    
    subtotal = get_cart_amounts(request)['subtotal']
    total_tax = get_cart_amounts(request)['tax']
    grand_total = get_cart_amounts(request)['grand_total']
    tax_data = get_cart_amounts(request)['tax_dict']
    
    # Get coupon information from cart amounts
    cart_amounts = get_cart_amounts(request)
    discount_amount = cart_amounts.get('discount', 0)
    applied_coupon = cart_amounts.get('applied_coupon', None)
    
    if request.method == 'POST':
        print("DEBUG: Processing POST request")
        form = OrderForm(request.POST)
        print(f"DEBUG: Form is valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"DEBUG: Form errors: {form.errors}")
            
        if form.is_valid():
            print("DEBUG: Creating order...")
            order = Order()
            order.first_name = form.cleaned_data['first_name']
            order.last_name = form.cleaned_data['last_name']
            order.phone = form.cleaned_data['phone']
            order.email = form.cleaned_data['email']
            order.address = form.cleaned_data['address']
            order.country = form.cleaned_data['country']
            order.state = form.cleaned_data['state']
            order.city = form.cleaned_data['city']
            order.pin_code = form.cleaned_data['pin_code']
            order.user = request.user
            order.total = grand_total
            order.tax_data = json.dumps(tax_data)
            order.total_data = json.dumps(total_data)
            order.total_tax = total_tax
            order.payment_method = 'Stripe'
              # Save coupon information if applied
            if applied_coupon:
                # Make sure coupon_code doesn't exceed the maximum length allowed
                coupon_code_value = applied_coupon.code if hasattr(applied_coupon, 'code') else str(applied_coupon)
                # Truncate to 50 characters
                order.coupon_code = coupon_code_value[:50]
                order.coupon_discount = discount_amount
            
            order.save() # order id/ pk is generated
            # Generate order number and truncate if necessary
            order_number = generate_order_number(order.id)
            # Truncate to 20 characters if longer
            order.order_number = order_number[:20]
            order.vendors.add(*vendors_ids)
            order.save()

            # Stripe Payment Intent
            try:
                # Get cart items for description
                cart_items = Cart.objects.filter(user=request.user)
                item_names = [item.fooditem.food_title for item in cart_items[:3]]  # First 3 items
                if len(cart_items) > 3:
                    description = f"Food order: {', '.join(item_names)} and {len(cart_items) - 3} more items"
                else:
                    description = f"Food order: {', '.join(item_names)}"
                
                # Truncate description to 1000 characters (Stripe limit)
                if len(description) > 1000:
                    description = description[:997] + "..."
                
                intent = stripe.PaymentIntent.create(
                    amount=int(float(order.total) * 100),  # amount in cents
                    currency='inr',
                    description=description,  # Required for Indian regulations
                    metadata={
                        'order_number': order.order_number,
                        'user_id': request.user.id,
                    }
                )
                
                context = {
                    'order': order,
                    'cart_items': cart_items,
                    'client_secret': intent.client_secret,
                    'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
                    'amount': float(order.total),
                    'subtotal': subtotal,
                    'tax_dict': tax_data,
                    'grand_total': grand_total,
                }
                return render(request, 'orders/place_order.html', context)
            except Exception as e:
                print(f"Error creating Stripe payment intent: {e}")
                return redirect('checkout')

        else:
            print("DEBUG: Form is invalid")
            print(f"DEBUG: Form errors: {form.errors}")
    else:
        print("DEBUG: GET request received, redirecting to checkout")
        return redirect('checkout')


@csrf_exempt
def create_payment_intent(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_number = data.get('order_number')
            
            order = Order.objects.get(order_number=order_number, user=request.user)
            
            # Get cart items for description
            cart_items = Cart.objects.filter(user=request.user)
            item_names = [item.fooditem.food_title for item in cart_items[:3]]  # First 3 items
            if len(cart_items) > 3:
                description = f"Food order: {', '.join(item_names)} and {len(cart_items) - 3} more items"
            else:
                description = f"Food order: {', '.join(item_names)}"
            
            # Truncate description to 1000 characters (Stripe limit)
            if len(description) > 1000:
                description = description[:997] + "..."
            
            # Create Stripe PaymentIntent with description
            intent = stripe.PaymentIntent.create(
                amount=int(float(order.total) * 100),  # Amount in paisa (INR cents)
                currency='inr',  # Changed from 'usd' to 'inr'
                description=description,  # Required for Indian regulations
                automatic_payment_methods={
                    'enabled': True,
                },
                metadata={
                    'order_number': order.order_number,
                    'user_id': str(request.user.id),
                    'customer_email': order.email,
                    'vendor_count': str(len(set(item.fooditem.vendor.id for item in cart_items))),
                }
            )
            
            return JsonResponse({
                'client_secret': intent.client_secret,
                'amount': float(order.total),
                'success': True
            })
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        except Exception as e:
            print(f"Error creating payment intent: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def process_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            payment_intent_id = data.get('payment_intent_id')
            order_number = data.get('order_number')
            
            # Retrieve the payment intent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                order = Order.objects.get(order_number=order_number, user=request.user)
                
                # Create payment record
                payment = Payment(
                    user=request.user,
                    transaction_id=payment_intent_id,
                    payment_method='Stripe',
                    amount=order.total,
                    status='SUCCESS'
                )
                payment.save()
                
                # Update order
                order.payment = payment
                order.is_ordered = True
                order.save()
                
                # Move cart items to ordered food
                cart_items = Cart.objects.filter(user=request.user)
                for item in cart_items:
                    ordered_food = OrderedFood()
                    ordered_food.order = order
                    ordered_food.payment = payment
                    ordered_food.user = request.user
                    ordered_food.fooditem = item.fooditem
                    ordered_food.quantity = item.quantity
                    ordered_food.price = item.fooditem.price
                    ordered_food.amount = item.fooditem.price * item.quantity
                    ordered_food.save()
                
                # Send confirmation emails (same as before)
                mail_subject = 'Thank you for ordering with us.'
                mail_template = 'orders/order_confirmation_email.html'

                ordered_food = OrderedFood.objects.filter(order=order)
                customer_subtotal = 0
                for item in ordered_food:
                    customer_subtotal += (item.price * item.quantity)
                tax_data = json.loads(order.tax_data)
                context = {
                    'user': request.user,
                    'order': order,
                    'to_email': order.email,
                    'ordered_food': ordered_food,
                    'domain': get_current_site(request),
                    'customer_subtotal': customer_subtotal,
                    'tax_data': tax_data,
                }
                send_notification(mail_subject, mail_template, context)
                
                # Send vendor notifications
                mail_subject = 'You have received a new order.'
                mail_template = 'orders/new_order_received.html'
                to_emails = []
                for i in cart_items:
                    if i.fooditem.vendor.user.email not in to_emails:
                        to_emails.append(i.fooditem.vendor.user.email)

                        ordered_food_to_vendor = OrderedFood.objects.filter(order=order, fooditem__vendor=i.fooditem.vendor)
                
                        context = {
                            'order': order,
                            'to_email': i.fooditem.vendor.user.email,
                            'ordered_food_to_vendor': ordered_food_to_vendor,
                            'vendor_subtotal': order_total_by_vendor(order, i.fooditem.vendor.id)['subtotal'],
                            'tax_data': order_total_by_vendor(order, i.fooditem.vendor.id)['tax_dict'],
                            'vendor_grand_total': order_total_by_vendor(order, i.fooditem.vendor.id)['grand_total'],
                        }
                        send_notification(mail_subject, mail_template, context)
                
                # Clear cart
                cart_items.delete()
                
                return JsonResponse({
                    'success': True,
                    'order_number': order_number,
                    'transaction_id': payment_intent_id,
                    'redirect_url': f'/orders/order_complete/?order_no={order_number}&trans_id={payment_intent_id}'
                })
            else:
                return JsonResponse({'success': False, 'error': 'Payment not completed'})
                
        except Exception as e:
            print(f"Error processing payment: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required(login_url='login')
def payments(request):
    # Keep this for backward compatibility or remove if not needed
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        # This is now handled by process_payment function
        return JsonResponse({'error': 'Use process_payment endpoint'}, status=400)
    return HttpResponse('Payments view')


@login_required(login_url='login')
def order_complete(request):
    order_number = request.GET.get('order_no')
    transaction_id = request.GET.get('trans_id')

    try:
        # Get the completed order details
        order = Order.objects.get(order_number=order_number, payment__transaction_id=transaction_id, is_ordered=True)
        ordered_food = OrderedFood.objects.filter(order=order)

        # Calculate subtotal
        subtotal = 0
        for item in ordered_food:
            subtotal += (item.price * item.quantity)

        # Parse tax data from JSON
        tax_data = json.loads(order.tax_data)
        
        # Get discount and coupon information
        discount_amount = order.coupon_discount if order.coupon_discount else 0
        
        # Format the coupon data - just show the code string, not the whole object
        if order.coupon_code:
            # If the coupon_code is stored as a JSON string or dict, extract just the code
            if order.coupon_code.startswith('{') and '"code":' in order.coupon_code:
                try:
                    coupon_data = json.loads(order.coupon_code.replace("'", '"'))
                    applied_coupon = coupon_data.get('code', order.coupon_code)
                except:
                    applied_coupon = order.coupon_code
            else:
                applied_coupon = order.coupon_code
        else:
            applied_coupon = None
        
        context = {
            'order': order,
            'ordered_food': ordered_food,
            'subtotal': subtotal,
            'tax_data': tax_data,
            'discount_amount': discount_amount,
            'applied_coupon': applied_coupon,
        }
        
        # Clear any lingering session data related to coupons
        if 'applied_coupon' in request.session:
            del request.session['applied_coupon']
            request.session.modified = True
            
        return render(request, 'orders/order_complete.html', context)
    except Exception as e:
        print(f"Error displaying order complete page: {str(e)}")
        return redirect('home')
    