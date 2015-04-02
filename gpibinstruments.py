#!/usr/bin/python

import sys, time, math
from collections import namedtuple
import pyvisa.visa as visa
import pyvisa.vpp43 as vpp43
import pyvisa.visa_exceptions as visa_exceptions

ON = "on"
OFF = "off"
params = namedtuple('params', ['value', 'units'])
class InstrumentError(ValueError):
    pass
class gpibinstruments:

    def __init__(self, station_info):
        eqpt = []
        self.stnInst_info = {}
        self.station_info = station_info
        for key in self.station_info.keys():
            if key.startswith('eqpt'):
                eqpt.append(key)
                print "Eqpt List: %s" %eqpt
                self.visaCred = self.station_info[key].split('_')
                print "Visa Credentials %s" %self.visaCred
                addr = "%s::%s" % (self.visaCred[1], self.visaCred[2])
                self.instr = visa.instrument(addr)
                if key.endswith('VOA') and self.visaCred[0] == 'JDSU':
                    self.instrInst = OpticalAttenuator_JDSU(self.instr, self.visaCred)
                elif key.endswith('WLM') and self.visaCred[0] == 'HP86120C':
                    self.instrInst = WLMeter_HP86120C(self.instr)
                elif key.endswith('OPM') and self.visaCred[0] == 'HP81635A':
                    self.instrInst = OpticalPowerMeter_HP81635A(self.instr, self.visaCred)
                else:
                    pass
                res = key + "_" + self.station_info[key]
                self.stnInst_info[res] = self.instrInst


class Boolean(object):
    def __init__(self, data):
        try:
            self.value = bool(int(data))
        except ValueError:
            if type(data) is str:
                data = data.lower()
            if data in ("on", "yes", "true", "enable", "ok"):
                self.value = True
            elif data in ("off", "no", "false", "disable", "notok"):
                self.value = False
            else:
                raise ValueError, "invalid value for Boolean: %s" % (data,)
    def __str__(self):
        def IF(val, trueval, falseval):
            if val: return trueval
            else: return falseval
        return IF(self.value, "ON", "OFF")
    def __repr__(self):
        return "Boolean(%r)" % (self.value,)
    def __nonzero__(self):
        return self.value
    def __int__(self):
        return int(self.value)


class OpticalAttenuator_JDSU(object):
    "A generic optical attenuator"

    def __init__(self, instr, visaCred):
        self.instrVisaCred = visaCred
        self.instr = instr
        self.chassis_addr = self.instrVisaCred[5]
        self.slot_addr = self.instrVisaCred[3]
        self.device_addr = self.instrVisaCred[4]

    def _get_attenuation(self):
        addr_params = "%s,%s,%s" % (self.chassis_addr, self.slot_addr, self.device_addr)
        cmd = ":OUTP:ATT? %s" % (addr_params)
        raw = self.instr.ask("%s" % cmd)
        return raw

    def _set_attenuation(self, atten):
        addr_params = "%s,%s,%s" % (self.chassis_addr, self.slot_addr, self.device_addr)
        cmd = ":OUTP:ATT %s,%.2f" % (addr_params, atten)
        print "att cmd: %s" % cmd
        self.instr.write("%s" % (cmd, ),)
        time.sleep(1) # JSDU voa need a time delay after set_attenuation

    def _no_attenuation(self):
        addr_params = "%s,%s,%s" % (self.chassis_addr, self.slot_addr, self.device_addr)
        cmd = ":OUTP:ATT %s,%.2f" % (addr_params, 0.0)
        self.instr.write(cmd, wait=True)
    attenuation = property(_get_attenuation, _set_attenuation, _no_attenuation, "attenuation factor (dB)")

    def _get_wavelength(self):
        addr_params = "%s,%s,%s" % (self.chassis_addr, self.slot_addr, self.device_addr)
        raw = self.instr.ask(":OUTP:WAV? %s" % addr_params) # in meters
        return raw

    def _set_wavelength(self, wl):
        addr_params = "%s,%s,%s" % (self.chassis_addr, self.slot_addr, self.device_addr)
        wl = params(wl, "nm")
        cmd = ":OUTP:WAV %s,%s" % (addr_params,wl._value)
        self.instr.write("%s" % (cmd,), wait=True)
    wavelength = property(_get_wavelength, _set_wavelength, None, "wavelengh in nM")

    def _get_output(self):
        addr_params = "%s,%s,%s" % (self.chassis_addr, self.slot_addr, self.device_addr)
        cmd = ":OUTP:BBLock? %s" % addr_params
        return Boolean(self.instr.ask(cmd))

    def _set_output(self, state):
        addr_params = "%s,%s,%s" % (self.chassis_addr, self.slot_addr, self.device_addr)
        if state=='ON':
            cmd = ":OUTP:BBLock %s,0" % (addr_params)
        else:
            cmd = ":OUTP:BBLock %s,1" % (addr_params)
        self.instr.wrbite(cmd, wait=True)
    output = property(_get_output, _set_output, None, "state of output shutter")
    state = output # alias

    def on(self):
        self._set_output(ON)

    def off(self):
        self._set_output(OFF)

