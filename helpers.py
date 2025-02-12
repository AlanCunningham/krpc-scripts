import math
import threading


auto_stage_enabled = False


def get_thrust_to_weight_ratio(conn, vessel):
    """
    Gets the thrust-to-weight ratio of a given vessel.
    Thrust-to-weight = Thrust / (mass * gravity) > 1
    :params conn: A krpc connection
    :params vessel: Vessel object
    :return: Thrust to weight ratio as a double
    """
    thrust = vessel.available_thrust
    mass = vessel.mass
    gravity = conn.space_center.bodies["Kerbin"].surface_gravity
    ratio = thrust / (mass * gravity)
    print(f"Thrust: {thrust} | Mass: {mass} | Gravity: {gravity} | Ratio: {ratio}")
    return ratio


def get_estimated_delta_v(conn, vessel, sea_level_impulse=True):
    """
    Gets the estimated delta-v of a given vessel. This is a rough approxmation
    and may be less accurate the larger the vessel.
    https://wiki.kerbalspaceprogram.com/wiki/Cheat_sheet
    Δv = Isp * g0   * ln(total_mass/dry_mass)
    For example:
       = 400 * 9.81 * ln(3.72/1.72)
       = 400 * 9.81 * ln(2.16)
       = 400 * 9.81 * 0.771 = 3026.97 m/s
    :params conn: A krpc connection
    :params vessel: Vessel object
    :params sea_level_impulse: Whether to use specific impulse at Kerbin sea-level
    or specific impulse in a vacuum.
    :returns: A float of the estimated delta v
    """
    print("Calculating delta-v")
    kerbin_gravity = conn.space_center.bodies["Kerbin"].surface_gravity
    number_of_stages = vessel.control.current_stage
    sum_delta_v = 0
    total_mass = 0
    previous_stage_total_mass_sum = 0
    # Iterate through each part in the stage in reverse-stage order, so we
    # can accumulate the mass as we go.
    for stage in range(-2, number_of_stages):
        engine_list = []
        stage_delta_v = 0
        stage_total_mass_sum = 0
        stage_dry_mass_sum = 0
        # For each part in the current stage
        for stage_part in vessel.parts.in_decouple_stage(stage):
            # Accumulate the mass so far
            stage_total_mass_sum = stage_total_mass_sum + stage_part.mass / 1000
            stage_dry_mass_sum = stage_dry_mass_sum + stage_part.dry_mass / 1000
            # Sum up the total mass
            total_mass = total_mass + stage_part.mass / 1000
            if stage_part.engine:
                engine_list.append(stage_part)
        # After adding up the mass for parts in the stage, work out the delta v
        # for this stage
        for engine_part in engine_list:
            if sea_level_impulse:
                engine_impulse = engine_part.engine.kerbin_sea_level_specific_impulse
            else:
                engine_impulse = engine_part.engine.vacuum_specific_impulse
            stage_delta_v = (
                engine_impulse
                * kerbin_gravity
                * math.log(
                    total_mass / (stage_dry_mass_sum + previous_stage_total_mass_sum)
                )
            )
        # Sum the stage's delta-v
        sum_delta_v = sum_delta_v + stage_delta_v
        if len(vessel.parts.in_decouple_stage(stage)):
            previous_stage_total_mass_sum = (
                previous_stage_total_mass_sum + stage_total_mass_sum
            )
    return sum_delta_v


def _auto_stage_thread(connection, vessel):
    """
    Automatically activate the next stage once the current stage's fuel is
    empty. Will skip past stages that don't have fuel (e.g. separation-only
    stages)
    """
    while auto_stage_enabled:
        fuel_in_current_stage = vessel.resources_in_decouple_stage(
            stage=vessel.control.current_stage - 1, cumulative=False
        )
        if not fuel_in_current_stage.names:
            print("No fuel in this stage - moving to next stage")
            vessel.control.activate_next_stage()
        else:
            print(f"Fuel types in this stage: {fuel_in_current_stage.names}")
            fuel_in_current_stage_fuel_amount = connection.add_stream(
                fuel_in_current_stage.amount, name=fuel_in_current_stage.names[0]
            )
            while fuel_in_current_stage_fuel_amount() > 0.1:
                if auto_stage_enabled:
                    pass
                else:
                    break

            if auto_stage_enabled:
                print(f"{fuel_in_current_stage.names} empty - moving to next stage")
                vessel.control.activate_next_stage()


def enable_auto_stage(connection, vessel):
    """
    Enable auto staging. Starts a new thread to monitor the fuel in the current
    stage, and moves to the next stage when there's no fuel.
    """
    global auto_stage_enabled
    auto_stage_enabled = True
    auto_stage_thread = threading.Thread(
        target=_auto_stage_thread,
        args=[connection, vessel],
    )
    auto_stage_thread.should_abort_immediately = True
    auto_stage_thread.start()


def disable_auto_stage():
    """
    Stop auto staging.
    """
    global auto_stage_enabled
    auto_stage_enabled = False
