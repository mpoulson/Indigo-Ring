# Ring Doorbell plugin for Indigodomo Home Automation

[![N|Solid](http://forums.indigodomo.com/static/www/images/wordmark.png)](http://indigodomo.com)

The plugin will allow triggers when someone presses the doorbell button or triggers a motion alert, as well as the ability to download video in .mp4 format associated with the event.

Requirements:
- A current username/password for your Ring doorbell account
- A Ring doorbell (https://www.amazon.com/dp/B00N2ZDXW2/ref=sr_ph_1?ie=UTF8&qid=1482732196&sr=sr-1&keywords=ring)
- A Ring Subscription (for downloading video)

Supported Devices:
- Ring Doorbell
- Ring Doorbell Pro
- Ring flood light
- Ring Sickup Cam

How to use:
- Install the plugin from (https://github.com/mpoulson/Indigo-Ring/archive/0.1.23.zip)
- Configure username/password
- Add a new device for each Doorbell or other Ring device

What it does:
- Updates Device States on Motion or Ring Events 
- Has separate states for last Motion and Ring event date/time
- Allows you to download video for an event on a device (Requires Ring Cloud subscription; NOTE: you must include a short delay of a few minutes after the event triggers in order for the video to become available from Ring before running the Download Video action)

Sample Use:
- Create a trigger that fires when a Ring device's lastMotionTime Has Any Change
- Fire an action to Download Video for that device's last event after waiting a few minutes by specifying a delay in the configuration of the action in Indigo
- Use another Indigo plugin such as Better Email to send the video as an email attachment to you (note: for this to work, you must also include a delay on this action to allow time for the file download to complete)
