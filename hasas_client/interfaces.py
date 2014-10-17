import random
import time
import json


class Actuator(object):

    do = {}

    def __init__(self, interface_id):
        self.interface_id = interface_id


    def describe(self):
        return {
            "id": self.interface_id,
            "type": self.type,
            "description": self.__doc__,
            "actions": [{
                "name": action,
                "description": self.do[action].__doc__,
                "params": self.do[action].func_code.co_varnames[1:]
            } for action in self.do]
        }

    def actuate(self, action, *args, **kwargs):
        try:
            self.do[action](*args, **kwargs)
        except KeyError:
            print "unknown action"


class Sensor(object):

    def describe(self):
        return {
            "id": self.id,
            "type": self.type,
            "description": self.__doc__,
        }
        print self.__doc__


class LightBulbActuator(Actuator):
    """Set the status of a light bulb"""

    type = "LIGHT_BULB"

    def __init__(self, *args, **kwargs):
        super(LightBulbActuator, self).__init__(*args, **kwargs)
        self.light_on = False
        do = {
            "SET_LIGHT": self.set_light
        }


    def set_light(self, light_on=False):
        """Turn on the light bulb if the parameter light_on is True, otherwise turn light off"""
        self.light_on = bool(light_on)
        print "Turned %s the light." % ("on" if self.light_on else "off")
        # http://www.raspberrypi.org/forums/viewtopic.php?f=31&t=12530
        with open("/sys/class/leds/led0/brightness", "w") as fh:
            fh.write("%d\n" % self.light_on)
