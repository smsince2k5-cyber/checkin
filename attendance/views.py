from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Employee, Attendance
from .forms import EmployeeForm, CheckInForm, CheckOutForm
from datetime import datetime
import base64
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim


from django.shortcuts import render
from datetime import datetime

def home(request):
    return render(request, 'home.html', {'year': datetime.now().year})



# Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def detect_face(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    return faces, gray

def compare_faces(enrolled_path, live_img_array):
    # Read enrolled image
    enrolled_img = cv2.imread(enrolled_path)
    faces1, gray1 = detect_face(enrolled_img)
    faces2, gray2 = detect_face(live_img_array)

    if len(faces1)==0 or len(faces2)==0:
        return False

    # Crop first face
    x,y,w,h = faces1[0]
    face1_crop = gray1[y:y+h, x:x+w]
    x2,y2,w2,h2 = faces2[0]
    face2_crop = gray2[y2:y2+h2, x2:x2+w2]
    face2_crop = cv2.resize(face2_crop, (face1_crop.shape[1], face1_crop.shape[0]))
    score, _ = ssim(face1_crop, face2_crop, full=True)
    return score > 0.5  # similarity threshold

# ---------------------- ENROLL ----------------------
def enroll_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            # Auto-generate Employee ID
            last = Employee.objects.order_by('-emp_id').first()
            employee.emp_id = 1001 if not last else last.emp_id + 1
            # Save face image from base64
            face_data = request.POST.get('face_image_data')
            if face_data:
                employee.save_face_base64(face_data)
            employee.save()
            messages.success(request, f"Employee enrolled successfully! ID: {employee.emp_id}")
            return redirect('enroll_employee')
    else:
        form = EmployeeForm()
    return render(request, 'enroll.html', {'form': form})

# ---------------------- CHECK-IN ----------------------
def check_in(request):
    if request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            emp_input = form.cleaned_data['emp_id_or_phone']
            face_data = form.cleaned_data['face_image_data']
            # Convert base64 to numpy array
            format, imgstr = face_data.split(';base64,')
            nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
            live_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            # Get employee
            try:
                employee = Employee.objects.get(emp_id=emp_input)
            except:
                try:
                    employee = Employee.objects.get(phone=emp_input)
                except:
                    messages.error(request, "Employee not found.")
                    return redirect('checkin')
            # Compare faces
            if compare_faces(employee.face_image.path, live_img):
                now = datetime.now()
                attendance, created = Attendance.objects.get_or_create(employee=employee, date=now.date())
                if attendance.check_in:
                    messages.warning(request, "Already checked in!")
                else:
                    attendance.check_in = now.time()
                    # Status
                    if now.hour < 9:
                        attendance.status = "Early"
                        msg = "Check-in successful – Status: Early"
                    elif now.hour == 9 and now.minute <= 10:
                        attendance.status = "On Time"
                        msg = "Check-in successful – Status: On Time"
                    else:
                        attendance.status = "Late"
                        msg = "Check-in recorded – Status: Late Today"
                    attendance.save()
                    messages.success(request, msg)
            else:
                messages.error(request, "Face verification failed. Please try again.")
            return redirect('checkin')
    else:
        form = CheckInForm()
    return render(request, 'checkin.html', {'form': form})

# ---------------------- CHECK-OUT ----------------------
def check_out(request):
    if request.method == 'POST':
        form = CheckOutForm(request.POST)
        if form.is_valid():
            emp_input = form.cleaned_data['emp_id_or_phone']
            face_data = form.cleaned_data['face_image_data']
            # Convert base64 to numpy array
            format, imgstr = face_data.split(';base64,')
            nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
            live_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            # Get employee
            try:
                employee = Employee.objects.get(emp_id=emp_input)
            except:
                try:
                    employee = Employee.objects.get(phone=emp_input)
                except:
                    messages.error(request, "Employee not found.")
                    return redirect('checkout')
            # Compare faces
            if compare_faces(employee.face_image.path, live_img):
                now = datetime.now()
                attendance = Attendance.objects.filter(employee=employee, date=now.date()).first()
                if not attendance or not attendance.check_in:
                    messages.warning(request, "Check-in not found for today!")
                elif attendance.check_out:
                    messages.warning(request, "Already checked out!")
                else:
                    attendance.check_out = now.time()
                    attendance.calculate_working_hours()
                    if attendance.loss_of_pay:
                        msg = f"Check-out recorded – Working hours: {attendance.working_hours} hrs – Loss of pay applicable"
                    else:
                        msg = f"Check-out successful – Working hours: {attendance.working_hours} hrs"
                    messages.success(request, msg)
            else:
                messages.error(request, "Face verification failed. Please try again.")
            return redirect('checkout')
    else:
        form = CheckOutForm()
    return render(request, 'checkout.html', {'form': form})

