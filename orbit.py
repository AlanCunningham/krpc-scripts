import time
import krpc
import helpers


"""
This script takes a two-stage rocket and launches into an ~80km orbit. This
script currently assumes the following:
- The first stage uses solid fuel boosters
- The second stage has RCS available
- There's enough fuel available to get into orbit
- The stages are in the following order:
    - Solid boosters
    - Decouple & boost liquid fuel
    - Decouple if out of fuel
    - Activate parachute if less than a given altitude
"""


def launch(connection):
    # Setup heading, control and throttle
    vessel = connection.space_center.active_vessel
    vessel.auto_pilot.engage()
    vessel.auto_pilot.target_pitch = 90
    vessel.control.throttle = 1
    time.sleep(1)

    # Launch
    print("Launch")
    vessel.control.activate_next_stage()

    # Reduce thrusters and set pitch for orbit
    helpers.wait_for_altitude_more_than(connection, vessel, 3000)
    vessel.control.throttle = 0.7
    vessel.auto_pilot.target_pitch = 45

    # Decouple external fuel tanks when empty
    helpers.wait_for_fuel_less_than(connection, vessel, "SolidFuel", 0.1)
    vessel.control.activate_next_stage()

    # Wait for the apoapsis to reach above Kerbin's atmosphere
    helpers.wait_for_apoapsis_more_than(connection, vessel, 80000)
    vessel.auto_pilot.target_pitch = 0
    vessel.control.throttle = 0
    vessel.control.rcs = True
    time.sleep(1)

    # Keep boosting until the periapsis reaches the target altitude
    while vessel.orbit.periapsis_altitude < 80000:
        if vessel.orbit.time_to_apoapsis < 30:
            vessel.control.throttle = 1
        else:
            vessel.control.throttle = 0

    # Decouple when out of fuel
    helpers.wait_for_fuel_less_than(connection, vessel, "LiquidFuel", 0.1)
    vessel.auto_pilot.disengage()
    vessel.control.activate_next_stage()

    # Deploy the parachutes when below a certain altitude
    vessel.auto_pilot.sas = False
    deploy_at_altitude = 4000
    helpers.wait_for_altitude_less_than(connection, vessel, deploy_at_altitude)
    vessel.control.activate_next_stage()


if __name__ == "__main__":
    connection = krpc.connect(address="192.168.0.215")
    launch(connection)
