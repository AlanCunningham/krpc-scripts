import krpc
import helpers
import orbit
import time
import sys
import signal
import math
from datetime import datetime


def kerbin_to_mun(connection, vessel, target_orbit_altitude):
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
    # encounter the Mun's sphere of influence, move the node further on in the
    # orbit. Repeat this process until the manuever encounters the Mun.
    # For estimated delta-v, see:
    # https://wiki.kerbalspaceprogram.com/wiki/Cheat_sheet#Maps
    estimated_mun_encounter_delta_v = 860
    mun_node = vessel.control.add_node(
        connection.space_center.ut,
        prograde=estimated_mun_encounter_delta_v,
    )
    universal_time_increment_counter = 100
    time_to_soi_change = float("nan")
    while math.isnan(time_to_soi_change):
        # Returns float "nan" if there is no sphere of influence change
        time_to_soi_change = mun_node.orbit.time_to_soi_change
        if math.isnan(time_to_soi_change):
            # Increment counter further into the future.
            mun_node.ut += universal_time_increment_counter

    # Wait until we're close to the manuever mun_node
    helpers.wait_for_time_to_manuever_less_than(connection, vessel, mun_node, 60)
    # Face the direction of the manuever mun_node
    print("Preparing for manuever")
    vessel.auto_pilot.sas = True
    vessel.control.rcs = True
    vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.maneuver

    # Start burning in the direction of the manuever mun_node
    helpers.wait_for_time_to_manuever_less_than(connection, vessel, mun_node, 3)
    print("Burning...")
    while mun_node.remaining_delta_v > 5:
        vessel.control.throttle = 1
    # Finished burn
    print("Manuever complete")
    vessel.control.throttle = 0
    vessel.control.rcs = False
    vessel.auto_pilot.sas = False

    # We want to set the next maneuver after the sphere of influence change.
    # Add a buffer to the sphere of influence change time.
    buffer_seconds = 20
    soi_change_time = connection.space_center.ut + vessel.orbit.time_to_soi_change
    # There appears to be an issue when creating a new maneuver node, where
    # the helpers.wait_for_time_maneuver_less_than function doesn't count
    # the time_to correctly.  For now, we move the existing mun_node node object.
    mun_node.ut = soi_change_time + buffer_seconds
    mun_node.prograde = 0
    helpers.wait_for_time_to_manuever_less_than(connection, vessel, mun_node, 10)
    # Even out the orbit
    helpers.even_orbit(connection, vessel, mun_node, next_orbit=False)

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
    kerbin_to_mun(connection, vessel, 300000)
