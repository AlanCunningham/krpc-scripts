# kRPC Scripts for Kerbal Space Program

Scripts for the [kRPC mod](https://krpc.github.io/krpc/).

# Installation
- Follow the ["Getting started" guide for kRPC](https://krpc.github.io/krpc/getting-started.html)
```
# Clone the repository
git clone git@github.com:AlanCunningham/krpc-scripts.git

# Create a python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the python dependencies using the requirements.txt file provided
pip install -r requirements.txt
```

# Running the scripts
Running the orbit.py script directly will launch your rocket into orbit.
```
(venv) $ python orbit.py
```

You can also import orbit.py and set the direction of the orbit and target altitude in meters:
```
import krpc
import orbit

connection = krpc.connect(address=ip_address)
vessel = connection.space_center.active_vessel
orbit.launch(connection, vessel, orbit.HEADING_EAST, 80000)
```

Running the mun.py script will maneuver a rocket already in Kerbin-orbit to an orbit around the Mun:
 ```
(venv) $ python mun.py
```

