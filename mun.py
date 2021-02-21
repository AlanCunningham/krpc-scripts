import krpc
import helpers
import orbit
import time
import sys
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

    # Find out if we're closer to the ascending node or the descending node
    ascending_node_time = vessel.orbit.ut_at_true_anomaly(
        vessel.orbit.true_anomaly_at_an(mun_target.orbit)
    )
    descending_node_time = vessel.orbit.ut_at_true_anomaly(
        vessel.orbit.true_anomaly_at_dn(mun_target.orbit)
    )
    if ascending_node_time < descending_node_time:
        node_ut_time = ascending_node_time
    else:
        node_ut_time = descending_node_time
    estimated_mun_encounter_delta_v = 860

    # Create the manuever node
    # TODO: This only creates manuever nodes on either the ascending or descending
    # node, regardless of where the Mun is.  We should adjust where the node
    # is placed dependng on the position of the Mun.
    node = vessel.control.add_node(
        node_ut_time, prograde=estimated_mun_encounter_delta_v
    )

    # Wait until we're close to the manuever node
    print(f"Waiting for manuever ({int(node.time_to)} seconds)")
    helpers.wait_for_time_to_manuever_less_than(connection, vessel, node, 20)
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

    helpers.wait_for_time_to_periapsis_less_than(connection, vessel, 45)
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
    helpers.wait_for_time_to_periapsis_less_than(connection, vessel, 30)
    print("Preparing for burn to even out the orbit")
    vessel.control.rcs = True
    vessel.auto_pilot.sas = True

    if vessel.orbit.apoapsis_altitude > target_orbit_altitude:
        vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.retrograde
    else:
        vessel.auto_pilot.sas_mode = vessel.auto_pilot.sas_mode.prograde

    helpers.wait_for_time_to_periapsis_less_than(connection, vessel, 3)
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
