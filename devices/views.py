from django.shortcuts import render, redirect
import requests
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from django.db.models import Prefetch, OuterRef, Subquery, Max, Q
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta
from .models import *
from .middleware import login_exempt

# Create your views here.
import pandas as pd
import numpy as np

def meanize_by_hours_old(df):
    df['when_local'] = pd.to_datetime(df['when_local'])
    
    df_m = df.set_index('when_local').resample('h').mean()
    df_c = df.set_index('when_local').resample('h').count()
    df_m[df_c['pm25'] < 3] = np.nan

    df_m.asfreq('h')
    return df_m

def meanize_by_hours(df):
    df['when_local'] = pd.to_datetime(df['when_local'])
    
    end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timezone.timedelta(hours=23)
    complete_index = pd.date_range(start=start_time, end=end_time, freq='h', tz=df['when_local'].dt.tz)

    df_m = df.set_index('when_local').resample('h').mean()
    df_c = df.set_index('when_local').resample('h').count()
    
    df_m[df_c['pm25'] < 3] = np.nan
    
    df_m = df_m.reindex(complete_index, fill_value=np.nan)
    
    return df_m

def meanize_by_days(df):
    # df['when_local'] = pd.to_datetime(df['when_local'])
    df = meanize_by_hours_old(df)

    end_date = pd.Timestamp.now(tz='UTC').normalize()
    start_date = end_date - pd.Timedelta(days=29)
    daily_index = pd.date_range(start=start_date, end=end_date, freq='D')

    df_m = df.resample('D').mean()
    df_c = df.resample('D').count()

    df_m[df_c['pm25'] < 16] = np.nan

    df_m = df_m.reindex(daily_index)
    
    # df_m = df.set_index('when_local').resample('D').mean()
    # df_c = df.set_index('when_local').resample('D').count()
    # df_m[df_c['pm25'] < 16] = np.nan

    # print(df_m)
    return df_m

@login_exempt
def index(request):
    # # with latest measure
    # devices_with_latest_timestamp = Devices.objects.filter(is_public=True).annotate(
    #     latest_measurement_time=Max('measurements__when')
    # )

    # latest_measurements = Measurement.objects.filter(
    #     Q(device_id__in=devices_with_latest_timestamp.values('id')) & 
    #     Q(when__in=devices_with_latest_timestamp.values('latest_measurement_time'))
    # )

    # devices = devices_with_latest_timestamp.prefetch_related(
    #     Prefetch(
    #         'measurements',
    #         queryset=latest_measurements,
    #         to_attr='latest_measurement'
    #     )
    # )

    # devices_js=[]
    # for instance in devices: 
    #     devices_js.append({'pk': instance.pk, 'name': instance.name, 'lat': instance.latitude, 'lng': instance.longitude,
    #                        'pm25':instance.latest_measurement[0].pm25, 'mtime': instance.latest_measurement[0].when_local.strftime('%Y-%m-%d %H:%M')})


    #with today's latest measure
    today_start = datetime.combine(timezone.now().date(), datetime.min.time())
    today_end = datetime.combine(timezone.now().date(), datetime.max.time())
    today_measurements = Measurement.objects.filter(
        device=OuterRef('pk'),
        when_local__range=(today_start, today_end)
    ).order_by('-when')

    devices = Devices.objects.filter(is_public=True).annotate(
        pm25=Subquery(today_measurements.values('pm25')[:1]),
        when_local=Subquery(today_measurements.values('when_local')[:1])
    )

    devices_js=[]
    for instance in devices:
        if instance.pm25 is not None:
            devices_js.append({'pk': instance.pk, 'name': instance.name, 'lat': instance.latitude, 'lng': instance.longitude, 'is_indoor': int(instance.is_indoor),
                            'pm25':instance.pm25, 'when_local': instance.when_local.strftime('%Y-%m-%d %H:%M') or "NaN"})
        else:
            devices_js.append({'pk': instance.pk, 'name': instance.name, 'lat': instance.latitude, 'lng': instance.longitude, 'is_indoor': int(instance.is_indoor),
                            'pm25':'', 'when_local': ''})

    return render(request, 'index.html', context={'devices':devices, "devices_js": devices_js})

