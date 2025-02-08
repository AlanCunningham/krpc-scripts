import time
import math
from datetime import datetime, timedelta
import krpc
import settings


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
    # Set up telemetry streams
    altitude = connection.add_stream(getattr, vessel.flight(), "mean_altitude")
    apoapsis = connection.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
    periapsis = connection.add_stream(getattr, vessel.orbit, "periapsis_altitude")
    time_to_apoapsis = connection.add_stream(getattr, vessel.orbit, "time_to_apoapsis")
    launch_stage = vessel.resources_in_decouple_stage(
        stage=vessel.control.current_stage - 2, cumulative=False
    )
    launch_stage_fuel_amount = connection.add_stream(
        launch_stage.amount, name="SolidFuel"
    )

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

    solid_fuel_separated = False
    running = True
    while running:
        # Decouple external fuel tanks when empty
        if not solid_fuel_separated:
            if launch_stage_fuel_amount() < 0.1:
                vessel.control.activate_next_stage()
                solid_fuel_separated = True
                print("Separating solid fuel boosters")

        # Reduce thrusters and set pitch for orbit
        if altitude() > 3000 and apoapsis() < target_altitude:
            vessel.control.throttle = 0.7
            vessel.auto_pilot.target_pitch = 45

        # Approaching the target apoapsis altitude
        if apoapsis() > target_altitude * 0.9:
            print(f"Approaching target apoapsis: {apoapsis()} / {target_altitude}")
            # Get rid of the solid boosters if they're still in use, as we're
            # approaching the apoapsis
            if not solid_fuel_separated:
                vessel.control.activate_next_stage()
                solid_fuel_separated = True
                print("Separating solid fuel boosters early")
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
    while periapsis() < apoapsis() * 0.99:
        max_time_to_apoapsis = 20
        min_time_to_apoapsis = 10

        # The throttle is based on how close we are to the apoapsis - i.e.
        # increase the throttle the closer to the apoapsis we are, decrease
        # throttle the further away we are.
        adjusted_throttle = 1 - (time_to_apoapsis() - min_time_to_apoapsis) / (
            max_time_to_apoapsis - min_time_to_apoapsis
        )
        vessel.control.throttle = adjusted_throttle

        # Adjust pitch based on how close we are to the apoapsis - i.e., pitch
        # up if we're close to the apoapsis, and pitch down the further
        # away we are.
        if time_to_apoapsis() <= max_time_to_apoapsis:
            adjusted_pitch = -10 + (1 - (time_to_apoapsis() - min_time_to_apoapsis) / (
                max_time_to_apoapsis - min_time_to_apoapsis
            )) * 20

            vessel.auto_pilot.target_pitch = adjusted_pitch

    # In stable orbit
    vessel.control.throttle = 0
    vessel.control.rcs = False
    vessel.auto_pilot.disengage()
    launch_duration = datetime.now() - start_time
    print(f"Stable orbit achieved in {launch_duration}")


if __name__ == "__main__":
    connection = krpc.connect(address=settings.krpc_ip_address)
    vessel = connection.space_center.active_vessel
    launch(connection, vessel, HEADING_EAST, 75000)