from datetime import date
import calendar
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Employee, Attendance, OTP
from .utils import send_otp_email, mask_email

# ---------- LOGIN VIA PHONE ----------
def login_phone(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        try:
            employee = Employee.objects.get(phone=phone)
        except Employee.DoesNotExist:
            messages.error(request, "Phone number not registered")
            return redirect("login_phone")

        OTP.objects.filter(phone=phone).delete()
        otp_code = OTP.generate_otp()
        OTP.objects.create(phone=phone, code=otp_code)

        send_otp_email(employee.email, otp_code)

        request.session["phone"] = phone
        request.session["masked_email"] = mask_email(employee.email)

        return redirect("verify_otp")

    return render(request, "auth/login_phone.html")


# # ---------- VERIFY OTP ----------
# def verify_otp(request):
#     phone = request.session.get("phone")
#     masked_email = request.session.get("masked_email")
#     if not phone:
#         return redirect("login_phone")

#     if request.method == "POST":
#         entered_otp = request.POST.get("otp")
#         try:
#             otp_obj = OTP.objects.get(phone=phone, code=entered_otp, is_verified=False)
#         except OTP.DoesNotExist:
#             messages.error(request, "Invalid OTP")
#             return redirect("verify_otp")

#         if otp_obj.is_expired():
#             messages.error(request, "OTP expired")
#             return redirect("login_phone")

#         otp_obj.is_verified = True
#         otp_obj.save()

#         employee = Employee.objects.get(phone=phone)
#         request.session["employee_id"] = employee.id

#         return redirect("attendance_calendar", emp_id=employee.emp_id)

#     return render(request, "auth/verify_otp.html", {"masked_email": masked_email})
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import OTP, Employee

def verify_otp(request):
    phone = request.session.get("phone")
    masked_email = request.session.get("masked_email")
    if not phone:
        return redirect("login_phone")  # Redirect if no phone in session

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        try:
            otp_obj = OTP.objects.get(phone=phone, code=entered_otp, is_verified=False)
        except OTP.DoesNotExist:
            messages.error(request, "Invalid OTP")
            return redirect("verify_otp")

        if otp_obj.is_expired():
            messages.error(request, "OTP expired")
            return redirect("login_phone")

        otp_obj.is_verified = True
        otp_obj.save()

        # Mark employee as logged in
        employee = Employee.objects.get(phone=phone)
        request.session["employee_id"] = employee.id

        return redirect("attendance_calendar", emp_id=employee.emp_id)

    return render(request, "auth/verify_otp.html", {"masked_email": masked_email})


# ---------- ATTENDANCE CALENDAR ----------
def attendance_calendar(request, emp_id):
    if not request.session.get("employee_id"):
        return redirect("login_phone")

    employee = get_object_or_404(Employee, emp_id=emp_id)

    year = int(request.GET.get("year", date.today().year))
    month = int(request.GET.get("month", date.today().month))

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    attendance_qs = Attendance.objects.filter(employee=employee, date__range=(first_day, last_day))
    attendance_map = {att.date: att for att in attendance_qs}

    cal = calendar.Calendar(calendar.SUNDAY)
    month_days = []
    for week in cal.monthdatescalendar(year, month):
        week_data = []
        for day in week:
            week_data.append({"date": day, "attendance": attendance_map.get(day)} if day.month == month else None)
        month_days.append(week_data)

    working_days = sum(1 for d in calendar.Calendar().itermonthdates(year, month) if d.month == month and d.weekday() < 5)
    worked_days = attendance_qs.filter(check_in__isnull=False, check_out__isnull=False).count()
    leave_days = attendance_qs.filter(status__iexact="Leave").count()
    holidays = attendance_qs.filter(status__iexact="Holiday").count()
    payable_days = worked_days + leave_days + holidays

    context = {
        "employee": employee,
        "month_days": month_days,
        "month": month,
        "year": year,
        "month_name": calendar.month_name[month],
        "working_days": working_days,
        "worked_days": worked_days,
        "leave_days": leave_days,
        "holidays": holidays,
        "payable_days": payable_days,
    }

    return render(request, "calendar.html", context)
