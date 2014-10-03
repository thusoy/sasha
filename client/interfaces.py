import random
import time
import json

class InterfaceList(object):
    """List of device's interfaces"""
    def __init__(self):
        self.interfaces = [
            TemperatureSensor("if0"),
            TermostatActuator("ac0"),
        ]
    def describe(self):
        return [iface.describe() for iface in self.interfaces]


class TemperatureSensor(object):
    """Track current temperature in Celcius"""
    def __init__(self, interface_id):
        self.type = "TEMPERATURE"
        self.id = interface_id

    def read(self):
        """Report the current temperature in Celcius"""
        return random.random()*60 - 20; # report temperatures in range -20, 40

    def describe(self):
        return {
            "id": self.id,
            "type": self.type,
            "description": self.__doc__,
        }
        print self.__doc__

class TermostatActuator(object):
    """Set target temperature on heating device"""

    def __init__(self, interface_id):
        self.type = "ACTUATOR"
        self.id = interface_id
        self.value = 20
        self.do = {
            "SET_TEMPERATURE": self.set_temp
        }


    def actuate(self, action, args):
        try:
            self.do[action](args)
        except KeyError:
            print "unknown action"

    def set_temp(self, arg):
        """Set termostat value to given parameter 'arg', where 'arg' is in range(14, 24)"""
        x = int(arg)
        if (14 >= x <= 24):
            print "temperature set to %d" % x

    def describe(self):
        return {
            "id": self.id,
            "type": self.type,
            "description": self.__doc__,
            "actions": [{"name": key, "description": self.do[key].__doc__} for key in self.do]
        }


def test_interfaces():
    iflist = InterfaceList()
    print json.dumps(iflist.describe(), indent=2);

if __name__ == '__main__':
    test_interfaces()
