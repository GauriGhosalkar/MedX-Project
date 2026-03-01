from plyer import notification
import time
import random

# MedX Forensic & Verification Reminders
medx_alerts = [
    ("🔍 Audit Pending", 
     "New medicine batch uploaded. Start forensic verification now."),

    ("🛡️ Security Protocol", 
     "Ensure your database connection is encrypted. Safety first!"),

    ("🧪 Quality Control", 
     "Double-check 'Counterfeit' flagged items. Accuracy is key in forensics."),

    ("📊 Export Logs", 
     "End of shift approaching. Remember to export your Forensic Audit PDF."),

    ("📷 Scanner Calibration", 
     "Calibrate your camera module for 99% confidence in image detection."),

    ("🚀 Stay Alert", 
     "Detecting fakes saves lives. You are making a difference today!")
]

def medx_forensic_mentor():
    print("MedX Notification System Started... (Press Ctrl+C to stop)")
    while True:
        # Select a random forensic alert
        title, message = random.choice(medx_alerts)

        notification.notify(
            title="MedX Forensic Alert",
            message=f"{title}\n{message}",
            app_name="MedX Verification",
            timeout=10  # Notification stays for 10 seconds
        )

        # Wait 30 minutes (1800 seconds) before next notification
        # Set to 10 for testing, change to 1800 for real use
        time.sleep(1800) 

if __name__ == "__main__":
    medx_forensic_mentor()