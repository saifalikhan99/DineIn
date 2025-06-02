from unicodedata import category
from urllib import response
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db import IntegrityError
from django.core.paginator import Paginator

from menu.forms import CategoryForm, FoodItemForm
from orders.models import Order, OrderedFood
import vendor
from .forms import VendorForm, OpeningHourForm, CouponForm
from accounts.forms import UserProfileForm

from accounts.models import UserProfile
from .models import OpeningHour, Vendor, Coupon, CouponUsage
from django.contrib import messages

from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import check_role_vendor
from menu.models import Category, FoodItem
from django.template.defaultfilters import slugify


def get_vendor(request):
    vendor = Vendor.objects.get(user=request.user)
    return vendor


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def vprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    vendor = get_object_or_404(Vendor, user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        vendor_form = VendorForm(request.POST, request.FILES, instance=vendor)
        if profile_form.is_valid() and vendor_form.is_valid():
            profile_form.save()
            vendor_form.save()
            messages.success(request, 'Settings updated.')
            return redirect('vprofile')
        else:
            print(profile_form.errors)
            print(vendor_form.errors)
    else:
        profile_form = UserProfileForm(instance = profile)
        vendor_form = VendorForm(instance=vendor)

    context = {
        'profile_form': profile_form,
        'vendor_form': vendor_form,
        'profile': profile,
        'vendor': vendor,
    }
    return render(request, 'vendor/vprofile.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def menu_builder(request):
    vendor = get_vendor(request)
    categories = Category.objects.filter(vendor=vendor).order_by('created_at')
    context = {
        'categories': categories,
    }
    return render(request, 'vendor/menu_builder.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def fooditems_by_category(request, pk=None):
    vendor = get_vendor(request)
    category = get_object_or_404(Category, pk=pk)
    fooditems = FoodItem.objects.filter(vendor=vendor, category=category)
    context = {
        'fooditems': fooditems,
        'category': category,
    }
    return render(request, 'vendor/fooditems_by_category.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category_name = form.cleaned_data['category_name']
            category = form.save(commit=False)
            category.vendor = get_vendor(request)
            
            category.save() # here the category id will be generated
            category.slug = slugify(category_name)+'-'+str(category.id) # chicken-15
            category.save()
            messages.success(request, 'Category added successfully!')
            return redirect('menu_builder')
        else:
            print(form.errors)

    else:
        form = CategoryForm()
    context = {
        'form': form,
    }
    return render(request, 'vendor/add_category.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def edit_category(request, pk=None):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category_name = form.cleaned_data['category_name']
            category = form.save(commit=False)
            category.vendor = get_vendor(request)
            category.slug = slugify(category_name)
            form.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('menu_builder')
        else:
            print(form.errors)

    else:
        form = CategoryForm(instance=category)
    context = {
        'form': form,
        'category': category,
    }
    return render(request, 'vendor/edit_category.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def delete_category(request, pk=None):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, 'Category has been deleted successfully!')
    return redirect('menu_builder')


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def add_food(request):
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES)
        if form.is_valid():
            foodtitle = form.cleaned_data['food_title']
            food = form.save(commit=False)
            food.vendor = get_vendor(request)
            food.slug = slugify(foodtitle)
            form.save()
            messages.success(request, 'Food Item added successfully!')
            return redirect('fooditems_by_category', food.category.id)
        else:
            print(form.errors)
    else:
        form = FoodItemForm()
        # modify this form
        form.fields['category'].queryset = Category.objects.filter(vendor=get_vendor(request))
    context = {
        'form': form,
    }
    return render(request, 'vendor/add_food.html', context)



@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def edit_food(request, pk=None):
    food = get_object_or_404(FoodItem, pk=pk)
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES, instance=food)
        if form.is_valid():
            foodtitle = form.cleaned_data['food_title']
            food = form.save(commit=False)
            food.vendor = get_vendor(request)
            food.slug = slugify(foodtitle)
            form.save()
            messages.success(request, 'Food Item updated successfully!')
            return redirect('fooditems_by_category', food.category.id)
        else:
            print(form.errors)

    else:
        form = FoodItemForm(instance=food)
        form.fields['category'].queryset = Category.objects.filter(vendor=get_vendor(request))
    context = {
        'form': form,
        'food': food,
    }
    return render(request, 'vendor/edit_food.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def delete_food(request, pk=None):
    food = get_object_or_404(FoodItem, pk=pk)
    food.delete()
    messages.success(request, 'Food Item has been deleted successfully!')
    return redirect('fooditems_by_category', food.category.id)


def opening_hours(request):
    opening_hours = OpeningHour.objects.filter(vendor=get_vendor(request))
    form = OpeningHourForm()
    context = {
        'form': form,
        'opening_hours': opening_hours,
    }
    return render(request, 'vendor/opening_hours.html', context)


def add_opening_hours(request):
    # handle the data and save them inside the database
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
            day = request.POST.get('day')
            from_hour = request.POST.get('from_hour')
            to_hour = request.POST.get('to_hour')
            is_closed = request.POST.get('is_closed')
            
            try:
                hour = OpeningHour.objects.create(vendor=get_vendor(request), day=day, from_hour=from_hour, to_hour=to_hour, is_closed=is_closed)
                if hour:
                    day = OpeningHour.objects.get(id=hour.id)
                    if day.is_closed:
                        response = {'status': 'success', 'id': hour.id, 'day': day.get_day_display(), 'is_closed': 'Closed'}
                    else:
                        response = {'status': 'success', 'id': hour.id, 'day': day.get_day_display(), 'from_hour': hour.from_hour, 'to_hour': hour.to_hour}
                return JsonResponse(response)
            except IntegrityError as e:
                response = {'status': 'failed', 'message': from_hour+'-'+to_hour+' already exists for this day!'}
                return JsonResponse(response)
        else:
            HttpResponse('Invalid request')


def remove_opening_hours(request, pk=None):
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            hour = get_object_or_404(OpeningHour, pk=pk)
            hour.delete()
            return JsonResponse({'status': 'success', 'id': pk})


def order_detail(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_food = OrderedFood.objects.filter(order=order, fooditem__vendor=get_vendor(request))

        context = {
            'order': order,
            'ordered_food': ordered_food,
            'subtotal': order.get_total_by_vendor()['subtotal'],
            'tax_data': order.get_total_by_vendor()['tax_dict'],
            'grand_total': order.get_total_by_vendor()['grand_total'],
        }
    except:
        return redirect('vendor')
    return render(request, 'vendor/order_detail.html', context)


def my_orders(request):
    vendor = Vendor.objects.get(user=request.user)
    orders = Order.objects.filter(vendors__in=[vendor.id], is_ordered=True).order_by('-created_at')

    # Calculate vendor-specific totals for each order
    for order in orders:
        vendor_totals = order.get_total_by_vendor()
        # Set the actual amount the customer paid to this vendor (after discounts)
        order.vendor_grand_total = vendor_totals['grand_total']
        order.vendor_subtotal = vendor_totals['subtotal']
        order.vendor_tax_dict = vendor_totals['tax_dict']
        
        # Calculate total tax amount for display
        order.vendor_tax_total = sum(vendor_totals['tax_dict'].values()) if vendor_totals['tax_dict'] else 0
    print(orders)
    context = {
        'orders': orders,
    }
    return render(request, 'vendor/my_orders.html', context)


# ============== COUPON MANAGEMENT VIEWS ==============

@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def coupon_list(request):
    """Display list of vendor's coupons"""
    vendor = get_vendor(request)
    coupons = Coupon.objects.filter(vendor=vendor).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'coupons': page_obj,
    }
    return render(request, 'vendor/coupon_list.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def create_coupon(request):
    """Create a new coupon"""
    vendor = get_vendor(request)
    
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.vendor = vendor
            try:
                coupon.save()
                messages.success(request, 'Coupon created successfully!')
                return redirect('coupon_list')
            except IntegrityError:
                messages.error(request, 'A coupon with this code already exists.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CouponForm()
    
    context = {
        'form': form,
        'action': 'Create'
    }
    return render(request, 'vendor/coupon_form.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def edit_coupon(request, coupon_id):
    """Edit an existing coupon"""
    vendor = get_vendor(request)
    coupon = get_object_or_404(Coupon, id=coupon_id, vendor=vendor)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Coupon updated successfully!')
                return redirect('coupon_list')
            except IntegrityError:
                messages.error(request, 'A coupon with this code already exists.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CouponForm(instance=coupon)
    
    context = {
        'form': form,
        'coupon': coupon,
        'action': 'Edit'
    }
    return render(request, 'vendor/coupon_form.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def delete_coupon(request, coupon_id):
    """Delete a coupon"""
    vendor = get_vendor(request)
    coupon = get_object_or_404(Coupon, id=coupon_id, vendor=vendor)
    
    if request.method == 'POST':
        coupon_code = coupon.code
        coupon.delete()
        messages.success(request, f'Coupon "{coupon_code}" deleted successfully!')
        return redirect('coupon_list')
    
    context = {
        'coupon': coupon
    }
    return render(request, 'vendor/coupon_confirm_delete.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def coupon_usage_report(request, coupon_id):
    """View usage report for a specific coupon"""
    vendor = get_vendor(request)
    coupon = get_object_or_404(Coupon, id=coupon_id, vendor=vendor)
    
    usage_records = CouponUsage.objects.filter(
        coupon=coupon,
        order__is_ordered=True
    ).select_related('user', 'order').order_by('-used_at')
    
    # Pagination
    paginator = Paginator(usage_records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_uses = usage_records.count()
    total_discount_given = sum(record.discount_amount for record in usage_records)
    unique_users = usage_records.values('user').distinct().count()
    
    context = {
        'coupon': coupon,
        'page_obj': page_obj,
        'usage_records': page_obj,
        'total_uses': total_uses,
        'total_discount_given': total_discount_given,
        'unique_users': unique_users,
    }
    return render(request, 'vendor/coupon_usage_report.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_vendor)
def toggle_coupon_status(request, coupon_id):
    """Toggle coupon active/inactive status via AJAX"""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        vendor = get_vendor(request)
        try:
            coupon = Coupon.objects.get(id=coupon_id, vendor=vendor)
            coupon.is_active = not coupon.is_active
            coupon.save()
            
            status = 'activated' if coupon.is_active else 'deactivated'
            return JsonResponse({
                'status': 'success',
                'message': f'Coupon {status} successfully!',
                'is_active': coupon.is_active
            })
        except Coupon.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Coupon not found!'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request!'
    })