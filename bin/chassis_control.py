#!/usr/bin/env python

import sys
#from gi.repository import GObject
import gobject
import dbus
import dbus.service
import dbus.mainloop.glib
import Openbmc

DBUS_NAME = 'org.openbmc.control.Chassis'
OBJ_NAME = '/org/openbmc/control/'+sys.argv[1]

POWER_OFF = 0
POWER_ON = 1

BOOTED = 100

class ChassisControlObject(dbus.service.Object):
	def __init__(self,bus,name):
		self.dbus_objects = { }

		dbus.service.Object.__init__(self,bus,name)
		## load utilized objects
		self.dbus_objects = {
			'power_control' : { 
				'bus_name' : 'org.openbmc.control.Power',
				'object_name' : '/org/openbmc/control/SystemPower_0',
				'interface_name' : 'org.openbmc.control.Power'
			},
			'identify_led' : {
				'bus_name' : 'org.openbmc.leds.ChassisIdentify',
				'object_name' : '/org/openbmc/leds/ChassisIdentify_0',
				'interface_name' : 'org.openbmc.Led'
			}
		}
		#self.power_sequence = 0
		self.reboot = 0	
		self.last_power_state = 0

		bus.add_signal_receiver(self.power_button_signal_handler, 
					dbus_interface = "org.openbmc.Button", signal_name = "ButtonPressed", 
					path="/org/openbmc/buttons/PowerButton_0" )
    		bus.add_signal_receiver(self.host_watchdog_signal_handler, 
					dbus_interface = "org.openbmc.Watchdog", signal_name = "WatchdogError")
		bus.add_signal_receiver(self.SystemStateHandler,signal_name = "GotoSystemState")


	def getInterface(self,name):
		o = self.dbus_objects[name]
		obj = bus.get_object(o['bus_name'],o['object_name'])
		return dbus.Interface(obj,o['interface_name'])

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='s')
	def getID(self):
		return id

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='')
	def setIdentify(self):
		print "Turn on identify"
		intf = self.getInterface('identify_led')
		intf.setOn()	
		return None

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='')
	def clearIdentify(self):
		print "Turn on identify"
		intf = self.getInterface('identify_led')
		intf.setOff()
		return None

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='')
	def powerOn(self):
		print "Turn on power and boot"
		self.reboot = 0
		if (self.getPowerState()==0):
			intf = self.getInterface('power_control')
			intf.setPowerState(POWER_ON)
		return None

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='')
	def powerOff(self):
		print "Turn off power"
		intf = self.getInterface('power_control')
		intf.setPowerState(POWER_OFF)
		return None

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='')
	def softPowerOff(self):
		print "Soft off power"
		## Somehow tell host to shutdown via ipmi
		return None

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='')
	def reboot(self):
		print "Rebooting"
		self.reboot=1
		intf.softPowerOff()
		return None

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='i')
	def getPowerState(self):
		intf = self.getInterface('power_control')
		return intf.getPowerState()

	@dbus.service.method(DBUS_NAME,
		in_signature='', out_signature='')
	def setDebugMode(self):
		return None

	@dbus.service.method(DBUS_NAME,
		in_signature='i', out_signature='')
	def setPowerPolicy(self,policy):
		return None


	## Signal handler

	def SystemStateHandler(self,state_name):
		if (state_name == "POWERED_OFF" and self.reboot==1):
			self.powerOn()
				

	def power_button_signal_handler(self):
		# toggle power
		state = self.getPowerState()
		if state == POWER_OFF:
			self.powerOn()
		elif state == POWER_ON:
			self.powerOff();
		
		# TODO: handle long press and reset

	def host_watchdog_signal_handler(self):
		print "Watchdog Error, Hard Rebooting"
		self.reboot = 1
		self.powerOff()
		

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = Openbmc.getDBus()
    name = dbus.service.BusName(DBUS_NAME, bus)
    obj = ChassisControlObject(bus, OBJ_NAME)
    mainloop = gobject.MainLoop()
    
    print "Running ChassisControlService"
    mainloop.run()

