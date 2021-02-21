import krpc
import helpers
import orbit
import time
import sys
import math
from datetime import datetime


def orbit(connection, vessel, target_orbit_altitude):
    """
    Takes a given vessel currently in orbit with Kerbin and moves to orbit with
    the Mun.
    :params connection: A krpc connection
    :params vessel: A vessel object
    :parmas target_orbit_altitude: A double of the target orbit altitude
    """
    start_time = datetime.now()
    # Target the Mun - this will need to be set manually for now
    mun_target = connection.space_center.target_body
    if mun_target is None:
        print(
            "No target selected - make sure to select the Mun as a target before running this script"
        )
        sys.exit(1)

    # Creates a manuever node, initially at the current position. If it doesn't
    # encounter the Mun's sphere of influence, remove the node and plot another
    # one further on in the orbit. Repeat this process until the manuever
    # encounters the Mun.
    estimated_mun_encounter_delta_v = 860
    # Start with 60 seconds in the future, in case we can encounter the Mun
    # from the current orbit position.
    universal_time_increment_counter = 60
    time_to_soi_change = float("nan")
    while math.isnan(time_to_soi_change):
        # Create the manuever node
        node = vessel.control.add_node(
            connection.space_center.ut + universal_time_increment_counter,
            prograde=estimated_mun_encounter_delta_v,
        )
        # Returns float "nan" if there is no sphere of influence change
        time_to_soi_change = node.orbit.time_to_soi_change
        if math.isnan(time_to_soi_change):
            # Remove the node and set the increment counter further into the
            # future.
            node.remove()
            universal_time_increment_counter += 100

    # Wait until we're close to the manuever node
    print(f"Waiting for manuever ({int(node.time_to)} seconds)")
    helpers.wait_for_time_to_manuever_less_than(connection, vessel, node, 60)
    # Face the direction of the manuever node
    print("Preparing for manuever")
    vessel.auto_pilot.sas = True
    vessel.control.rcs = True
    vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.maneuver

    # Start burning in the direction of the manuever node
    helpers.wait_for_time_to_manuever_less_than(connection, vessel, node, 3)
    print("Burning...")
    while node.remaining_delta_v > 5:
        vessel.control.throttle = 1
    # Finished burn
    print("Manuever complete")
    vessel.control.throttle = 0
    vessel.control.rcs = False
    vessel.auto_pilot.sas = False

    # Wait until we're at the new orbit's periapsis, which should be at the Mun
    print(
        f"Waiting to arrive at {mun_target.name}'s periapsis ({int(vessel.orbit.time_to_periapsis)} seconds)"
    )
    helpers.wait_for_time_to_periapsis_less_than(connection, vessel, 60)
    print("Preparing for retro-burn")
    vessel.control.rcs = True
    vessel.auto_pilot.sas = True
    vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.retrograde

    helpers.wait_for_time_to_periapsis_less_than(connection, vessel, 30)
    print("Retro-burning...")
    vessel.control.throttle = 0.3
    # The apoapsis is initially reported as a minus number - probably because
    # we're still actually in orbit with Kerbin.  Keep boosting until the
    # apoapsis begings reporting as a positive number.
    helpers.wait_for_apoapsis_more_than(connection, vessel, 0)
    # Keep boosting until the periapsis reaches the target altitude
    while vessel.orbit.periapsis_altitude > target_orbit_altitude:
        vessel.control.throttle = 0.1
    print(f"At target apoapsis: {vessel.orbit.apoapsis_altitude}")
    vessel.control.rcs = False
    vessel.auto_pilot.sas = False
    vessel.control.throttle = 0

    # Even out the other side of the orbit
    print("Waiting for new periapsis to even out the orbit")
    helpers.wait_for_time_to_periapsis_less_than(connection, vessel, 60)
    print("Preparing for burn to even out the orbit")
    vessel.control.rcs = True
    vessel.auto_pilot.sas = True

    if vessel.orbit.apoapsis_altitude > target_orbit_altitude:
        vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.retrograde
    else:
        vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.prograde

    helpers.wait_for_time_to_periapsis_less_than(connection, vessel, 30)
    print("Burning...")
    if vessel.orbit.apoapsis_altitude > target_orbit_altitude:
        while vessel.orbit.apoapsis_altitude > target_orbit_altitude:
            vessel.control.throttle = 0.1
    else:
        while vessel.orbit.apoapsis_altitude < target_orbit_altitude:
            vessel.control.throttle = 0.1

    # In stable orbit
    vessel.control.rcs = False
    vessel.auto_pilot.sas = False
    vessel.control.throttle = 0
    vessel.auto_pilot.disengage()

    duration = datetime.now() - start_time
    print(f"{mun_target.name} orbit achieved in {duration}")
    print(
        f"Delta-v left: {helpers.get_estimated_delta_v(connection, vessel, sea_level_impulse=False)}"
    )


if __name__ == "__main__":
    server_ip_address = "192.168.0.15"
    connection = krpc.connect(address=server_ip_address)
    vessel = connection.space_center.active_vessel
    orbit(connection, vessel, 300000)
