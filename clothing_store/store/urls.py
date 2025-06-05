from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('cart/', views.cart_page, name='cart_page'), 
    path('category/<str:category>/', views.category_page, name='category_page'),
    path('confirm-order/', views.confirm_order, name='confirm_order'),
    path('order-summary/', views.order_summary, name='order_summary'),
    path("payment/", views.payment_page, name="payment_page"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('add-product/', views.add_product, name='add_product'), 
    path('delete-product/', views.delete_product_page, name='delete_product_page'),  # 👈 Page to display products for deletion
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),  # 👈 Handles product deletion
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)