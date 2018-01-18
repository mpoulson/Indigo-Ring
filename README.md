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
  - Add a new device for each Doorbell

What it does:
  - Updates Devices States on Motion or Ring Events 
  - Has separate states for last Motion and Ring event date/time
  - Allows you to download video for the last event on a device (Requires Ring Cloud subscription; NOTE: you must include a short delay of a few minutes after the event triggers in order for the video to become available from Ring before running the Download Video action)
