import time
import krpc
import helpers


def launch(connection):
    # Setup heading, control and throttle
    vessel = connection.space_center.active_vessel
    vessel.auto_pilot.target_pitch_and_heading(90, 90)
    vessel.auto_pilot.sas = True
    vessel.control.throttle = 1
    time.sleep(1)

    # Launch
    print("Launch")
    vessel.control.activate_next_stage()

    # Thrust until half fuel is remaining, then move to the next stage
    fuel_amount = connection.get_call(vessel.resources.amount, name="LiquidFuel")
    max_fuel_capacity = vessel.resources.max("LiquidFuel")
    monitor_fuel_expression = connection.krpc.Expression.less_than(
        connection.krpc.Expression.call(fuel_amount),
        connection.krpc.Expression.constant_float(10)
    )
    fuel_event = connection.krpc.add_event(monitor_fuel_expression)
    with fuel_event.condition:
        fuel_event.wait()
    # At half fuel
    vessel.control.throttle = 0
    time.sleep(1)
    vessel.control.activate_next_stage()

    # Wait until 500m and deploy the parachutes
    vessel.auto_pilot.sas = False
    altitude = connection.get_call(getattr, vessel.flight(), "mean_altitude")
    parachute_altitude = connection.krpc.Expression.less_than(
        connection.krpc.Expression.call(altitude),
        connection.krpc.Expression.constant_double(500)
    )
    altitude_event = connection.krpc.add_event(parachute_altitude)
    with altitude_event.condition:
        altitude_event.wait()
    print(f"Altitude: {vessel.flight().mean_altitude}")
    vessel.control.activate_next_stage()


if __name__ == "__main__":
    connection = krpc.connect(address="192.168.0.215")
    launch(connection)
