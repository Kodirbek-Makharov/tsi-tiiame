from django.db import models

# Create your models here.

class Token(models.Model):
    token = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

class Devices(models.Model):
    name = models.CharField(max_length=255)
    device_id = models.CharField(max_length=255, unique=True)
    model = models.CharField(max_length=255)
    serial = models.CharField(max_length=255)
    is_indoor = models.BooleanField()
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=10, decimal_places=8)
    is_public = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Measurement(models.Model):
    device = models.ForeignKey(Devices, on_delete=models.CASCADE, related_name='measurements')
    when = models.DateTimeField()
    when_local = models.DateTimeField()
    pm1 = models.FloatField(null=True, blank=True)
    pm25 = models.FloatField(null=True, blank=True)
    pm4 = models.FloatField(null=True, blank=True)
    pm10 = models.FloatField(null=True, blank=True)
    pm25aqi = models.FloatField(null=True, blank=True)
    pm10aqi = models.FloatField(null=True, blank=True)
    pm05nc = models.FloatField(null=True, blank=True)
    pm1nc = models.FloatField(null=True, blank=True)
    pm25nc = models.FloatField(null=True, blank=True)
    pm4nc = models.FloatField(null=True, blank=True)
    pm10nc = models.FloatField(null=True, blank=True)
    tps = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    co2 = models.FloatField(null=True, blank=True)
    pressure = models.FloatField(null=True, blank=True)
    etoh = models.FloatField(null=True, blank=True)
    tvoc = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f'{self.device}: pm25 = {self.pm25}, ({self.when})'