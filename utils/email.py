# utils/email.py
# WORKS WITH OUTLOOK / OFFICE 365 / HOTMAIL / REVA.EDU.IN

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_attendance_email(name, email, action, timestamp=None, checkin_time=None, checkout_time=None, total_hours=None, total_minutes=None, duration_min=None, login_time=None, logout_time=None):
    """
    Sends beautiful email with attendance details
    For DAILY_SUMMARY: shows complete attendance record (check-in, check-out, total hours)
    For ABSENT_AUTO: shows auto-absent notification
    """
    try:
        SENDER_EMAIL = "prashanthsrinivas2001@gmail.com"
        SENDER_PASSWORD = "zdle xgot feac mwdv"

        if timestamp is None:
            timestamp = datetime.now().strftime("%d %b %Y • %H:%M:%S")

        if action == "DAILY_SUMMARY":
            subject = "✅ Attendance Recorded Successfully"
            title = "Daily Attendance Summary"
            message = "Your attendance for today has been recorded successfully."
            
            # Format total time display
            if total_hours > 0 and total_minutes > 0:
                total_time_str = f"{total_hours}h {total_minutes}m"
            elif total_hours > 0:
                total_time_str = f"{total_hours}h"
            else:
                total_time_str = f"{total_minutes}m"
            
            details_html = f"""
                <div style="background: #f0f9ff; padding: 25px; border-radius: 12px; border-left: 5px solid #10b981; margin: 20px 0;">
                    <p style="margin: 8px 0; font-size: 18px;"><strong>Check-in:</strong> <span style="color: #059669;">{checkin_time}</span></p>
                    <p style="margin: 8px 0; font-size: 18px;"><strong>Check-out:</strong> <span style="color: #dc2626;">{checkout_time}</span></p>
                    <p style="margin: 8px 0; font-size: 18px;"><strong>Total Hours:</strong> <span style="color: #1e40af; font-weight: bold;">{total_time_str}</span></p>
                </div>
                <p style="margin: 15px 0; color: #059669; font-weight: 600; font-size: 16px;">✅ Status: Present</p>
            """
        elif action == "ABSENT_AUTO":
            subject = "⚠️ Attendance Update — Auto Absent"
            title = "Session Timed Out"
            message = "You were marked absent (no checkout ≥9 hours)"
            details_html = f"""
                <div style="background: #fef2f2; padding: 25px; border-radius: 12px; border-left: 5px solid #ef4444; margin: 20px 0;">
                    <p style="margin: 8px 0; font-size: 18px;"><strong>Auto Logout Time:</strong> {timestamp}</p>
                    <p style="margin: 8px 0; color: #dc2626; font-weight: 600;">❌ Status: Absent (User Fault)</p>
                    <p style="margin: 8px 0; color: #6b7280;">Reason: Failed to checkout within 9 hours</p>
                </div>
            """
        else:  # Fallback for any other cases
            subject = "Attendance Update"
            title = "Attendance Notification"
            message = "Your attendance status has been updated"
            details_html = f"""
                <p><strong>Time:</strong> {timestamp}</p>
                <p><strong>Action:</strong> {action}</p>
            """

        html = f"""
        <div style="font-family:Arial; max-width:600px; margin:auto; background:white; border-radius:16px; overflow:hidden; box-shadow:0 10px 40px rgba(0,0,0,0.1);">
            <div style="background:#FF5500; padding:35px; text-align:center; color:white;">
                <h1>REVA University</h1>
                <p>Smart Biometric Attendance System</p>
            </div>
            <div style="padding:45px; text-align:center;">
                <h2>Hello {name}!</h2>
                <p style="font-size:21px;"><strong>{message}</strong></p>
                
                <div style="background:#f0f9ff; padding:30px; border-radius:14px; margin:35px 0;">
                    {details_html}
                </div>
                
                <p>Thank you for using the system!</p>
            </div>
            <div style="background:#1e293b; color:#e2e8f0; padding:25px; text-align:center;">
                © 2025 REVA University • Biometric Kiosk v2.7
            </div>
        </div>
        """

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())

        print(f"EMAIL SENT → {email} | {action}")

    except Exception as e:
        print(f"EMAIL FAILED → {e}")


def send_structured_attendance_email(name, email, date, in_time, out_time, status):
    """
    Sends attendance email in the exact structured format requested
    
    Args:
        name (str): User's full name
        email (str): Recipient email address
        date (str): Date in DD/MM/YY format (e.g., "09/12/24")
        in_time (str): In-time (e.g., "09:30 AM")
        out_time (str): Out-time (e.g., "06:15 PM")
        status (str): Attendance status (e.g., "Present", "Absent")
    """
    try:
        SENDER_EMAIL = "prashanthsrinivas2001@gmail.com"
        SENDER_PASSWORD = "zdle xgot feac mwdv"

        subject = f"Attendance Status for {date}"

        # Create structured email content exactly as specified
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.1);">
            <div style="background:#FF5500; padding:35px; text-align:center; color:white;">
                <h1 style="margin:0; font-size:32px; font-weight:bold;">RACE, REVA University</h1>
                <p style="margin:10px 0 0; font-size:19px;">Smart Biometric Attendance System</p>
            </div>
            
            <div style="padding: 20px;">
                <p style="font-size: 16px; margin-bottom: 20px;">
                    <strong>Hi {name},</strong>
                </p>
            
            <p style="font-size: 14px; margin-bottom: 20px;">
                The following is your attendance status for <strong>{date}</strong>:
            </p>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px; border: 1px solid #ddd;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="border: 1px solid #ddd; padding: 12px; text-align: left; font-weight: bold;">Date</th>
                        <th style="border: 1px solid #ddd; padding: 12px; text-align: left; font-weight: bold;">In-Time</th>
                        <th style="border: 1px solid #ddd; padding: 12px; text-align: left; font-weight: bold;">Out-Time</th>
                        <th style="border: 1px solid #ddd; padding: 12px; text-align: left; font-weight: bold;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 12px;">{date}</td>
                        <td style="border: 1px solid #ddd; padding: 12px;">{in_time}</td>
                        <td style="border: 1px solid #ddd; padding: 12px;">{out_time}</td>
                        <td style="border: 1px solid #ddd; padding: 12px;">{status}</td>
                    </tr>
                </tbody>
            </table>
            
            <p style="font-size: 14px; margin-bottom: 8px;">
                In case of any discrepancy, please contact your HR department.
            </p>
            <p style="font-size: 14px; margin-bottom: 25px;">
                Please apply for Regularization / OD / Leave if required.
            </p>
            
                <p style="font-size: 12px; color: #dc2626; font-style: italic;">
                    Auto mail generated by the system, please do not reply.
                </p>
            </div>
            
            <div style="background:#1e293b; color:#e2e8f0; padding:25px; text-align:center; font-size:14px;">
                © 2025 RACE, REVA University
            </div>
        </div>
        """

        # Create plain text version for email clients that don't support HTML
        plain_text = f"""Hi {name},

The following is your attendance status for {date}:

Date         In-Time      Out-Time     Status
{date}      {in_time}    {out_time}   {status}

In case of any discrepancy, please contact your HR department.
Please apply for Regularization / OD / Leave if required.

Auto mail generated by the system, please do not reply.
"""

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = subject
        
        # Add both plain text and HTML versions
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())

        print(f"STRUCTURED EMAIL SENT → {email} | Attendance for {date}")

    except Exception as e:
        print(f"STRUCTURED EMAIL FAILED → {e}")

