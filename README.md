# Vacuum Bed For Klipper
This is designed to work with a vacuum bed, vacuum pump, vacuum transmitter and vacuum tank(not a must but nice to have). Still in development but usable.
### TODO
* Add mode change function to handle different sensors and vacuum ranges. So far this is hard coded for generic vacuum sensor with 1-5V output, 0 to - 14.7psig range.
* Provide different units
* Run long test runs, possible timing bug, but can't confirm
* Improve gcode commands, come up with better control system
# Configure  "printer.cfg"
add the module name
``` bash 
[vacuum tank]
sensor_pin:mega:PK7 #analog pin for sensor read
vacuum_pump_pin:mega:PF3 #digital pin for vacuum pump relay
valve_pin:pico2:gpio7 #digital pin for solenoid valve
minimum_vac:13 #vacuum pump starts if vacuum level is equal to or below min. desired vacuum level
maximum_vac:27 #vacuum pump stops when it reaches maximum desired vacuum level
```
# Built-in Gcode commands
Starts the vacuum system. Maintains vacuum level based on desired levels.
``` bash 
    ENABLE_VAC
```

Stops the vacuum system. If tank is used or hose line has vacuum in it, then this command won't empty that line.
``` bash 
    DISABLE_VAC
```

Turn ons the solenoid without turning on the pump. Fills the system with air.
``` bash 
    EMPTY_TANK
```
# Configure macro for reading vacuum level
``` bash 
[gcode_macro QUERY_VACUUM]
gcode:
    {% set sensor = printer["vacuum tank"] %}
    {action_respond_info(
        "vacuum: %.2f inHg\n" % (
            sensor.vacuum))}```
```


