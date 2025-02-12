import time
from datetime import datetime, timedelta
import krpc
import helpers
import settings



"""
This script takes a rocket and launches it into orbit from Kerbin.
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
    # Set up telemetry streams
    altitude = connection.add_stream(getattr, vessel.flight(), "mean_altitude")
    apoapsis = connection.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
    periapsis = connection.add_stream(getattr, vessel.orbit, "periapsis_altitude")
    time_to_apoapsis = connection.add_stream(getattr, vessel.orbit, "time_to_apoapsis")

    # Setup heading, control and throttle
    vessel.auto_pilot.engage()
    vessel.auto_pilot.target_pitch_and_heading(90, heading)
    vessel.control.throttle = 1

    # Countdown...
    print("3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print("Launch!")
    vessel.control.activate_next_stage()
    start_time = datetime.now()

    # When fuel is empty in the current stage, automatically move to the next
    # one
    helpers.enable_auto_stage(connection, vessel)

    running = True
    while running:
        # Start gravity turn - we start pointing up (90 degrees) and gradually
        # pitch until we're at 45 degrees.
        min_altitude = 0
        max_altitude = 10000
        start_pitch = 90
        end_pitch = 45
        if apoapsis() < target_altitude and int(vessel.auto_pilot.target_pitch) != end_pitch:
            adjusted_pitch = start_pitch - ((altitude() - min_altitude) / (
                max_altitude - min_altitude
            )) * end_pitch

            vessel.auto_pilot.target_pitch = adjusted_pitch

        # Approaching the target apoapsis altitude
        if apoapsis() > target_altitude * 0.9:
            print(f"Approaching target apoapsis: {apoapsis()} / {target_altitude}")
            # Get rid of the solid boosters if they're still in use, as we're
            # approaching the apoapsis
            fuel_in_current_stage = vessel.resources_in_decouple_stage(
                stage=vessel.control.current_stage - 1, cumulative=False
            )
            if "SolidFuel" in fuel_in_current_stage.names:
                vessel.control.activate_next_stage()
                solid_fuel_separated = True
                print("Near target apoapsis - separating solid fuel boosters early")
            break

    # Reduce throttle and boost until we reach the target orbit altitude
    vessel.control.throttle = 0.25
    while apoapsis() < target_altitude:
        pass

    # Reached target apoapsis - shut down engines
    print(f"Reached target apoapsis: {apoapsis()} / {target_altitude}")
    vessel.control.throttle = 0
    vessel.auto_pilot.target_pitch = 0

    # Circularise the orbit.
    starting_periapsis = periapsis()
    max_apoapsis = apoapsis() * 0.7
    while periapsis() < apoapsis() * 0.99:
        max_time_to_apoapsis = 25
        min_time_to_apoapsis = 15

        if time_to_apoapsis() <= max_time_to_apoapsis:
            # Adjust the throttle - start at full throttle and gradually reduce
            # as the periapsis matches the apoapsis.
            adjusted_throttle = 1 - (periapsis() - starting_periapsis) / (
                max_apoapsis - starting_periapsis
            )
            if adjusted_throttle > 0.1:
                vessel.control.throttle = adjusted_throttle


            # Adjust pitch based on how close we are to the apoapsis - i.e., pitch
            # up by 10 degrees if we're close to the apoapsis, and pitch down by 10
            # degrees the further away we are.
            # Pitching up will "move" the apoapsis further away, while pitching down
            # will "move" the apoapsis closer to us.
            adjusted_pitch = -10 + (1 - (time_to_apoapsis() - min_time_to_apoapsis) / (
                max_time_to_apoapsis - min_time_to_apoapsis
            )) * 20

            vessel.auto_pilot.target_pitch = adjusted_pitch

    # In stable orbit
    vessel.control.throttle = 0
    vessel.control.rcs = False
    vessel.auto_pilot.disengage()
    helpers.disable_auto_stage()
    launch_duration = datetime.now() - start_time
    print(f"Stable orbit achieved in {launch_duration}")


if __name__ == "__main__":
    connection = krpc.connect(address=settings.krpc_ip_address)
    vessel = connection.space_center.active_vessel
    launch(connection, vessel, HEADING_EAST, 75000)
