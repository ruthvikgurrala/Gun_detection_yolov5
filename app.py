from flask import Flask, render_template, Response, jsonify
import torch
import cv2

# Load the YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5/runs/train/exp2/weights/best.pt', force_reload=True)

app = Flask(__name__)
camera = None
streaming = False
gun_detected = False  # Initialize global variable


def initialize_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)

def release_camera():
    global camera
    if camera and camera.isOpened():
        camera.release()

def generate_frames():
    global streaming, camera, gun_detected
    initialize_camera()
    while streaming:
        success, frame = camera.read()
        if not success:
            break
        else:
            results = model(frame)
            gun_detected_detected_now = False  # Temporary flag for this frame
            for result in results.xyxy[0]:
                x1, y1, x2, y2, conf, cls = result
                if int(cls) == 0 and conf >= 0.45:  # Only apply threshold for guns
                    gun_detected_detected_now = True
                    label = f'{model.names[int(cls)]} {conf:.2f}'
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                    '''# Send an email notification when a gun is detected
                    send_email('Gun Detected', 'A gun was detected in the camera feed!', 'ruthvikgurrala@gmail.com')
                    # Send signal to frontend to show popup
                    return jsonify({'email_sent': True})'''
                

                else:  # For other classes
                    label = f'{model.names[int(cls)]} {conf:.2f}'
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            # Check if gun is newly detected and send an email only once
            if gun_detected_detected_now and not gun_detected:
                gun_detected = True  # Update global variable
                send_email('Gun Detected', 'A gun was detected in the camera feed!', 'gurrala141@gmail.com')

            elif not gun_detected_detected_now:
                gun_detected = False  # Reset if no gun is detected
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    global streaming
    if not streaming:
        return "Stream is off", 204  # No Content
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_stream', methods=['POST'])
def toggle_stream():
    global streaming
    streaming = not streaming
    if streaming:
        initialize_camera()
    else:
        release_camera()
    return jsonify(streaming=streaming)

@app.route('/gun_detected_status')
def gun_detected_status():
    """This API returns whether a gun has been detected"""
    return jsonify({"gun_detected": gun_detected})

@app.route('/')
def index():
    return render_template('index.html')


'''implementing notification using msg'''
from twilio.rest import Client

def send_sms(body, to_phone):
    account_sid = 'your_account_sid'
    auth_token = 'your_auth_token'
    from_phone = 'your_twilio_phone_number'
    
    # Set up Twilio client
    client = Client(account_sid, auth_token)
    
    # Send the SMS
    message = client.messages.create(
        body=body,
        from_=from_phone,
        to=to_phone
    )
    return message.sid


'''implementing notification using smtp'''
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
    # Load environment variables
load_dotenv()
# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
def send_email(subject, body, recipient_email):

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
        
        print("Email sent successfully!")
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    app.run(debug=True)
