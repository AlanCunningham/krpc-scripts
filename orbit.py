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
    start_time = datetime.now()
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

    # Circularise the orbit. The throttle is based on how close we are to the
    # apoapsis - i.e. increase the throttle the closer to the apoapsis we are,
    # decrease throttle the further away we are.
    while periapsis() < apoapsis() * 0.99:
        vessel.auto_pilot.target_pitch = 0
        if apoapsis() - periapsis() < 15000:
            # The orbit is almost circularised - we can afford to get closer
            # to the apoapsis when burning
            max_time_to_apoapsis = 3
            min_time_to_apoapsis = 0.1
        else:
            # Beginning of circularisation - may need to burn early depending
            # on the ship otherwise we'll overshoot the apoapsis.
            max_time_to_apoapsis = 30
            min_time_to_apoapsis = 15

        # Adjust the throttle based on how close to the apoapsis we are.
        adjusted_throttle = 1 - (time_to_apoapsis() - min_time_to_apoapsis) / (
            max_time_to_apoapsis - min_time_to_apoapsis
        )
        vessel.control.throttle = adjusted_throttle

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
