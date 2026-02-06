from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(email, otp):
    subject = "Your Attendance Login OTP"
    message = f"""
Your OTP for Attendance Login is: {otp}

This OTP is valid for 60 seconds.
Do not share it with anyone.
"""
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


def mask_email(email):
    """
    selvarajn@gmail.com → sel*****n@gmail.com
    """
    name, domain = email.split("@")
    if len(name) <= 3:
        masked = name[0] + "***"
    else:
        masked = name[:3] + "*" * (len(name) - 4) + name[-1]
    return masked + "@" + domain
