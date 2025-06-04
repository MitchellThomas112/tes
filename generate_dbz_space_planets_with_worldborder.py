import os
import json
import random

# --- Configuration ---
NUM_PLANETS = 10000
MIN_DIST = 400
MAX_DIST = 700
SPACE_ORIGIN = (0, 100, 0)  # Y=100 so planets are not at void or too high
TICK_FUNCTION_FILE = "data/dbz_space/functions/tick.mcfunction"
PLANET_MARKERS_FILE = "data/dbz_space/planet_markers.json"
PLANET_FUNCTIONS_DIR = "data/dbz_space/functions/planets"
PLANET_DIMENSIONS_DIR = "data/dbz_space/dimensions"
PLANET_TEXTURE = "dbz_space:planets/planet_surface"  # 64x64 texture assumed for all
PLANET_WORLD_BORDER = 256  # Set worldborder size (256x256 area)

os.makedirs(os.path.dirname(TICK_FUNCTION_FILE), exist_ok=True)
os.makedirs(PLANET_FUNCTIONS_DIR, exist_ok=True)
os.makedirs(PLANET_DIMENSIONS_DIR, exist_ok=True)

def random_position_far_enough(existing_positions, min_dist, max_dist):
    # Place planets radially outwards, avoiding overlap
    if not existing_positions:
        return SPACE_ORIGIN
    attempts = 0
    while True:
        angle = random.uniform(0, 2 * 3.14159)
        dist = random.randint(min_dist, max_dist)
        last_x, last_y, last_z = existing_positions[-1]
        x = int(last_x + dist * random.cos(angle))
        z = int(last_z + dist * random.sin(angle))
        y = SPACE_ORIGIN[1]
        pos = (x, y, z)
        # Ensure new pos is far enough from all others
        too_close = False
        for px, py, pz in existing_positions[-100:]:  # Only check last 100 for speed
            d = ((x - px)**2 + (z - pz)**2)**0.5
            if d < min_dist:
                too_close = True
                break
        if not too_close:
            return pos
        attempts += 1
        if attempts > 5000:
            # If for some reason we can't find a spot, just place it anyway
            return pos

planets = []
positions = []
for i in range(NUM_PLANETS):
    pos = random_position_far_enough(positions, MIN_DIST, MAX_DIST)
    positions.append(pos)
    name = f"planet_{i+1}"
    dim_name = f"dbz_space:{name}"
    planets.append({
        "name": name,
        "dim_name": dim_name,
        "x": pos[0],
        "y": pos[1],
        "z": pos[2]
    })

# Save planet marker JSON for optional use
with open(PLANET_MARKERS_FILE, "w") as f:
    json.dump(planets, f, indent=2)

# Generate dimension JSON stubs (overworld-like, simple biome source)
dimension_stub = {
    "type": "minecraft:overworld",
    "generator": {
        "type": "minecraft:noise",
        "biome_source": {
            "type": "minecraft:multi_noise",
            "biomes": [{"biome": "minecraft:plains"}]
        },
        "settings": "minecraft:overworld"
    }
}

for p in planets:
    with open(f"{PLANET_DIMENSIONS_DIR}/{p['name']}.json", "w") as f:
        json.dump(dimension_stub, f, indent=4)

# Generate function for each planet (teleport logic and worldborder)
for p in planets:
    planet_dim = p['dim_name']
    fn = f"""# Teleport player to this planet's dimension at a safe Y
execute as @a[distance=..10] at @s run tp @s {planet_dim} 0 100 0
# Set the worldborder to 256x256 centered at 0 0
execute in {planet_dim} run worldborder center 0 0
execute in {planet_dim} run worldborder set {PLANET_WORLD_BORDER}
"""
    with open(f"{PLANET_FUNCTIONS_DIR}/{p['name']}_enter.mcfunction", "w") as f:
        f.write(fn)

# Generate tick.mcfunction to loop over all planets
with open(TICK_FUNCTION_FILE, "w") as f:
    for p in planets:
        marker_tag = f"{p['name']}_marker"
        # Check if any player is near the marker in the space dim, then call the planet's function
        line = f"execute as @a[dimension=dbz_space:space] at @s if entity @e[tag={marker_tag},distance=..10] run function dbz_space:planets/{p['name']}_enter\n"
        f.write(line)

print(f"Generated {NUM_PLANETS} planets, positions, dimension stubs, planet entry functions (with worldborder), and main tick.mcfunction.")

# ---- USAGE NOTES ----
# 1. Place armor stands or markers at each planet's space coordinate (x, y, z) in the space dimension:
#    /summon minecraft:armor_stand X Y Z {{Invisible:1b,Marker:1b,Tags:["planet_1_marker"]}}
# 2. Add the tick function to your datapack's load/tick:
#    In data/dbz_space/functions/tick.mcfunction (already generated), and in data/dbz_space/tags/functions/tick.json:
#    {{
#      "values": ["dbz_space:tick"]
#    }}
# 3. Each planet's dimension has a 256x256 worldborder.