def devices(request):
    order_by = request.GET.get('order_by', 'name')  
    sort_direction = request.GET.get('sort', 'asc') 


    latest_measurement = Measurement.objects.filter(device=OuterRef('pk')).order_by('-when').values('when_local')[:1]
    devices = Devices.objects.annotate(last_measurement_time=Subquery(latest_measurement))#.all()

    if sort_direction == 'desc':
        devices = devices.order_by(f'-{order_by}')
    else:
        devices = devices.order_by(order_by)
    
    context = {
        'devices': devices,
        'current_order_by': order_by,
        'current_sort': sort_direction,
    }
    return render(request, 'devices.html', context)

def devices_map(request):
    today_start = datetime.combine(timezone.now().date(), datetime.min.time())
    today_end = datetime.combine(timezone.now().date(), datetime.max.time())
    today_measurements = Measurement.objects.filter(
        device=OuterRef('pk'),
        when_local__range=(today_start, today_end)
    ).order_by('-when')

    devices = Devices.objects.annotate(
        pm25=Subquery(today_measurements.values('pm25')[:1]),
        when_local=Subquery(today_measurements.values('when_local')[:1])
    )

    devices_js=[]
    for instance in devices:
        if instance.pm25 is not None:
            devices_js.append({'pk': instance.pk, 'name': instance.name, 'lat': instance.latitude, 'lng': instance.longitude, 'is_indoor': int(instance.is_indoor),
                            'pm25':instance.pm25, 'when_local': instance.when_local.strftime('%Y-%m-%d %H:%M') or "NaN"})
        else:
            devices_js.append({'pk': instance.pk, 'name': instance.name, 'lat': instance.latitude, 'lng': instance.longitude, 'is_indoor': int(instance.is_indoor),
                            'pm25':'', 'when_local': ''})
    # latest_measurement = Measurement.objects.filter(device=OuterRef('pk')).order_by('-when').values('when_local', 'pm25')[:1]
    # devices = Devices.objects.annotate(last_measurement_time=Subquery(latest_measurement))#.all()

    context = {
        # 'devices': devices,
        'devices': devices_js,
    }
    return render(request, 'devices_map.html', context)

def change_public(request, device_id):
    device = Devices.objects.filter(pk=device_id).first()
    if device is None:
        messages.warning(request, 'Device not found!')
        return redirect('devices')    
    device.is_public=not device.is_public
    device.save()
    messages.success(request, 'Device visibility changed!')
    return redirect('devices')    

def get_tsi_token():
    url = 'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken'
    
    params = {'grant_type': 'client_credentials'}
    data = {
        'client_id': 'rXFlgIzIAkaZE0mQpTSf8E45qhzCuXG4AVeEXSFZraANsMVy',
        'client_secret': '6Y6JU6c8q6Uelbhfaiu2Es5AWvsdd0BZUQPXJHAezsQoFMSO7dIKRcAyxwbJ321P'
    }
    
    response = requests.post(url, params=params, data=data)
    
    if response.status_code == 200:
        token = response.json().get('access_token')
    
        t = None
        try:
            t = Token.objects.first()
        except Token.DoesNotExist:
            t = Token()
        t.token = token
        t.save()
        return True
    
    return False

def get_devices(request):

    def fetch_device_data(token):
        url = 'https://api-prd.tsilink.com/api/v3/external/devices/legacy-format'
        headers = {'Authorization': f'Bearer {token}'}
        return requests.get(url, headers=headers)

    token = Token.objects.first().token
    response = fetch_device_data(token)

    if response.status_code != 200:
        get_tsi_token()
        token = Token.objects.first().token
        response = fetch_device_data(token)

    if response.status_code == 200:
        data = response.json()
        
        for d in data:
            if not Devices.objects.filter(device_id=d['device_id']).exists():
                Devices.objects.create(
                    name=d['metadata']['friendlyName'],
                    device_id=d['device_id'],
                    model=d['model'],
                    serial=d['serial'],
                    is_indoor=d['metadata']['is_indoor'],
                    latitude=d['metadata']['latitude'],
                    longitude=d['metadata']['longitude']
                )
                
        # message = 'Updated!'
        messages.success(request, 'Updated!')
    else:
        messages.warning(request, 'Failed to fetch device data, please try again!')
        # message = 'Failed to fetch device data, please try again.'
    return redirect('devices')    
    # return render(request, 'index.html', context = {'message':message})

