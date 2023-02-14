import inspect

class TrackedObject:

    def __init__(self, init_value):
        self._value = init_value
        self._value_changed = True

    @property
    def value(self):
        # getting object's value resets the tracker
        #print("getter caller %s() " % (inspect.currentframe().f_back.f_code.co_name), end='')
        #print(self._value, self._value_changed, end='')
        self._value_changed = False
        #print("->", self._value, self._value_changed)
        return self._value

    @value.setter
    def value(self, new_value):
        #print("setter caller %s() " % (inspect.currentframe().f_back.f_code.co_name), end='')
        #print(self._value, self._value_changed, end='')
        if self._value != new_value:
            self._value = new_value
            self._value_changed = True
        #print("->", self._value, self._value_changed)
        pass

    @property
    def value_changed(self):
        #print("tracker caller %s() " % (inspect.currentframe().f_back.f_code.co_name), end='')
        #print(self._value, self._value_changed)
        return self._value_changed



