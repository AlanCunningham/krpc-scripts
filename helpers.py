import math

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


def get_total_delta_v(conn, vessel):
    """
    Gets the total delta-v available to a given vessel.
    Δv = Isp * g0   * ln(Mt/Md)
       = 400 * 9.81 * ln(3.72/1.72)
       = 400 * 9.81 * ln(2.16)
       = 400 * 9.81 * 0.771 = 3026.97 m/s
    :params conn: A krpc connection
    :params vessel: Vessel object
    """
    kerbin_gravity = conn.space_center.bodies["Kerbin"].surface_gravity
    number_of_stages = vessel.control.current_stage
    sum_delta_v = 0
    sum_specific_impulse = 0

    # Iterate through each part in the stage in reverse-stage order, so we
    # can accumulate the mass as we go.
    total_mass = 0
    dry_mass = 0
    previous_stage_total_mass_sum = 0
    # for stage in range(number_of_stages, -2, -1):
    for stage in range(-2, number_of_stages):
        print(f"Stage {stage} (Number of parts: {len(vessel.parts.in_decouple_stage(stage))})")
        parts_list = []
        engine_list = []
        stage_delta_v = 0
        stage_total_mass_sum = 0
        stage_dry_mass_sum = 0
        # For each part in the current stage
        for stage_part in vessel.parts.in_decouple_stage(stage):

            if stage_part.title in parts_list and stage_part.engine:
                # Ignore if we have the same engine more than once in the same
                # stage
                print("###### Ignore #######")
                break
            else:
                # Add the part to the current stage list
                parts_list.append(stage_part.title)
                print(f"{stage_part.title}: Total mass: {stage_part.mass / 1000} | Dry mass: {stage_part.dry_mass / 1000}")

                # Accumulate the dry mass so far
                stage_total_mass_sum = stage_total_mass_sum + stage_part.mass / 1000
                stage_dry_mass_sum = stage_dry_mass_sum + stage_part.dry_mass / 1000

                # Sum up the mass of each part in the current stage in tonnes
                total_mass = total_mass + stage_part.mass / 1000
                dry_mass = dry_mass + stage_part.dry_mass / 1000

                if stage_part.engine:
                    engine_list.append(stage_part)

        # After adding up the mass for part in the stage, work out the delta v
        # for this stage
        for engine_part in engine_list:
            print(f"Calculation: engine_part.engine.kerbin_sea_level_specific_impulse * kerbin_gravity * math.log(total_mass/stage_dry_mass_sum + previous_stage_total_mass_sum)")
            print(f"Calculation: {engine_part.engine.kerbin_sea_level_specific_impulse} * {kerbin_gravity} * math.log({total_mass}/{stage_dry_mass_sum} + {previous_stage_total_mass_sum})")
            print(f"Calculation: {engine_part.engine.kerbin_sea_level_specific_impulse} * {kerbin_gravity} * {math.log(total_mass/stage_dry_mass_sum + previous_stage_total_mass_sum)}")
            stage_delta_v = engine_part.engine.kerbin_sea_level_specific_impulse * kerbin_gravity * math.log(total_mass/(stage_dry_mass_sum + previous_stage_total_mass_sum))

            # Add to the sum delta v and specific impulse
            sum_delta_v = sum_delta_v + stage_delta_v
            sum_specific_impulse = sum_specific_impulse + engine_part.engine.kerbin_sea_level_specific_impulse

        # Debug
        print(f"Total mass so far: {total_mass}")
        print(f"Dry mass so far: {dry_mass + previous_stage_total_mass_sum}")
        print(f"Delta V for stage: {stage_delta_v}")

        if len(vessel.parts.in_decouple_stage(stage)):
            previous_stage_total_mass_sum = previous_stage_total_mass_sum + stage_total_mass_sum
            print(f"Adding total mass from this stage: {previous_stage_total_mass_sum}")

        print("\n")

    print(f"Total delta v: {sum_delta_v}")
    total_mass = vessel.mass / 1000
    dry_mass = vessel.dry_mass / 1000
    print(f"Test Total delta v: {sum_specific_impulse * kerbin_gravity * math.log(total_mass/dry_mass)}")



