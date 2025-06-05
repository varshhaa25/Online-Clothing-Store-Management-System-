from pyexpat.errors import messages
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from .models import Product, Cart, Order
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import razorpay

# Function to check if a user is admin
def is_admin(user):
    return user.is_authenticated and user.is_superuser  # Only superusers (admins) can access

# View to add a product (Only for Admins)
@user_passes_test(is_admin)
def add_product(request):
    if request.method == "POST":
        name = request.POST['name']
        category = request.POST['category']
        price = request.POST['price']
        description = request.POST['description']
        image = request.FILES['image']

        fs = FileSystemStorage()
        fs = FileSystemStorage(location=settings.MEDIA_ROOT)  # Ensure correct storage
        filename = fs.save(image.name, image)

        Product.objects.create(
            name=name,
            category=category,
            price=price,
            description=description,
            image=image
        )
        return redirect('main_page')  # Redirect to main page after adding
    return render(request, 'store/add_product.html')

@user_passes_test(is_admin)
def delete_product_page(request):
    products = Product.objects.all()
    return render(request, 'store/delete_product.html', {'products': products})

@user_passes_test(is_admin)
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('delete_product_page')

# Main Page View (Displays Products & Authenticated User Info)
def main_page(request):
    men_products = Product.objects.filter(category='Men')
    women_products = Product.objects.filter(category='Women')
    kids_products = Product.objects.filter(category='Kids')

    # Check if the user is authenticated and is a superuser (admin)
    is_admin = request.user.is_authenticated and request.user.is_superuser

    return render(request, 'store/main_page.html', {
        'men_products': men_products,
        'women_products': women_products,
        'kids_products': kids_products,
        'is_admin': is_admin
    })

def category_page(request, category):
    sort_order = request.GET.get('sort', 'asc')
    # Filter products based on the category
    products = Product.objects.filter(category=category)
    if sort_order == 'asc':
        products = products.order_by('price')  # Sort from Low to High
    elif sort_order == 'desc':
        products = products.order_by('-price')
    return render(request, 'store/category_page.html', {'products': products, 'category': category,  'sort_order': sort_order})

# User Registration View
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto-login after registration
            return redirect('main_page')  # Redirect to homepage
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))  # Default to 1 if not provided

    # Check if the item is already in the cart
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)

    if not created:
        cart_item.quantity += quantity  # Update quantity if already exists
    else:
        cart_item.quantity = quantity  # Set initial quantity

    cart_item.save()
    return redirect('category_page',category=product.category) 

@login_required
def cart_page(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.total_price() for item in cart_items)

    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total': total})

@login_required
def remove_from_cart(request, cart_id):
    cart_item = get_object_or_404(Cart, id=cart_id, user=request.user)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1  # ✅ Reduce quantity instead of deleting
        cart_item.save()
    else:
        cart_item.delete()  # ✅ Remove item if quantity is 1

    return redirect('cart_page') 



@login_required
def update_cart_quantity(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
    new_quantity = int(request.POST.get('quantity', 1))  # Default to 1 if not provided

    if new_quantity > 0:
        cart_item.quantity = new_quantity
        cart_item.save()
    else:
        cart_item.delete()  # Remove if quantity is zero

    return redirect('cart_page')


@login_required
def confirm_order(request):
    cart_items = Cart.objects.filter(user=request.user)
    
    if not cart_items:
        return redirect('cart_page')  # If cart is empty, stay on cart page
    
    total_price = sum(item.total_price() for item in cart_items)

    # Create an order (but don't delete cart yet in case of payment issues)
    order = Order.objects.create(user=request.user, total_price=total_price)
    
    # Add cart items to the order
    for cart_item in cart_items:
        order.products.add(cart_item.product)
        order.quantities[cart_item.product.id] = cart_item.quantity  # Store quantity in a dict
    order.save()

    return redirect('order_summary')  # Redirect to order summary page


@login_required
def order_summary(request):
    order = Order.objects.filter(user=request.user).last()  # Get the most recent order
    if not order:
        return redirect('cart_page')  # If no order exists, go back to cart
    
    order_items = []
    for product in order.products.all():
        order_items.append({
            'name': product.name,
            'price': product.price,
            'quantity': order.quantities.get(str(product.id), 1),
            'total': product.price * order.quantities.get(str(product.id), 1)
        })

    return render(request, 'store/order.html', {'order_items': order_items, 'total_price': order.total_price})

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=("rzp_test_HvJcHYlWeLrHPr", "dySJG8vpBrqgYH1hkG0eMoz3"))

@login_required
def payment_page(request):
    amount = 50000  # Amount in paise (₹500)
    currency = "INR"

    # Create an order
    order_data = {
        "amount": amount,
        "currency": currency,
        "payment_capture": 1,  # Auto capture payment
    }
    order = razorpay_client.order.create(order_data)

    context = {
        "order_id": order["id"],
        "amount": amount // 100,  # Convert paise to rupees
        "currency": currency,
        "key_id": "rzp_test_HvJcHYlWeLrHPr",
    }
    
    return render(request, "store/payment.html", context)

# Razorpay webhook/callback
@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        return render(request, "store/payment_success.html")  