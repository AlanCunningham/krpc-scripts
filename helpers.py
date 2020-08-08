

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
        print(f"Out of fuel: {fuel_type}")


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