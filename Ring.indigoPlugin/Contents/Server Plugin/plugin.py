#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import indigo
import os
import sys
import traceback
import random
import re
import time
from datetime import datetime,tzinfo,timedelta

from Ring import Ring

from copy import deepcopy
from ghpu import GitHubPluginUpdater
# Need json support; Use "simplejson" for Indigo support
try:
	import simplejson as json
except:
	import json

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.Ring = Ring(self)
		self.debug = pluginPrefs.get("debug", False)
		self.UserID = None
		self.Password = None
		self.deviceList = {}
		self.loginFailed = False
		self.retryCount = 0
		self.keepProcessing = True
		self.restartCount = 0

	def _refreshStatesFromHardware(self, dev):
		try:
			doorbellId = dev.pluginProps["doorbellId"]
			#self.debugLog(u"Getting data for Doorbell : %s" % doorbellId)
			doorbell = Ring.GetDevice(self.Ring,doorbellId)

			lastEvents = Ring.GetDoorbellEvent(self.Ring)

			if len(lastEvents) == 0:
				event = Ring.GetDoorbellEventsforId(self.Ring,doorbellId)
			else:
				self.debugLog("Recient Event(s) found!  Count: %s" % len(lastEvents))
				for k,v in lastEvents.iteritems():
					event = v
					break

			if (event == None):
				#self.debugLog("Failed to get correct event data for deviceID:%s.  Will keep retrying for now.  " % doorbellId)
				return

			isNewEvent = True

			if (dev.states["lastEventTime"] != ""):
				try: 
					isNewEvent = datetime.strptime(dev.states["lastEventTime"],'%Y-%m-%d %H:%M:%S') < event.now
				except: 
					self.errorLog("Failed to parse some datetimes. If this happens a lot you might need help from the developer!")

				#Always update the battery level.  In the event we dont have motion but the battery level
				
			if hasattr(doorbell, 'batterylevel'):
				try: self.updateStateOnServer(dev, "batteryLevel", doorbell.batterylevel)
				except: self.de (dev, "batteryLevel")
		
			if isNewEvent:
				try: self.updateStateOnServer(dev, "name", doorbell.description)
				except: self.de (dev, "name")
				try: self.updateStateOnServer(dev, "lastEvent", event.kind)
				except: self.de (dev, "lastEvent")
				try: self.updateStateOnServer(dev, "lastEventTime", str(event.now))
				except: self.de (dev, "lastEventTime")
				try: self.updateStateOnServer(dev, "lastAnswered", event.answered)
				except: self.de (dev, "lastAnswered")
				try: self.updateStateOnServer(dev, "firmware", doorbell.firmware_version)
				except: self.de (dev, "firmware")
				try: self.updateStateOnServer(dev, "model", doorbell.kind)
				except: self.de (dev, "model")
				if (doorbell.state != None):
					try: dev.updateStateOnServer("onOffState", doorbell.state)
					except: self.de (dev, "onOffState")
				if (event.recordingState == "ready"):
					try: self.updateStateOnServer(dev, "recordingUrl", self.Ring.GetRecordingUrl(event.id))
					except: self.de (dev, "recordingUrl")
				if (event.kind == "motion"):
					try: self.updateStateOnServer(dev, "lastMotionTime", str(event.now))
					except: self.de (dev, "lastMotionTime")
				else:
					try: self.updateStateOnServer(dev, "lastButtonPressTime", str(event.now))
					except: self.de (dev, "lastButtonPressTime")
			self.retryCount = 0
		except Exception as err:
			self.retryCount  = self.retryCount + 1
			Ring.logTrace(self.Ring, "Update Error",  {'Error': str(err)})

			self.errorLog("Failed to get correct event data for deviceID:%s. Will keep retrying until max attempts (%s) reached" % (doorbellId, self.pluginPrefs.get("maxRetry", 5)))
			self.errorLog("Error: %s" % err)

	def updateStateOnServer(self, dev, state, value):
		if dev.states[state] != value:
			self.debugLog(u"Updating Device: %s, State: %s, Value: %s" % (dev.name, state, value))
			dev.updateStateOnServer(state, value)

	def de (self, dev, value):
		self.debugLog("[%s] No value found for device: %s, field: %s" % (time.asctime(), dev.name, value))

	########################################
	def startup(self):
		self.debug = self.pluginPrefs.get('showDebugInLog', False)
		self.debugLog(u"startup called")

		self.updater = GitHubPluginUpdater(self)
		#self.updater.checkForUpdate()
		self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', 24)) * 60.0 * 60.0
		self.debugLog(u"updateFrequency = " + str(self.updateFrequency))
		self.next_update_check = time.time()
		self.login(False)

	def login(self, force):
		if self.Ring.startup(force) == False:
			indigo.server.log(u"Login to Ring site failed.  Canceling processing!", isError=True)
			self.loginFailed = True
			return
		else:
			self.loginFailed = False

			self.buildAvailableDeviceList()

	def shutdown(self):
		self.keepProcessing = False
		self.debugLog(u"shutdown called")

	########################################
	def runConcurrentThread(self):
		try:
			while self.keepProcessing:
				if self.loginFailed == False:
					if (self.updateFrequency > 0.0) and (time.time() > self.next_update_check):
						self.next_update_check = time.time() + self.updateFrequency
						self.updater.checkForUpdate()

					for dev in indigo.devices.iter("self"):
						if not dev.enabled:
							continue
						if (int(self.pluginPrefs.get("maxRetry", 5)) != 0 and self.retryCount >= int(self.pluginPrefs.get("maxRetry", 5))):
							self.errorLog("Reached max retry attempts.  Won't Refresh from Server. !")
							self.errorLog("You may need to contact Mike for support.  Please post a message at http://forums.indigodomo.com/viewforum.php?f=235")
							self.sleep(36000)

						self._refreshStatesFromHardware(dev)
						self.restartCount = self.restartCount + 1

				if (self.restartCount > 10000):
					self.restartCount = 0
					indigo.server.log(u"Memory Leak Prevention. Restarting Plugin. - This will happen until I find and fix the leak")
					serverPlugin = indigo.server.getPlugin(self.pluginId)
					serverPlugin.restart(waitUntilDone=False)
					break
				self.sleep(5)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		indigo.server.log(u"validateDeviceConfigUi \"%s\"" % (valuesDict))
		return (True, valuesDict)

	def validatePrefsConfigUi(self, valuesDict):
		self.debugLog(u"Vaidating Plugin Configuration")
		errorsDict = indigo.Dict()
		if valuesDict[u"maxRetry"] == "":
			errorsDict[u"maxRetry"] = u"Please enter retry value."
		else:
			try: int(valuesDict[u"maxRetry"])
			except:
				errorsDict[u"maxRetry"] = u"Please enter a valid Retry Value."
		if len(errorsDict) > 0:
			self.errorLog(u"\t Validation Errors")
			return (False, valuesDict, errorsDict)
		else:
			self.debugLog(u"\t Validation Succesful")
			return (True, valuesDict)
		return (True, valuesDict)

	########################################
	def deviceStartComm(self, dev):
		if self.loginFailed == True:
			return

		self.initDevice(dev)

		dev.stateListOrDisplayStateIdChanged()
		
	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		pass

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			#Check if Debugging is set
			try:
				self.debug = self.pluginPrefs[u'showDebugInLog']
			except:
				self.debug = False

			try:
				if (self.UserID != self.pluginPrefs["UserID"]) or \
					(self.Password != self.pluginPrefs["Password"]):
					indigo.server.log("[%s] Replacting Username/Password." % time.asctime())
					self.UserID = self.pluginPrefs["UserID"]
					self.Password = self.pluginPrefs["Password"]
			except:
				pass

			indigo.server.log("[%s] Processed plugin preferences." % time.asctime())
			self.login(True)
			return True
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		#self.debugLog(u"validateDeviceConfigUi called with valuesDict: %s" % str(valuesDict))
		
		return (True, valuesDict)

	def initDevice(self, dev):
		self.debugLog("Initializing Ring device: %s" % dev.name)
		#if (dev.states["lastEventTime"] == "")
		dev.states["lastEventTime"]  =  str(datetime.strptime('2016-01-01 01:00:00','%Y-%m-%d %H:%M:%S'))
	
	def buildAvailableDeviceList(self):
		self.debugLog("Building Available Device List")

		self.deviceList = self.Ring.GetDevices()

		indigo.server.log("Number of devices found: %i" % (len(self.deviceList)))
		for (k, v) in self.deviceList.iteritems():
			indigo.server.log("\t%s (id: %s)" % (v.description, k))

	def showAvailableDevices(self):
		indigo.server.log("Number of devices found: %i" % (len(self.deviceList)))
		for (id, details) in self.deviceList.iteritems():
			indigo.server.log("\t%s (id: %s)" % (details.description, id))

	def doorbellList(self, filter, valuesDict, typeId, targetId):
		self.debugLog("deviceList called")
		deviceArray = []
		deviceListCopy = deepcopy(self.deviceList)
		for existingDevice in indigo.devices.iter("self"):
			for id in self.deviceList:
				self.debugLog("States: %s" % existingDevice.address)
				
				self.debugLog("\tcomparing %s against deviceList item %s" % (existingDevice.address,id))
				if str(existingDevice.address) == str(id):
					self.debugLog("\tremoving item %s" % (id))
					del deviceListCopy[id]
					break

		if len(deviceListCopy) > 0:
			for (id,value) in deviceListCopy.iteritems():
				deviceArray.append((id,value.description))
		else:
			if len(self.deviceList):
				indigo.server.log("All devices found are already defined")
			else:
				indigo.server.log("No devices were discovered on the network - select \"Rescan for Doorbells\" from the plugin's menu to rescan")

		self.debugLog("\t DeviceList deviceArray:\n%s" % (str(deviceArray)))
		return deviceArray

	def selectionChanged(self, valuesDict, typeId, devId):
		self.debugLog("SelectionChanged")
		if int(valuesDict["doorbell"]) in self.deviceList:
			self.debugLog("Looking up deviceID %s in DeviceList Table" % valuesDict["doorbell"])
			selectedData = self.deviceList[int(valuesDict["doorbell"])]
			valuesDict["address"] = valuesDict["doorbell"]
			valuesDict["doorbellId"] = valuesDict["doorbell"]
			valuesDict["name"] = selectedData.description
			valuesDict["kind"] = selectedData.kind
			valuesDict["firmware"] = selectedData.firmware_version
		
		#self.debugLog(u"\tSelectionChanged valuesDict to be returned:\n%s" % (str(valuesDict)))
		return valuesDict
	##########################################
	def checkForUpdates(self):
		self.updater.checkForUpdate()

	def updatePlugin(self):
		self.updater.update()

	def forceUpdate(self):
		self.updater.update(currentVersion='0.0.0')
	########################################
	# Relay / Dimmer Action callback
	######################
	def actionControlDevice(self, action, dev):
		doorbellId = dev.pluginProps["doorbellId"]
		indigo.server.log(u"Current state is \"%s\"" % (dev.onState), isError=False)
		###### TURN ON ######
		if action.deviceAction == indigo.kDeviceAction.TurnOn:
			# Command hardware module (dev) to turn ON here:
			sendSuccess = self.Ring.SetFloodLightOn(str(doorbellId))
			#sendSuccess = True		# Set to False if it failed.

			if sendSuccess:
				# If success then log that the command was successfully sent.
				indigo.server.log(u"sent \"%s\" %s" % (dev.name, "on"))

				# And then tell the Indigo Server to update the state.
				dev.updateStateOnServer("onOffState", True)
			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "on"), isError=True)

		###### TURN OFF ######
		elif action.deviceAction == indigo.kDeviceAction.TurnOff:
			# Command hardware module (dev) to turn OFF here:
			sendSuccess = self.Ring.SetFloodLightOff(str(doorbellId))

			if sendSuccess:
				# If success then log that the command was successfully sent.
				indigo.server.log(u"sent \"%s\" %s" % (dev.name, "off"))

				# And then tell the Indigo Server to update the state:
				dev.updateStateOnServer("onOffState", False)
			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "off"), isError=True)

		###### TOGGLE ######
		elif action.deviceAction == indigo.kDeviceAction.Toggle:
			# Command hardware module (dev) to toggle here:
			indigo.server.log(u"Current state is \"%s\"" % (dev.onState), isError=True)
			newOnState = not dev.onState
			sendSuccess = True		# Set to False if it failed.

			if sendSuccess:
				# If success then log that the command was successfully sent.
				indigo.server.log(u"sent \"%s\" %s" % (dev.name, "toggle"))

				# And then tell the Indigo Server to update the state:
				dev.updateStateOnServer("onOffState", newOnState)
			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "toggle"), isError=True)