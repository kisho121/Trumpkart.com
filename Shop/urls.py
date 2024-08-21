from django.urls import path,include
from . import views 
from django.views.generic import TemplateView

urlpatterns=[
    path('accounts/', include('allauth.urls')),
    
    path('',views.homepage, name='home'),
    path('login', views.login_page,name="account_login"),
    path('logout', views.logout_page,name="account_logout"),
    path('register',views.registerpage, name="account_signup"),
    path('otp-verification/', views.otp_verification, name='otp_verification'),
    path('addtocart', views.add_to_cart,name="addtocart"),
    path('cart',views.cartpage, name="cart"),
    path('removecart/<int:cid>',views.removecartpage, name="removecart"),
    path('fav',views.favpage, name="fav"),
    path('favrt',views.favview,name='favrt'),
    path('removefavrt/<str:fid>',views.removefavrt,name='removefavrt'),
    path('collection',views.collectionpage, name="collection"),
    path('collection/<str:name>',views.collections, name="collection"),
    path('collection/<str:cname>/<str:pname>',views.productsDetail, name="collectiondetails"),
    path('search',views.searchview,name='search'),
    path('about',views.aboutview, name='about'),
    path('privacy',views.privacyview, name='privacy'),
    path('faq',views.faqview, name='faq'),
    path('checkout',views.checkout_view,name='checkout'), 
    path('success',views.checkout_view,name='success'),
    path('order/', views.order_view, name='order'),
    path('invoice/<int:order_id>/',views.invoice_view,name='invoice'),
    path('pdf/<int:order_id>/',views.pdf_view,name='pdf'),
    path('order/<int:order_id>/deliver',views.order_delivered_view,name='order_delivered'),
    path('order/<int:order_id>/cancel/',views.cancel_order_view, name="cancel_order"),
    path('order/<int:order_id>/return/',views.return_order_view, name='return_order'),
    path('Support_team',views.supportView,name='support_team'),
]  