def aget_data(request):
    token = Token.objects.first().token

    did = request.POST.get('device', None)
    age = int(request.POST.get('age', 90))
    if not did.isdigit():
        messages.warning(request, "Invalid device ID")
        return redirect('devices')

    try:
        device = Devices.objects.get(id=did)
    except Devices.DoesNotExist:
        messages.error(request, "Device not found")
        return redirect('devices')

    def fetch_measurements(token):
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }
        params = {
            'age': age,
            'device_id': device.device_id,
        }
        return requests.get(
            'https://api-prd.tsilink.com/api/v3/external/telemetry/legacy-format',
            headers=headers,
            params=params
        )

    response = fetch_measurements(token)

    if response.status_code != 200:
        get_tsi_token()
        token = Token.objects.first().token
        response = fetch_measurements(token)

    if response.status_code == 200:
        data = response.json()
        for m in data:
            measurement_time = timezone.datetime.fromisoformat(m['timestamp'])#.replace(tzinfo=timezone.utc)
            if not Measurement.objects.filter(when=measurement_time, device_id=device.id).exists():

                measurement = Measurement(
                    when=measurement_time,
                    when_local=measurement_time + timedelta(hours=5),
                    device=device
                )

                for sensor in m.get('sensors', []):
                    for sm in sensor.get('measurements', []):
                        name, value = sm.get('name'), sm.get('value')
                        if name == 'pm1.0': measurement.pm1 = value
                        elif name == 'pm2.5': measurement.pm25 = value
                        elif name == 'pm4.0': measurement.pm4 = value
                        elif name == 'pm10': measurement.pm10 = value
                        elif name == 'pm2.5 aqi': measurement.pm25aqi = value
                        elif name == 'pm10 aqi': measurement.pm10aqi = value
                        elif name == 'pm0.5 NC': measurement.pm05nc = value
                        elif name == 'pm1.0 NC': measurement.pm1nc = value
                        elif name == 'pm2.5 NC': measurement.pm25nc = value
                        elif name == 'pm4.0 NC': measurement.pm4nc = value
                        elif name == 'pm10 NC': measurement.pm10nc = value
                        elif name == 'typical particle size': measurement.tps = value
                        elif name == 'Temperature': measurement.temperature = value
                        elif name == 'Relative Humidity': measurement.humidity = value
                        elif name == 'co2': measurement.co2 = value
                        elif name == 'pressure': measurement.pressure = value
                        elif name == 'EtOH': measurement.etoh = value
                        elif name == 'tvoc': measurement.tvoc = value
                
                measurement.save()

        messages.success(request, "Measurements updated!")
    else:
        messages.warning(request, "Failed to retrieve data. Please try again later.")
    
    return redirect('devices')

def view_measurements_full(request, device_id):
    device = Devices.objects.filter(id=device_id).first()
    
    if not device:
        return redirect('devices')

    measurements = Measurement.objects.filter(device_id=device_id).order_by('-when')

    paginator = Paginator(measurements, 100)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'view_measurements_full.html', {
        'device': device,
        # 'measurements': measurements,
        'page_obj': page_obj,
    })

