"""
URL configuration for Ecom project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.http import HttpResponse

from Shop.views import robots_txt
from django.contrib.sitemaps.views import sitemap
from Shop.sitemaps import StaticSitemap

from django.contrib import admin
from django.urls import path,include

from django.urls import re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

import os

sitemaps = {
    'static': StaticSitemap,
}

# ============================================
# PWA VIEWS
# ============================================
def serve_manifest(request):
    # Try staticfiles first (Render production), then static (local dev)
    for folder in ['staticfiles', 'static']:
        manifest_path = os.path.join(settings.BASE_DIR, folder, 'manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='application/manifest+json')
    
    return HttpResponse(f'manifest.json not found', status=404)

def serve_sw(request):
    # Try staticfiles first (Render production), then static (local dev)
    for folder in ['staticfiles', 'static']:
        sw_path = os.path.join(settings.BASE_DIR, folder, 'sw.js')
        if os.path.exists(sw_path):
            with open(sw_path, 'r', encoding='utf-8') as f:
                content = f.read()
            response = HttpResponse(content, content_type='application/javascript')
            response['Cache-Control'] = 'no-cache'
            response['Service-Worker-Allowed'] = '/'
            return response
    
    return HttpResponse(f'sw.js not found', status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),

    # PWA — must be before app routes
    path('manifest.json', serve_manifest, name='manifest'),
    path('sw.js', serve_sw, name='sw'),

    path('',include('Shop.urls')),
   
    
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns += [
#         path('__debug__/', include(debug_toolbar.urls)),
#     ]
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)