#Agilent===========
class OpticalPowerMeter_HP81635A(object):
    """HP81635A dual power meter for HP8163A chassis"""
    def __init__(self, instr, visaCred):
        self.instrVisaCred = visaCred
        self.instr = instr
        self.chassis_addr = self.instrVisaCred[5]
        self.slot = int(self.instrVisaCred[3])
        self.port = int(self.instrVisaCred[4])
        self._currentunit = self._get_unit()
        if self._currentunit is None:
            raise InstrumentError, "could not initialize HP81635APort"

    def _set_unit(self, unit):
        assert unit in ("dBm", "DBM", "Watts", "W")
        self.instr.write(':SENSE%d:CHAN%d:POW:UNIT %s' % (self.slot, self.port, unit) )
        self._currentunit = self._get_unit()
    def _get_unit(self):
        val = int(self.instr.ask(':SENSE%d:CHAN%d:POW:UNIT?' % (self.slot, self.port) ))
        if val == 0:
            return "dBm"
        elif val == 1:
            return "W"
    unit = property(_get_unit, _set_unit, None, "Measurement unit: dBm or Watts")

    def _set_wavelength(self, wl):
        wl = params(wl, "nm")
        self.instr.write(':SENSE%d:CHAN%d:POW:WAV %sM' % (self.slot,self.port, wl._value) )
    def _get_wavelength(self):
        val = self.instr.ask(':SENSE%d:CHAN%d:POW:WAV?' % (self.slot,self.port) )
        return val
    wavelength = property(_get_wavelength, _set_wavelength, None, "Wavelength in M")

    def _set_averaging(self, tm):
        tm = params(tm, "s")
        if self.is_master():
            self.instr.write(':SENSE%d:CHAN%d:POW:ATIM %sS' % (self.slot, self.port, tm._value))
        else:
            raise InstrumentError, "invalid operation on non-master port"
    def _get_averaging(self):
        val = self.instr.ask(':SENSE%d:CHAN%d:POW:ATIM?' % (self.slot,self.port))
        return val
    averaging_time = property(_get_averaging, _set_averaging, None, "Averaging time in S")

    def _set_continuous(self, state):
        if self.is_master():
            state = Boolean(state)
            self.instr.write(':INIT%d:CHAN%d:CONT %s' % (self.slot,self.port,state) )
        else:
            raise InstrumentError, "invalid operation on non-master port"
    def _get_continuous(self):
        return Boolean(self.instr.ask(':INIT%d:CHAN%d:CONT?' % (self.slot,self.port)))
    continuous = property(_get_continuous, _set_continuous, None, "continuous measurement mode?")

    def _get_power(self):
        val = self.instr.ask(':FETCH%d:CHAN%d:SCAL:POW?' % (self.slot,self.port) )
        return val, self._currentunit
    power = property(_get_power, None, None, "Power in current units.")


class WLMeter_HP86120C(object):
    "A HEWLETT-PACKARD 86120C Multi-Wavelength Meter"
    def __init__(self, instr):
        self.instr = instr

    def _get_array(self):
        self.instr.write(":INIT:CONT OFF")
        self.instr.write(":CONF:ARR:POW MAX")
        self.instr.write(":INIT:IMM")
        levels = self.instr.ask(":FETC:ARR:POW?")
        wavelengths = self.instr.ask(":FETC:ARR:POW:WAV?")
        # convert to lists
        levels = filter(None, levels.split(","))
        wavelengths = filter(None, wavelengths.split(","))
        # sanity checks...
        len_levels = int(levels[0]) ; len_wavelengths = int(wavelengths[0])
        assert len_levels == len_wavelengths
        levels.pop(0) ; wavelengths.pop(0)
        assert len_levels == len(levels) ; assert len_wavelengths == len(wavelengths)
        if len_levels > 0:
            return map(float, wavelengths), "m",  map(float, levels), "dBm", "Wavemeter Readings"
        else:
            return None
    def _get_wavelength(self):
        wavelengths = self.instr.ask(":FETC:ARR:POW:WAV?")
        wavelengths = filter(None, wavelengths.split(","))
        return float(wavelengths[1])*1000000000
    def _get_power(self):
        levels = self.instr.ask(":FETC:ARR:POW?")
        return filter(None, levels.split(","))