@login_exempt
def view_measurements(request, device_id):

    # shuni to'g'irlash kerak!!!
    today=timezone.now().date()
    device = Devices.objects.filter(id=device_id).first()
    
    if not device:
        return redirect('devices')

    measurements = Measurement.objects.filter(device_id=device_id, when__date=today).order_by('-when').values('pm25', 'when_local')
    if measurements:#.count()>0:
        last_ = measurements[0].copy()
        last_["date"]=last_['when_local'].strftime('%Y-%m-%d')
        last_["time"]=last_['when_local'].strftime('%H:%M')
        df = pd.DataFrame(list(measurements))
        df_= meanize_by_hours(df)
        # df_ = df_.reset_index()
        df_["date"] = df_.index.to_series().apply(lambda x: x.date().strftime('%Y-%m-%d'))
        df_["time"] = df_.index.to_series().apply(lambda x: x.time().strftime('%H:%M'))
        # df_.sort_index(inplace=True)
        df_ = df_.to_dict('records')
        last = df_[-1]
        if np.isnan(last['pm25']): 
            last=df_[-2]
    else:
        last = np.nan
        last_ = np.nan

    return render(request, 'view_measurements_uzstandart.html', {
        'device': device,
        'measurements': measurements,
        # 'measurements_by_hour': df_,
        'lst':last,
        'lst_':last_,
    })

def get_data(request):

    did = request.POST.get('device', None)
    age = int(request.POST.get('age', 90))
    if not did.isdigit():
        messages.warning(request, "Invalid device ID")
        return redirect('devices')

    try:
        device = Devices.objects.get(id=did)
    except Devices.DoesNotExist:
        messages.error(request, "Device not found")
        return redirect('devices')

    token = Token.objects.first().token

    def fetch_measurements(token):
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }
        params = {
            'age': age,
            'device_id': device.device_id,
        }
        return requests.get(
            'https://api-prd.tsilink.com/api/v3/external/telemetry/legacy-format',
            headers=headers,
            params=params
        )

    response = fetch_measurements(token)

    if response.status_code != 200:
        get_tsi_token()
        token = Token.objects.first().token
        response = fetch_measurements(token)

    if response.status_code == 200:
        data = response.json()
        measurements_to_save = []
        existing_measurement_times = Measurement.objects.filter(device=device).values_list('when', flat=True)

        for m in data:
            measurement_time = timezone.datetime.fromisoformat(m['timestamp'])
            if measurement_time not in existing_measurement_times:

                measurement = Measurement(
                    when=measurement_time,
                    when_local=measurement_time + timedelta(hours=5),
                    device=device
                )

                for sensor in m.get('sensors', []):
                    for sm in sensor.get('measurements', []):
                        name, value = sm.get('name'), sm.get('value')
                        # Set measurement fields based on the name
                        if name == 'pm1.0': measurement.pm1 = value
                        elif name == 'pm2.5': measurement.pm25 = value
                        elif name == 'pm4.0': measurement.pm4 = value
                        elif name == 'pm10': measurement.pm10 = value
                        elif name == 'pm2.5 aqi': measurement.pm25aqi = value
                        elif name == 'pm10 aqi': measurement.pm10aqi = value
                        elif name == 'pm0.5 NC': measurement.pm05nc = value
                        elif name == 'pm1.0 NC': measurement.pm1nc = value
                        elif name == 'pm2.5 NC': measurement.pm25nc = value
                        elif name == 'pm4.0 NC': measurement.pm4nc = value
                        elif name == 'pm10 NC': measurement.pm10nc = value
                        elif name == 'typical particle size': measurement.tps = value
                        elif name == 'Temperature': measurement.temperature = value
                        elif name == 'Relative Humidity': measurement.humidity = value
                        elif name == 'co2': measurement.co2 = value
                        elif name == 'pressure': measurement.pressure = value
                        elif name == 'EtOH': measurement.etoh = value
                        elif name == 'tvoc': measurement.tvoc = value
                
                measurements_to_save.append(measurement)

        if measurements_to_save:
            Measurement.objects.bulk_create(measurements_to_save)

        messages.success(request, "Measurements updated!")
    else:
        messages.warning(request, "Failed to retrieve data. Please try again later.")
    
    return redirect('devices')

