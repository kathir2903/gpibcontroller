#!/usr/bin/python
"""
This module is just to test the
gpibinstruments module. 
Read the instrumentsinfo.conf file and
initialize the gpibinstruments with
gpib device information.
"""
import ConfigParser
from gpibinstruments import gpibinstruments
  
class instrumentstest(gpibinstruments):
    def __init__(self):
        self.out = self.getinstruments()
        gpibinstruments.__init__(self, self.out)
    def getinstruments(self):
        cfg = ConfigParser.SafeConfigParser()
        cfg.optionxform = str
        cfg.read('instrumentsinfo.conf')
        inst_info = {}
        for section in cfg.sections():
            if section == 'instrumentsinfo':
                for content in cfg.options(section):
                    inst_info[content] = cfg.get(section, content)
        return inst_info
    
if __name__ == "__main__":
    gpibobj = instrumentstest()
    if (len(gpibobj.stnInst_info) >0):
        eqpt_VOA_JDSU_GPIB2_5_1_1_1 = \
        gpibobj.stnInst_info['eqpt_VOA_JDSU_GPIB2_5_1_1_1']
        eqpt_WLM_HP86120C_GPIB2_9_0_0_0 = \
        gpibobj.stnInst_info['eqpt_WLM_HP86120C_GPIB2_9_0_0_0']
        eqpt_OPM_HP81635A_GPIB2_6_1_2_0 = \
        gpibobj.stnInst_info['eqpt_OPM_HP81635A_GPIB2_6_1_2_0']
    else:
        print "No GPIB instruments available"
    def read_power():
        pwr = eqpt_OPM_HP81635A_GPIB2_6_1_2_0._get_power()
        print "==================="
        print "Power read: %s", pwr
        print "==================="
    read_power()