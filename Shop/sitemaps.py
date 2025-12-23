from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = "daily"

    def items(self):
        return [
            'home',
            'collection',
            'about',
            'privacy',
            'faq',
            'support_team',
        ]

    def location(self, item):
        return reverse(item)
