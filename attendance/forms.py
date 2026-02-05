from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'phone', 'email', 'role', 'salary']

class CheckInForm(forms.Form):
    emp_id_or_phone = forms.CharField(max_length=20)
    face_image_data = forms.CharField(widget=forms.HiddenInput())

class CheckOutForm(forms.Form):
    emp_id_or_phone = forms.CharField(max_length=20)
    face_image_data = forms.CharField(widget=forms.HiddenInput())
