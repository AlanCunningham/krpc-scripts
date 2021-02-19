import time
from datetime import datetime, timedelta
import krpc
import helpers


"""
This script takes a two-stage rocket and launches it into orbit. The following
assumptions are made:
- The first stage uses solid fuel boosters
- The second stage has RCS available
- There's enough fuel available to get into orbit
- The stages are in the following order:
    - Solid boosters
    - Decouple & boost liquid fuel
"""

HEADING_NORTH = 0
HEADING_EAST = 90
HEADING_SOUTH = 180
HEADING_WEST = 270


def launch(connection, vessel, heading, target_altitude):
    """
    Launch a given vessel into orbit at a given target altitude.
    :params connection: A krpc connection
    :params vessel: A vessel object
    :params heading: The heading of the orbit
    :params target_altitude: The target apoapsis and periapsis altitude in meters
    """
    # Setup heading, control and throttle
    start_time = datetime.now()
    vessel.auto_pilot.engage()
    vessel.auto_pilot.target_pitch_and_heading(90, heading)
    vessel.control.throttle = 1
    print(f"Delta-v: {helpers.get_estimated_delta_v(connection, vessel)}")

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

    # Keep boosting until we reach the target orbit altitude
    helpers.wait_for_apoapsis_more_than(connection, vessel, target_altitude)
    vessel.auto_pilot.target_pitch = 0
    vessel.control.throttle = 0
    vessel.control.rcs = True
    time.sleep(1)

    # Keep boosting until the periapsis reaches the target altitude
    while vessel.orbit.periapsis_altitude < target_altitude:
        if vessel.orbit.time_to_apoapsis < 30:
            vessel.control.throttle = 1
        else:
            vessel.control.throttle = 0
    print(f"At target periapsis: {vessel.orbit.periapsis_altitude}")

    # In stable orbit
    vessel.control.rcs = False
    vessel.auto_pilot.disengage()
    launch_duration = datetime.now() - start_time
    print(f"Stable orbit achieved in {launch_duration}")
    print(f"Delta-v left: {helpers.get_estimated_delta_v(connection, vessel, sea_level_impulse=False)}")


if __name__ == "__main__":
    server_ip_address = "replace_with_your_server_ip_address"
    connection = krpc.connect(address=server_ip_address)
    vessel = connection.space_center.active_vessel
    launch(connection, vessel, HEADING_EAST, 80000)