def get_data_allf(age=1):
    ds = Devices.objects.all()
    token = Token.objects.first().token
    device_results = []
    for device in ds:
        def fetch_measurements(token):
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
            }
            params = {
                'age': age,
                'device_id': device.device_id,
            }
            return requests.get(
                'https://api-prd.tsilink.com/api/v3/external/telemetry/legacy-format',
                headers=headers,
                params=params
            )

        response = fetch_measurements(token)

        if response.status_code != 200:
            get_tsi_token()
            token = Token.objects.first().token
            response = fetch_measurements(token)

        if response.status_code == 200:
            data = response.json()
            measurements_to_save = []
            existing_measurement_times = Measurement.objects.filter(device=device).values_list('when', flat=True)

            for m in data:
                measurement_time = timezone.datetime.fromisoformat(m['timestamp'])
                if measurement_time not in existing_measurement_times:

                    measurement = Measurement(
                        when=measurement_time,
                        when_local=measurement_time + timedelta(hours=5),
                        device=device
                    )

                    for sensor in m.get('sensors', []):
                        for sm in sensor.get('measurements', []):
                            name, value = sm.get('name'), sm.get('value')
                            # Set measurement fields based on the name
                            if name == 'pm1.0': measurement.pm1 = value
                            elif name == 'pm2.5': measurement.pm25 = value
                            elif name == 'pm4.0': measurement.pm4 = value
                            elif name == 'pm10': measurement.pm10 = value
                            elif name == 'pm2.5 aqi': measurement.pm25aqi = value
                            elif name == 'pm10 aqi': measurement.pm10aqi = value
                            elif name == 'pm0.5 NC': measurement.pm05nc = value
                            elif name == 'pm1.0 NC': measurement.pm1nc = value
                            elif name == 'pm2.5 NC': measurement.pm25nc = value
                            elif name == 'pm4.0 NC': measurement.pm4nc = value
                            elif name == 'pm10 NC': measurement.pm10nc = value
                            elif name == 'typical particle size': measurement.tps = value
                            elif name == 'Temperature': measurement.temperature = value
                            elif name == 'Relative Humidity': measurement.humidity = value
                            elif name == 'co2': measurement.co2 = value
                            elif name == 'pressure': measurement.pressure = value
                            elif name == 'EtOH': measurement.etoh = value
                            elif name == 'tvoc': measurement.tvoc = value
                    
                    measurements_to_save.append(measurement)

            if measurements_to_save:
                Measurement.objects.bulk_create(measurements_to_save)

            device_results.append(f"{device}: Measurements updated!")
        else:
            device_results.append(f"{device}: Failed to retrieve data!")
    return '\n'.join(device_results)

def get_data_all(request, age=1):
    if request.method=="POST":
        age = request.POST.get('age', 1)
    print(age)
    ds = Devices.objects.all()
    token = Token.objects.first().token
    for device in ds:
        def fetch_measurements(token):
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
            }
            params = {
                'age': age,
                'device_id': device.device_id,
            }
            return requests.get(
                'https://api-prd.tsilink.com/api/v3/external/telemetry/legacy-format',
                headers=headers,
                params=params
            )

        response = fetch_measurements(token)

        if response.status_code != 200:
            get_tsi_token()
            token = Token.objects.first().token
            response = fetch_measurements(token)

        if response.status_code == 200:
            data = response.json()
            measurements_to_save = []
            existing_measurement_times = Measurement.objects.filter(device=device).values_list('when', flat=True)

            for m in data:
                measurement_time = timezone.datetime.fromisoformat(m['timestamp'])
                if measurement_time not in existing_measurement_times:

                    measurement = Measurement(
                        when=measurement_time,
                        when_local=measurement_time + timedelta(hours=5),
                        device=device
                    )

                    for sensor in m.get('sensors', []):
                        for sm in sensor.get('measurements', []):
                            name, value = sm.get('name'), sm.get('value')
                            # Set measurement fields based on the name
                            if name == 'pm1.0': measurement.pm1 = value
                            elif name == 'pm2.5': measurement.pm25 = value
                            elif name == 'pm4.0': measurement.pm4 = value
                            elif name == 'pm10': measurement.pm10 = value
                            elif name == 'pm2.5 aqi': measurement.pm25aqi = value
                            elif name == 'pm10 aqi': measurement.pm10aqi = value
                            elif name == 'pm0.5 NC': measurement.pm05nc = value
                            elif name == 'pm1.0 NC': measurement.pm1nc = value
                            elif name == 'pm2.5 NC': measurement.pm25nc = value
                            elif name == 'pm4.0 NC': measurement.pm4nc = value
                            elif name == 'pm10 NC': measurement.pm10nc = value
                            elif name == 'typical particle size': measurement.tps = value
                            elif name == 'Temperature': measurement.temperature = value
                            elif name == 'Relative Humidity': measurement.humidity = value
                            elif name == 'co2': measurement.co2 = value
                            elif name == 'pressure': measurement.pressure = value
                            elif name == 'EtOH': measurement.etoh = value
                            elif name == 'tvoc': measurement.tvoc = value
                    
                    measurements_to_save.append(measurement)

            if measurements_to_save:
                Measurement.objects.bulk_create(measurements_to_save)

            print(device, "Measurements updated!")
            messages.success(request, f"{device}: Measurements updated!")
        else:
            print(device, "Failed to retrieve data. Please try individually.")
            messages.warning(request, f"{device}: Failed to retrieve data. Please try individually.")
        
    return redirect('devices')

