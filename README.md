# Pathdrone
Design a simulation for drones to find the most optimal path to distinguish fires on a grid-based map with obstacles, resource points, objective points, terrain, etc.

## Running

```bash
pip install -r requirements.txt
python Map.py                        # starts with the priority planner
python Map.py --algorithm nearest    # starts with the baseline
```

While it runs, switch the drone's algorithm by clicking a button under
**ALGORITHM** in the side panel, or by pressing `1` / `2`.

| Algorithm | What it does |
|---|---|
| Nearest first | Always flies to the closest fire, refills at the closest water. |
| Priority planner | Goes for the most dangerous fire, sticks with it until it's out, never forgets old fires, and refills at the water tile that's best on the way. |

Algorithms live in `algorithms.py`. To add one, write a class with a
`next_path(drone, burning_tiles)` method and add it to `ALGORITHMS`.