def wait_for_altitude_more_than(connection, vessel, target_altitude):
    """
    Wait for the altitude to be more than a given value.
    :params conn: A krpc connection
    :params vessel: A vessel object
    :params target_altutude: A double of the target altitude in meters
    """
    altitude = connection.get_call(getattr, vessel.flight(), "mean_altitude")
    parachute_altitude = connection.krpc.Expression.greater_than(
        connection.krpc.Expression.call(altitude),
        connection.krpc.Expression.constant_double(target_altitude)
    )
    altitude_event = connection.krpc.add_event(parachute_altitude)
    with altitude_event.condition:
        altitude_event.wait()
        print(f"At target altitude: {vessel.flight().mean_altitude}")


def wait_for_altitude_less_than(connection, vessel, target_altitude):
    """
    Wait for the altitude to be more than a given value.
    :params conn: A krpc connection
    :params vessel: A vessel object
    :params target_altutude: A double of the target altitude in meters
    """
    altitude = connection.get_call(getattr, vessel.flight(), "mean_altitude")
    parachute_altitude = connection.krpc.Expression.less_than(
        connection.krpc.Expression.call(altitude),
        connection.krpc.Expression.constant_double(target_altitude)
    )
    altitude_event = connection.krpc.add_event(parachute_altitude)
    with altitude_event.condition:
        altitude_event.wait()
        print(f"At target altitude: {vessel.flight().mean_altitude}")


def wait_for_fuel_less_than(connection, vessel, fuel_type, target_fuel):
    """
    Wait for a given fuel type amount to be less than a given value.
    :params conn: A krpc connection
    :params vessel: A vessel object
    :params fuel_type: A string of the fuel type to monitor
    :params target_fuel: A float of the fuel amount target
    """
    fuel_amount = connection.get_call(vessel.resources.amount, name=fuel_type)
    monitor_fuel_expression = connection.krpc.Expression.less_than(
        connection.krpc.Expression.call(fuel_amount),
        connection.krpc.Expression.constant_float(target_fuel)
    )
    fuel_event = connection.krpc.add_event(monitor_fuel_expression)
    with fuel_event.condition:
        fuel_event.wait()
        print(f"{fuel_type} empty")


def wait_for_apoapsis_more_than(connection, vessel, target_apoapsis):
    """
    Wait for the apoapsis to be more than a given value.
    :params conn: A krpc connection
    :params vessel: A vessel object
    :params target_apoapsis: A double of the target apoapsis altitude in meters
    """
    apoapsis_altitude = connection.get_call(getattr, vessel.orbit, 'apoapsis_altitude')
    expr = connection.krpc.Expression.greater_than(
        connection.krpc.Expression.call(apoapsis_altitude),
        connection.krpc.Expression.constant_double(target_apoapsis))
    event = connection.krpc.add_event(expr)
    with event.condition:
        event.wait()
        print(f"At target apoapsis: {vessel.orbit.apoapsis_altitude}")


def wait_for_periapsis_more_than(connection, vessel, target_periapsis):
    """
    Wait for the periapsis to be more than a given value.
    :params conn: A krpc connection
    :params vessel: A vessel object
    :params target_periapsis: A double of the target periapsis altitude in meters
    """
    periapsis_altitude = connection.get_call(getattr, vessel.orbit, 'periapsis_altitude')
    expr = connection.krpc.Expression.greater_than(
        connection.krpc.Expression.call(periapsis_altitude),
        connection.krpc.Expression.constant_double(target_periapsis))
    event = connection.krpc.add_event(expr)
    with event.condition:
        event.wait()
        print(f"At target periapsis: {vessel.orbit.periapsis_altitude}")


def wait_for_time_to_apoapsis_less_than(connection, vessel, target_time):
    """
    Wait for the time to apoapsis to be less than a given value in seconds.
    :params conn: A krpc connection
    :params vessel: A vessel object
    :params target_time: A double of the target time in seconds to the apoapsis
    """
    time_to_apoapsis = connection.get_call(getattr, vessel.orbit, 'time_to_apoapsis')
    expr = connection.krpc.Expression.less_than(
        connection.krpc.Expression.call(time_to_apoapsis),
        connection.krpc.Expression.constant_double(target_time))
    event = connection.krpc.add_event(expr)
    with event.condition:
        event.wait()