def get_data_all_lastf():
    token = Token.objects.first().token
    
    def fetch_measurements(token):
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }
        return requests.get(
            'https://api-prd.tsilink.com/api/v3/external/telemetry/legacy-format',
            headers=headers,
        )

    response = fetch_measurements(token)

    if response.status_code != 200:
        get_tsi_token()
        token = Token.objects.first().token
        response = fetch_measurements(token)

    if response.status_code == 200:

        data = response.json()
        measurements_to_create = []
        messages_about_create = []

        device_mapping = {device.device_id: [device.id, device.name] for device in Devices.objects.all()}

        sensor_to_field_mapping = {
            'pm1.0': 'pm1',
            'pm2.5': 'pm25',
            'pm4.0': 'pm4',
            'pm10': 'pm10',
            'pm2.5 aqi': 'pm25aqi',
            'pm10 aqi': 'pm10aqi',
            'pm0.5 NC': 'pm05nc',
            'pm1.0 NC': 'pm1nc',
            'pm2.5 NC': 'pm25nc',
            'pm4.0 NC': 'pm4nc',
            'pm10 NC': 'pm10nc',
            'typical particle size': 'tps',
            'Temperature': 'temperature',
            'Relative Humidity': 'humidity',
            'co2': 'co2',
            'pressure': 'pressure',
            'EtOH': 'etoh',
            'tvoc': 'tvoc'
        }

        for m in data:
            device_m = device_mapping.get(m['device_id'])
            device_id = device_m[0]
            device_name = device_m[1]
            if not device_id:
                continue  # Skip if device not found

            timestamp = timezone.datetime.fromisoformat(m['timestamp'])
            
            # Check if the measurement already exists in a single query
            existing_measurements = set(Measurement.objects.filter(when=timestamp, device_id=device_id).values_list('when', flat=True))

            if timestamp not in existing_measurements:
                measurement = Measurement(
                    when=timestamp,
                    when_local=timestamp + timezone.timedelta(hours=5),
                    device_id=device_id,
                )

                # Extract sensor measurements and map them to model fields
                sensor_data = {sm['name']: sm['value'] for sensor in m['sensors'] for sm in sensor['measurements']}
                for sensor_name, value in sensor_data.items():
                    model_field_name = sensor_to_field_mapping.get(sensor_name)
                    if model_field_name:
                        setattr(measurement, model_field_name, value)

                measurements_to_create.append(measurement)
                messages_about_create.append(device_name + " updated!")

        # Bulk create measurements to optimize database writes
        if measurements_to_create:
            Measurement.objects.bulk_create(measurements_to_create)

        # messages.info(request, "Updated.")
        return "success", '<br>'.join(f"{i+1}. {name}" for i, name in enumerate(messages_about_create))
    else:
        return "warning", "Failed to fetch data."

def get_data_all_last(request):
    info, text = get_data_all_lastf()
    if info == 'success':
        messages.success(request, mark_safe(text))
    else:
        messages.warning(request, text)

    return redirect('devices')

