from winotify import Notification
Notification(app_id="SkyEvents",
             title="SkyEvents Test",
             msg="If you see this, notifcations work.",
             duration="short").show()
print("Sent test toast")