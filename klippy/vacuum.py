import logging
from . import bus
from struct import unpack_from


REPORT_TIME = 2
ADC_REPORT_TIME = 0.5
ADC_SAMPLE_TIME = 0.001
ADC_SAMPLE_COUNT = 6
PIN_MIN_TIME = 0.100
RESEND_HOST_TIME = 0.300 + PIN_MIN_TIME
MAX_SCHEDULE_TIME = 5.0

class vacuum:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.name = config.get_name().split()[-1]
        self.printer.load_object(config, 'query_adc')
        self.motor_pin = config.get('vacuum_pump_pin')
        self.valve_pin = config.get('valve_pin')
        self.sensor_pin = config.get('sensor_pin')
        self.minimum_vacuum = config.getint('minimum_vac')
        self.maximum_vacuum = config.getint('maximum_vac')
        self.vacuum_level = -1
        self.is_system_activate = False
        self.is_system_running = False
        max_mcu_duration = config.getfloat('maximum_mcu_duration', 0.,
                                            minval=0.500,
                                            maxval=MAX_SCHEDULE_TIME)
        if max_mcu_duration:
            self.resend_interval = max_mcu_duration - RESEND_HOST_TIME
        self.last_value = config.getfloat(
            'value', 0., minval=0., maxval=1)
        self.shutdown_value = config.getfloat(
            'shutdown_value', 0., minval=0., maxval=1)

        ppins = self.printer.lookup_object('pins')
        #Motor_pin setup
        self.mcu_motor_pin= ppins.setup_pin('digital_out', self.motor_pin)
        self.mcu_motor_pin.setup_max_duration(max_mcu_duration)
        self.mcu_motor_pin.setup_start_value(self.last_value, self.shutdown_value)
        #valve_pin setup
        self.mcu_valve_pin= ppins.setup_pin('digital_out', self.valve_pin)
        self.mcu_valve_pin.setup_max_duration(max_mcu_duration)
        self.mcu_valve_pin.setup_start_value(self.last_value, self.shutdown_value)
        #sensor_pin setup
        self.mcu_adc = ppins.setup_pin('adc', self.sensor_pin)
        self.mcu_adc.setup_minmax(ADC_SAMPLE_TIME, ADC_SAMPLE_COUNT)
        self.mcu_adc.setup_adc_callback(ADC_REPORT_TIME, self.adc_callback)
        query_adc = self.printer.lookup_object('query_adc')
        query_adc.register_adc('adc_vacuum:' + self.sensor_pin.strip(), self.mcu_adc)
        #gcode setup
        self.cmd_ENABLE_VACUUM_help = "Enable Vacuum System"
        self.cmd_DISABLE_VACUUM_help = "Disable Vacuum System"
        self.cmd_EMPTY_VACUUM_TANK_help = "Repressure Tank"
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('ENABLE_VACUUM', self.cmd_ENABLE_VACUUM,
            desc=self.cmd_ENABLE_VACUUM_help)
        gcode.register_command('DISABLE_VACUUM', self.cmd_DISABLE_VACUUM,
            desc=self.cmd_DISABLE_VACUUM_help)
        gcode.register_command('EMPTY_VACUUM_TANK', self.cmd_EMPTY_VACUUM_TANK,
            desc=self.cmd_EMPTY_VACUUM_TANK_help)

    
    def cmd_ENABLE_VACUUM(self,gcmd):
        self.is_system_activate=True
        self.is_system_running=False
    def cmd_DISABLE_VACUUM(self,gcmd):
        self.is_system_activate=False
        self.is_system_running=False
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.register_lookahead_callback(
        lambda print_time: self._turn_off(print_time))
    def cmd_EMPTY_VACUUM_TANK(self,gcmd):
        self.is_system_activate = False
        self.is_system_running = False
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.register_lookahead_callback(
        lambda print_time: self._empty_tank(print_time))

    #Turn on sequence
    def _turn_on(self, print_time):
        self.mcu_motor_pin.set_digital(print_time, 1)
        self.mcu_valve_pin.set_digital(print_time + 1, 1) #add 1 second in between
    #Turn off sequence
    def _turn_off(self,print_time):
        self.mcu_valve_pin.set_digital(print_time, 0)
        #self.reactor.pause(self.reactor.monotonic() + 2) # Bad
        self.mcu_motor_pin.set_digital(print_time + 1, 0) # add 1 second in between
    #Repressure Tank sequence
    def _empty_tank(self,print_time):
        self.mcu_motor_pin.set_digital(print_time, 0)
        self.mcu_valve_pin.set_digital(print_time + 1, 1)


    def adc_callback(self, read_time, read_value):
        #adc = max(.00001, min(.99999, read_value))
        #self.vacuum_level = adc / (1.0 - adc)
        self.vacuum_level = ((((read_value - 0.1) * (30 - 0)) / (0.99999 - 0.1)) +0)
        vacuum_level_abs = abs(self.vacuum_level)
        if self.is_system_activate:
            if(vacuum_level_abs <= self.minimum_vacuum):
                if not self.is_system_running:
                    toolhead = self.printer.lookup_object('toolhead')
                    toolhead.register_lookahead_callback(
                    lambda print_time: self._turn_on(print_time))
                    #logging.info("Vacuum is LOW, system POWER On")
                    self.is_system_running=True   
            else:
                if (vacuum_level_abs >= self.maximum_vacuum):
                    if self.is_system_running:
                        toolhead = self.printer.lookup_object('toolhead')
                        toolhead.register_lookahead_callback(
                        lambda print_time: self._turn_off(print_time))
                        #logging.info("Vacuum is High, system POWER Off")
                        self.is_system_running=False
    
    def get_status(self, eventtime):
        data = {'vacuum': self.vacuum_level}
        return data 

def load_config_prefix(config):
    return vacuum(config)
        