def aget_data_all_last(request):
    token = Token.objects.first().token

    def fetch_measurements(token):
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }
        return requests.get(
            'https://api-prd.tsilink.com/api/v3/external/telemetry/legacy-format',
            headers=headers,
        )

    response = fetch_measurements(token)

    if response.status_code != 200:
        get_tsi_token()
        token = Token.objects.first().token
        response = fetch_measurements(token)

    if response.status_code == 200:
        data = response.json()
        for m in data:
            device = Devices.objects.filter(device_id=m['device_id']).first()
            if device:
                device_id = device.id
                timestamp = timezone.datetime.fromisoformat(m['timestamp'])
                
                count = Measurement.objects.filter(when=timestamp, device_id=device_id).count()
                if count == 0:
                    measurement = Measurement(
                        when=timestamp,
                        when_local=timestamp + timezone.timedelta(hours=5),
                        device_id=device_id,
                    )

                    for sensor in m['sensors']:
                        for sm in sensor['measurements']:
                            if sm['name'] == 'pm1.0':
                                measurement.pm1 = sm['value']
                            elif sm['name'] == 'pm2.5':
                                measurement.pm25 = sm['value']
                            elif sm['name'] == 'pm4.0':
                                measurement.pm4 = sm['value']
                            elif sm['name'] == 'pm10':
                                measurement.pm10 = sm['value']
                            elif sm['name'] == 'pm2.5 aqi':
                                measurement.pm25aqi = sm['value']
                            elif sm['name'] == 'pm10 aqi':
                                measurement.pm10aqi = sm['value']
                            elif sm['name'] == 'pm0.5 NC':
                                measurement.pm05nc = sm['value']
                            elif sm['name'] == 'pm1.0 NC':
                                measurement.pm1nc = sm['value']
                            elif sm['name'] == 'pm2.5 NC':
                                measurement.pm25nc = sm['value']
                            elif sm['name'] == 'pm4.0 NC':
                                measurement.pm4nc = sm['value']
                            elif sm['name'] == 'pm10 NC':
                                measurement.pm10nc = sm['value']
                            elif sm['name'] == 'typical particle size':
                                measurement.tps = sm['value']
                            elif sm['name'] == 'Temperature':
                                measurement.temperature = sm['value']
                            elif sm['name'] == 'Relative Humidity':
                                measurement.humidity = sm['value']
                            elif sm['name'] == 'co2':
                                measurement.co2 = sm['value']
                            elif sm['name'] == 'pressure':
                                measurement.pressure = sm['value']
                            elif sm['name'] == 'EtOH':
                                measurement.etoh = sm['value']
                            elif sm['name'] == 'tvoc':
                                measurement.tvoc = sm['value']

                    measurement.save()

        request.session['status'] = 'Updated!'
        request.session['alert'] = 'alert-success'
    else:
        request.session['status'] = 'Failed to fetch data!'
        request.session['alert'] = 'alert-danger'

    if token:

        if response.status_code == 200:
            data = response.json()
            for m in data:
                device = Devices.objects.filter(device_id=m['device_id']).first()
                if device:
                    device_id = device.id
                    timestamp = timezone.datetime.fromisoformat(m['timestamp'])
                    
                    # Check if the measurement already exists
                    count = Measurement.objects.filter(when=timestamp, device_id=device_id).count()
                    if count == 0:
                        # Create and save the new measurement
                        measurement = Measurement(
                            when=timestamp,
                            when_local=timestamp + timezone.timedelta(hours=5),
                            device_id=device_id,
                        )

                        # Extract sensor measurements
                        for sensor in m['sensors']:
                            for sm in sensor['measurements']:
                                if sm['name'] == 'pm1.0':
                                    measurement.pm1 = sm['value']
                                elif sm['name'] == 'pm2.5':
                                    measurement.pm25 = sm['value']
                                elif sm['name'] == 'pm4.0':
                                    measurement.pm4 = sm['value']
                                elif sm['name'] == 'pm10':
                                    measurement.pm10 = sm['value']
                                elif sm['name'] == 'pm2.5 aqi':
                                    measurement.pm25aqi = sm['value']
                                elif sm['name'] == 'pm10 aqi':
                                    measurement.pm10aqi = sm['value']
                                elif sm['name'] == 'pm0.5 NC':
                                    measurement.pm05nc = sm['value']
                                elif sm['name'] == 'pm1.0 NC':
                                    measurement.pm1nc = sm['value']
                                elif sm['name'] == 'pm2.5 NC':
                                    measurement.pm25nc = sm['value']
                                elif sm['name'] == 'pm4.0 NC':
                                    measurement.pm4nc = sm['value']
                                elif sm['name'] == 'pm10 NC':
                                    measurement.pm10nc = sm['value']
                                elif sm['name'] == 'typical particle size':
                                    measurement.tps = sm['value']
                                elif sm['name'] == 'Temperature':
                                    measurement.temperature = sm['value']
                                elif sm['name'] == 'Relative Humidity':
                                    measurement.humidity = sm['value']
                                elif sm['name'] == 'co2':
                                    measurement.co2 = sm['value']
                                elif sm['name'] == 'pressure':
                                    measurement.pressure = sm['value']
                                elif sm['name'] == 'EtOH':
                                    measurement.etoh = sm['value']
                                elif sm['name'] == 'tvoc':
                                    measurement.tvoc = sm['value']

                        measurement.save()

            request.session['status'] = 'Updated!'
            request.session['alert'] = 'alert-success'
        else:
            request.session['status'] = 'Failed to fetch data!'
            request.session['alert'] = 'alert-danger'
    else:
        request.session['status'] = 'Need to get token!'
        request.session['alert'] = 'alert-warning'

    return redirect('tsi_home')  # Replace with your actual URL name


