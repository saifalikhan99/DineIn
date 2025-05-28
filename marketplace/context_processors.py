from .models import Cart, Tax
from menu.models import FoodItem


def get_cart_counter(request):
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart_items = Cart.objects.filter(user=request.user)
            if cart_items:
                for cart_item in cart_items:
                    cart_count += cart_item.quantity
            else:
                cart_count = 0
        except:
            cart_count = 0
    return dict(cart_count=cart_count)


# ...existing code...

from decimal import Decimal

def get_cart_amounts(request):
    subtotal = 0
    tax = 0
    grand_total = 0
    tax_dict = {}
    discount = Decimal('0.00')  # Initialize as Decimal
    
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user)
        for item in cart_items:
            fooditem = FoodItem.objects.get(pk=item.fooditem.id)
            subtotal += (fooditem.price * item.quantity)

        # Get applied coupon from session
        if 'applied_coupon' in request.session:
            discount = Decimal(str(request.session['applied_coupon']['discount_amount']))
        
        # Calculate tax
        get_tax = Tax.objects.filter(is_active=True)
        for i in get_tax:
            tax_type = i.tax_type
            tax_percentage = i.tax_percentage
            tax_amount = round((tax_percentage * subtotal)/100, 2)
            tax_dict.update({tax_type: {str(tax_percentage): str(tax_amount)}})
        
        tax = sum(x for key in tax_dict.values() for x in map(Decimal, key.values()))
        grand_total = subtotal + tax - discount
    
    return dict(
        subtotal=subtotal, 
        tax=tax, 
        grand_total=grand_total, 
        tax_dict=tax_dict,
        discount=discount  # Add discount to the context
    )
