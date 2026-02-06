from django.db import models
from datetime import date, datetime
from django.core.files.base import ContentFile
import base64

class Employee(models.Model):
    emp_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50)
    salary = models.FloatField()
    face_image = models.ImageField(upload_to='faces/')  # Store captured camera image

    def save_face_base64(self, base64_str, filename=None):
        """Decode base64 image and save to ImageField"""
        if not filename:
            filename = f"{self.name}.jpg"
        format, imgstr = base64_str.split(';base64,')
        data = ContentFile(base64.b64decode(imgstr), name=filename)
        self.face_image.save(filename, data, save=True)

    def __str__(self):
        return f"{self.name} ({self.emp_id})"


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, blank=True)  # Early / On Time / Late
    working_hours = models.FloatField(default=0)           # in hours
    loss_of_pay = models.BooleanField(default=False)

    def calculate_working_hours(self):
        if self.check_in and self.check_out:
            t_in = datetime.combine(self.date, self.check_in)
            t_out = datetime.combine(self.date, self.check_out)
            delta = t_out - t_in
            self.working_hours = round(delta.total_seconds() / 3600, 2)
            self.loss_of_pay = self.check_out < datetime.strptime('16:00', '%H:%M').time()
            self.save()

    def __str__(self):
        return f"{self.employee.name} - {self.date}"


import random
from datetime import timedelta
from django.db import models
from django.utils import timezone


class OTP(models.Model):
    phone = models.CharField(max_length=15)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(seconds=60)

    @staticmethod
    def generate_otp():
        return str(random.randint(1000, 9999))

    def __str__(self):
        return f"{self.phone} - {self.code}"