@login_exempt
def pm25_for_chart(request, device_id):
    now = timezone.now()
    last_24_hours = now - timezone.timedelta(hours=24)
    measurements = Measurement.objects.filter(
        device_id=device_id,
        when__gte=last_24_hours
    ).order_by('when').values('pm25', 'when_local')
    # data = {
    #     "labels": [measurement.when_local.strftime("%H:%M") for measurement in measurements],
    #     "pm25_values": [measurement.pm25 for measurement in measurements],
    # }
    # print("===============================")
    # print(measurements)
    if measurements.count()>0:
        df = pd.DataFrame(list(measurements))
        df_= meanize_by_hours(df)
        df_["date"] = df_.index.to_series().apply(lambda x: x.date().strftime('%Y-%m-%d'))
        df_["time"] = df_.index.to_series().apply(lambda x: x.time().strftime('%H:%M'))
        # df_.sort_index(inplace=True)
        df_ = df_.to_dict('records')

        data_24 = {
            "labels": [measurement['time'] for measurement in df_],
            "pm25_values": [measurement['pm25'] if not pd.isnull(measurement['pm25']) else 0 for measurement in df_],
        }
    else:
        data_24 = {
            "labels": [],
            "pm25_values": [],
        }

    last_30_days = now - timezone.timedelta(days=30)

    measurements = Measurement.objects.filter(
        device_id=device_id,
        when__gte=(last_30_days)
    ).order_by('when').values('pm25', 'when_local')

    if measurements.count()>0:
        df = pd.DataFrame(list(measurements))
        df_= meanize_by_days(df)
        df_["date"] = df_.index.to_series().apply(lambda x: x.date().strftime('%Y-%m-%d'))
        df_["time"] = df_.index.to_series().apply(lambda x: x.time().strftime('%H:%M'))
        df_ = df_.to_dict('records')

        data_30 = {
            "labels": [measurement['date'] for measurement in df_],
            "pm25_values": [measurement['pm25'] if not pd.isnull(measurement['pm25']) else 0 for measurement in df_],
        }
    else:
        data_30 = {
            "labels": [],
            "pm25_values": [],
        }

    data = {
        'data24': data_24,
        'data30': data_30,
    }
    return JsonResponse(data)

@login_exempt
def login(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        from django.contrib.auth import login, authenticate  # add this

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            # messages.info(request, f"You are now logged in as {username}.")
            return redirect("index")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "login.html")

def logout(request):
    from django.contrib.auth import logout

    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("index")

def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keeps the user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('password_change_done')  # Adjust the redirect as needed
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
        print(form)
    return render(request, 'change_password.html', {'form': form})