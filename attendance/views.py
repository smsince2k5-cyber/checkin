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
