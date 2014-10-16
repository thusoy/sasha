import random
import time
import json

class Actuator(object):

    do = {}

    def describe(self):
        return {
            "id": self.id,
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

class TemperatureSensor(Sensor):
    """Track current temperature in Celcius"""
    def __init__(self, interface_id):
        self.type = "TEMPERATURE"
        self.id = interface_id

    def read(self):
        """Report the current temperature in Celcius"""
        return random.random()*60 - 20 # report temperatures in range -20, 40


class TermostatActuator(Actuator):
    """Set target temperature on heating device"""

    def __init__(self, interface_id):
        self.type = "ACTUATOR"
        self.id = interface_id
        self.value = 20
        self.do = {
            "SET_TEMPERATURE": self.set_temp
        }

    def set_temp(self, temp=0):
        """Set termostat value to given parameter 'temp', where 'temp' is in range(14, 24)"""

        if temp and (14 <= temp <= 24):
            print "temperature set to %d" % x
        else:
            raise ArgumentError("Invalid temperature")




def test_interfaces():
    iflist = InterfaceList()
    print json.dumps(iflist.describe(), indent=2);

if __name__ == '__main__':
    test_interfaces()
