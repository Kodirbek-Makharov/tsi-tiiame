"""
URL configuration for tsi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, re_path
from django.conf.urls.i18n import i18n_patterns
import devices.views as dv



urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', dv.index, name='index'),
    path('devices', dv.devices, name='devices'),
    path('devices/map', dv.devices_map, name='devices_map'),
    path('refresh-devices/', dv.get_devices, name='refresh_devices'),
    path('change-public/<int:device_id>', dv.change_public, name='change-public'),
    path('api/pm25/<int:device_id>', dv.pm25_for_chart, name='last-day-data'),
    
    
    path('device-data/<int:device_id>', dv.view_measurements, name='view_measurements'),
    path('device-data-full/<int:device_id>', dv.view_measurements_full, name='view_measurements_full'),
    path('get-data/', dv.get_data, name='get-data'),
    re_path(r'^get-data-all/(?P<age>\d+)?$', dv.get_data_all, name='get-data-all'),
    # path('get-data-all/<int:age>', dv.get_data_all, name='get-data-all'),
    path('get-data-all-last/', dv.get_data_all_last, name='get-data-all-last'),

    path("change-password", dv.change_password, name="chp"),
    path("login", dv.login, name="login"),
    path("logout", dv.logout, name="logout"),
)