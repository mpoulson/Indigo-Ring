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

	def _refreshStatesFromHardware(self, dev):

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

		isNew = True

		try: isNew = datetime.strptime(dev.states["lastEventTime"],'%Y-%m-%d %H:%M:%S') < event.now
		except: self.debugLog("Failed to parse some datetimes!  You might need help from the developer!")

		if isNew:
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
			try: self.updateStateOnServer(dev, "batteryLevel", doorbell.batteryLevel)
			except: self.de (dev, "batteryLevel")
			try: self.updateStateOnServer(dev, "model", doorbell.kind)
			except: self.de (dev, "model")

			if (event.kind == "motion"):
				try: self.updateStateOnServer(dev, "lastMotionTime", str(event.now))
				except: self.de (dev, "lastMotionTime")
			else:
				try: self.updateStateOnServer(dev, "lastButtonPressTime", str(event.now))
				except: self.de (dev, "lastButtonPressTime")
		
	def updateStateOnServer(self, dev, state, value):
		if dev.states[state] != value:
			self.debugLog(u"Updating Device: %s, State: %s, Value: %s" % (dev.name, state, value))
			dev.updateStateOnServer(state, value)

	def de (self, dev, value):
		self.errorLog ("[%s] No value found for device: %s, field: %s" % (time.asctime(), dev.name, value))

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
		self.debugLog(u"shutdown called")

	########################################
	def runConcurrentThread(self):
		try:
			while True:
				if self.loginFailed == False:
					if (self.updateFrequency > 0.0) and (time.time() > self.next_update_check):
						self.next_update_check = time.time() + self.updateFrequency
						self.updater.checkForUpdate()

					for dev in indigo.devices.iter("self"):
						if not dev.enabled:
							continue

						self._refreshStatesFromHardware(dev)

				self.sleep(3)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		indigo.server.log(u"validateDeviceConfigUi \"%s\"" % (valuesDict))
		return (True, valuesDict)

	def validatePrefsConfigUi(self, valuesDict):
		self.debugLog(u"Vaidating Plugin Configuration")
		errorsDict = indigo.Dict()
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
		self.debugLog(u"validateDeviceConfigUi called with valuesDict: %s" % str(valuesDict))
		
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
				self.debugLog("\tcomparing %s against deviceList item %s" % (existingDevice.pluginProps["ringId"],id))
				if existingDevice.pluginProps["ringId"] == id:
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
		
		self.debugLog("\tSelectionChanged valuesDict to be returned:\n%s" % (str(valuesDict)))
		return valuesDict
	##########################################
	def checkForUpdates(self):
		self.updater.checkForUpdate()

	def updatePlugin(self):
		self.updater.update()

	def forceUpdate(self):
		self.updater.update(currentVersion='0.0.0')