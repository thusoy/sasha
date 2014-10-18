import inspect

class Actuator(object):

    type = 'NULL-ACTUATOR'
    actions = {}

    def __init__(self, interface_id):
        self.interface_id = interface_id
        self._actions = {}
        for action_name, method_name in self.actions.items():
            method = getattr(self, method_name)
            assert method is not None, "No method named %s found" % method_name
            self._actions[action_name] = method


    def describe(self):
        actions = []
        for action_name, method in self._actions.items():
            argspec = inspect.getargspec(method)
            actions.append({
                'name': action_name,
                'description': method.__doc__,
                'params': argspec.args[1:],
            })
        return {
            "id": self.interface_id,
            "type": self.type,
            "description": self.__doc__,
            "actions": actions,
        }

    def actuate(self, action, *args, **kwargs):
        try:
            self._actions[action](*args, **kwargs)
        except KeyError:
            print "unknown action"


class Sensor(object):

    def describe(self):
        return {
            "id": self.id,
            "type": self.type,
            "description": self.__doc__,
        }


class LightBulbActuator(Actuator):
    """A simple on/off light bulb."""

    type = "LIGHT_BULB"

    actions = {
        'SET-LIGHT': 'set_light',
    }

    def __init__(self, *args, **kwargs):
        super(LightBulbActuator, self).__init__(*args, **kwargs)
        self.light_on = False


    def set_light(self, light_on=False):
        """Turn on the light bulb if the parameter light_on is True, otherwise turn light off"""
        self.light_on = bool(light_on)
        print "Turned %s the light." % ("on" if self.light_on else "off")
        # http://www.raspberrypi.org/forums/viewtopic.php?f=31&t=12530
        with open("/sys/class/leds/led0/brightness", "w") as fh:
            fh.write("%d\n" % self.light_on)
