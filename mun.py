import krpc
import settings
import time
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
    ut = connection.add_stream(getattr, connection.space_center, "ut")

    # Target the Mun
    connection.space_center.target_body = connection.space_center.bodies["Mun"]

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

    # Face the direction of the manuever mun_node
    vessel.auto_pilot.disengage()
    vessel.auto_pilot.sas = True
    vessel.control.rcs = True
    # There seems to be a race condition of some sort where SAS pilot mode
    # gets enabled, but doesn't switch to maneuver mode. Workaround here
    # is just to keep trying until we've switched to maneuever mode.
    while vessel.auto_pilot.sas_mode != vessel.auto_pilot.sas_mode.maneuver:
        time.sleep(1)
        vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.maneuver

    # Warp to manuever
    time_to_mun_manuever = connection.add_stream(getattr, mun_node, "time_to")
    print(f"Manuever in {time_to_mun_manuever()} seconds")
    lead_time = 45
    connection.space_center.warp_to((ut() + time_to_mun_manuever()) - lead_time)

    while time_to_mun_manuever() >= 30:
        pass

    # Start burning in the direction of the manuever mun_node
    print("Starting burn for Mun")
    while mun_node.remaining_delta_v > 5:
        vessel.control.throttle = 1

    # Finished burn
    print("Manuever complete")
    vessel.control.throttle = 0
    mun_node.remove()
    # vessel.control.rcs = False
    # vessel.auto_pilot.sas = False

    # Warp to the Mun's periapsis
    # First warp to the SOI change
    time_to_mun_soi_change = connection.add_stream(
        getattr, vessel.orbit, "time_to_soi_change"
    )
    buffer_time = 10
    connection.space_center.warp_to((ut() + time_to_mun_soi_change()) + buffer_time)

    # Face retrograde
    while vessel.auto_pilot.sas_mode != vessel.auto_pilot.sas_mode.retrograde:
        time.sleep(1)
        vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.retrograde

    # Now warp to the Mun's periapsis
    time_to_periapsis = connection.add_stream(
        getattr, vessel.orbit, "time_to_periapsis"
    )
    lead_time = 75
    connection.space_center.warp_to((ut() + time_to_periapsis()) - lead_time)

    while time_to_periapsis() > 60:
        pass

    # Circularise the orbit by burning retrograde.
    # The apoapsis readings start off as a minus value, and then switch to a
    # positive, so we do two checks here. First check for when the apoapsis
    # switches, and then compare against the higher value.
    periapsis = connection.add_stream(getattr, vessel.orbit, "periapsis_altitude")
    apoapsis = connection.add_stream(getattr, vessel.orbit, "apoapsis_altitude")

    while periapsis() > apoapsis() * 0.99:
        vessel.control.throttle = 1

    # Apoapsis reading has switched
    # The throttle is based on how close we are to the periapsis - i.e. increase
    # the throttle the closer to the periapsis we are, decrease throttle the
    # further away we are.
    vessel.control.throttle = 0
    while periapsis() < apoapsis() * 0.99:
        max_time_to_periapsis = 30
        min_time_to_periapsis = 20

        # Adjust the throttle based on how close to the periapsis we are.
        adjusted_throttle = 1 - (time_to_periapsis() - min_time_to_periapsis) / (
            max_time_to_periapsis - min_time_to_periapsis
        )
        vessel.control.throttle = adjusted_throttle

    # In stable orbit
    vessel.control.rcs = False
    vessel.auto_pilot.sas = False
    vessel.control.throttle = 0
    vessel.auto_pilot.disengage()

    duration = datetime.now() - start_time
    print(f"Orbit achieved in {duration}")


if __name__ == "__main__":
    connection = krpc.connect(address=settings.krpc_ip_address)
    vessel = connection.space_center.active_vessel
    kerbin_to_mun(connection, vessel, 300000)
