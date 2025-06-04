import os
import json
import math
import random
import numpy as np
from PIL import Image
import colorsys

# --- Configuration ---
NUM_PLANETS = 10000
MIN_DIST = 400
MAX_DIST = 700
SPACE_ORIGIN = (0, 100, 0)
PLANET_DIM = 32
PLANET_Y_SURFACE = 100
PLANET_Y_EXIT = 250
PLANET_WORLDBORDER = 224  # 224x224 = 50,176 blocks, closest integer to 50,000
TICK_FUNCTION_FILE = "data/dbz_space/functions/tick.mcfunction"
PLANET_MARKERS_FILE = "data/dbz_space/planet_markers.json"
PLANET_FUNCTIONS_DIR = "data/dbz_space/functions/planets"
PLANET_DIMENSIONS_DIR = "data/dbz_space/dimensions"
PLANET_EXITS_FUNCTION = "data/dbz_space/functions/planet_exits.mcfunction"
SPHERE_STRUCTURE_FILE = "planet_sphere_blocks.txt"
PLANET_TEXTURES_DIR = "assets/dbz_space/textures/planets"
SPACE_DIM = "dbz_space:space"
SHIP_TYPE_EUREKA = "eureka:ship"
SHIP_TYPE_VS2 = "valkyrienskies:ship"
SHIP_CMD_EUREKA = "eureka move_ship"
SHIP_CMD_VS2 = "vs teleport"
STYLE_PNG = "planet1.png"
BASE_PNG = "namek.png"

# Biome lists (expand as needed)
vanilla_biomes = [
    "minecraft:plains", "minecraft:desert", "minecraft:savanna", "minecraft:forest",
    "minecraft:taiga", "minecraft:swamp", "minecraft:jungle", "minecraft:badlands",
    "minecraft:snowy_plains", "minecraft:birch_forest"
]
bop_biomes = [
    "biomesoplenty:lavender_field", "biomesoplenty:maple_woods", "biomesoplenty:rainbow_hills",
    "biomesoplenty:alps", "biomesoplenty:cherry_blossom_grove", "biomesoplenty:orchard",
    "biomesoplenty:ominous_woods", "biomesoplenty:wasteland", "biomesoplenty:bayou",
    "biomesoplenty:crag"
]
all_biomes = vanilla_biomes + bop_biomes

os.makedirs(os.path.dirname(TICK_FUNCTION_FILE), exist_ok=True)
os.makedirs(PLANET_FUNCTIONS_DIR, exist_ok=True)
os.makedirs(PLANET_DIMENSIONS_DIR, exist_ok=True)
os.makedirs(PLANET_TEXTURES_DIR, exist_ok=True)

def random_position_far_enough(existing_positions, min_dist, max_dist):
    if not existing_positions:
        return SPACE_ORIGIN
    attempts = 0
    while True:
        angle = math.radians(random.uniform(0, 360))
        dist = random.randint(min_dist, max_dist)
        last_x, last_y, last_z = existing_positions[-1]
        x = int(last_x + dist * math.cos(angle))
        z = int(last_z + dist * math.sin(angle))
        y = SPACE_ORIGIN[1]
        pos = (x, y, z)
        too_close = False
        for px, py, pz in existing_positions[-100:]:
            d = ((x - px) ** 2 + (z - pz) ** 2) ** 0.5
            if d < min_dist:
                too_close = True
                break
        if not too_close:
            return pos
        attempts += 1
        if attempts > 5000:
            return pos

# --- PLANETS METADATA ---
planets = []
positions = []
for i in range(NUM_PLANETS):
    pos = random_position_far_enough(positions, MIN_DIST, MAX_DIST)
    positions.append(pos)
    name = f"planet_{i+1}"
    dim_name = f"dbz_space:{name}"
    skin = f"dbz_space:planets/skin_{i+1}"  # One unique skin per planet
    chosen_biome = random.choice(all_biomes)
    planets.append({
        "name": name,
        "dim_name": dim_name,
        "x": pos[0],
        "y": pos[1],
        "z": pos[2],
        "skin": skin,
        "biome": chosen_biome
    })

with open(PLANET_MARKERS_FILE, "w") as f:
    json.dump(planets, f, indent=2)

# --- DIMENSIONS ---
for p in planets:
    biome = p["biome"]
    dimension_custom = {
        "type": "minecraft:overworld",
        "generator": {
            "type": "minecraft:noise",
            "biome_source": {
                "type": "minecraft:fixed",
                "biome": biome
            },
            "settings": "minecraft:overworld"
        }
    }
    with open(f"{PLANET_DIMENSIONS_DIR}/{p['name']}.json", "w") as f:
        json.dump(dimension_custom, f, indent=4)

# --- FUNCTIONS ---
def make_ship_teleport_lines(planet_dim, tx, ty, tz):
    lines = []
    # Eureka ships
    lines.append(
        f"execute as @a at @s if entity @e[type={SHIP_TYPE_EUREKA},distance=..5] run {SHIP_CMD_EUREKA} {planet_dim} {tx} {ty} {tz}"
    )
    # Valkyrien Skies 2 ships
    lines.append(
        f"execute as @a at @s if entity @e[type={SHIP_TYPE_VS2},distance=..5] run {SHIP_CMD_VS2} {planet_dim} {tx} {ty} {tz}"
    )
    # Fallback: player only
    lines.append(
        f"execute as @a at @s unless entity @e[type={SHIP_TYPE_EUREKA},distance=..5] unless entity @e[type={SHIP_TYPE_VS2},distance=..5] run tp @s {planet_dim} {tx} {ty} {tz}"
    )
    return "\n".join(lines)

for p in planets:
    planet_dim = p['dim_name']
    # Exclude overworld from worldborder logic
    if planet_dim == "minecraft:overworld":
        continue
    entry = f"""# Ship-compatible teleport to planet and set worldborder
{make_ship_teleport_lines(planet_dim, 0, PLANET_Y_SURFACE, 0)}
execute in {planet_dim} run worldborder center 0 0
execute in {planet_dim} run worldborder set {PLANET_WORLDBORDER}
"""
    with open(f"{PLANET_FUNCTIONS_DIR}/{p['name']}_enter.mcfunction", "w") as f:
        f.write(entry)

for p in planets:
    planet_dim = p['dim_name']
    x, z = p['x'], p['z']
    exit_func_path = f"{PLANET_FUNCTIONS_DIR}/{p['name']}_exit.mcfunction"
    exit_logic = f"""# Exit: if above Y={PLANET_Y_EXIT}, ship/player returns to space marker
execute as @a[dimension={planet_dim},y={PLANET_Y_EXIT}..] at @s if entity @e[type={SHIP_TYPE_EUREKA},distance=..5] run {SHIP_CMD_EUREKA} {SPACE_DIM} {x} 110 {z}
execute as @a[dimension={planet_dim},y={PLANET_Y_EXIT}..] at @s if entity @e[type={SHIP_TYPE_VS2},distance=..5] run {SHIP_CMD_VS2} {SPACE_DIM} {x} 110 {z}
execute as @a[dimension={planet_dim},y={PLANET_Y_EXIT}..] at @s unless entity @e[type={SHIP_TYPE_EUREKA},distance=..5] unless entity @e[type={SHIP_TYPE_VS2},distance=..5] run tp @s {SPACE_DIM} {x} 110 {z}
"""
    with open(exit_func_path, "w") as f:
        f.write(exit_logic)

with open(TICK_FUNCTION_FILE, "w") as f:
    for p in planets:
        marker_tag = f"{p['name']}_marker"
        f.write(f"execute as @a[dimension={SPACE_DIM}] at @s if entity @e[tag={marker_tag},distance=..10] run function dbz_space:planets/{p['name']}_enter\n")
    f.write("function dbz_space:planet_exits\n")

with open(PLANET_EXITS_FUNCTION, "w") as f:
    for p in planets:
        f.write(f"function dbz_space:planets/{p['name']}_exit\n")

# --- PLANET SPHERE BLOCKLIST ---
sphere_blocks = []
radius = PLANET_DIM // 2
for y in range(PLANET_DIM):
    for z in range(PLANET_DIM):
        for x in range(PLANET_DIM):
            dx = x - radius + 0.5
            dy = y - radius + 0.5
            dz = z - radius + 0.5
            if dx*dx + dy*dy + dz*dz <= (radius-0.5)**2:
                sphere_blocks.append((x, y, z))
with open(SPHERE_STRUCTURE_FILE, "w") as f:
    for bx, by, bz in sphere_blocks:
        f.write(f"{bx} {by} {bz}\n")
print("Saved 'planet_sphere_blocks.txt' for use with WorldEdit or as a placement guide.")

# --- ADVANCED PLANET SKIN GENERATOR ---
def extract_colored_mask(image):
    arr = np.array(image.convert('RGBA'))
    mask = np.zeros((arr.shape[0], arr.shape[1]), dtype=np.uint8)
    for y in range(arr.shape[0]):
        for x in range(arr.shape[1]):
            r, g, b, a = arr[y, x]
            if a > 32:
                mask[y, x] = 255
    return Image.fromarray(mask, 'L')

def randomize_palette(img, mask):
    arr = np.array(img.convert('RGBA'))
    mask_arr = np.array(mask.convert('L'))
    h_shift = random.uniform(0, 1)
    s_scale = random.uniform(0.7, 1.1)
    v_scale = random.uniform(0.8, 1.2)
    for y in range(arr.shape[0]):
        for x in range(arr.shape[1]):
            a = arr[y, x, 3]
            if mask_arr[y, x] < 32 or a < 32:
                arr[y, x, 3] = 0  # transparent outside mask
                continue
            r, g, b = arr[y, x, :3]
            h, s, v = colorsys.rgb_to_hsv(r/255., g/255., b/255.)
            h = (h + h_shift) % 1.0
            s = min(max(s * s_scale, 0.35), 1.0)
            v = min(max(v * v_scale, 0.7), 1.0)
            rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
            arr[y, x, :3] = int(rr*255), int(gg*255), int(bb*255)
    return Image.fromarray(arr, 'RGBA')

def transfer_bands_and_randomize(style_path, base_path, output_path):
    base = Image.open(base_path).convert("RGBA").resize((32,32), Image.LANCZOS)
    style = Image.open(style_path).convert("RGBA").resize((32,32), Image.LANCZOS)
    mask = extract_colored_mask(base)
    style_arr = np.array(style)
    out_arr = np.array(base)
    for y in range(32):
        for x in range(32):
            if mask.getpixel((x,y)) > 32:
                out_arr[y,x,:3] = style_arr[y,x,:3]
                out_arr[y,x,3] = 255
            else:
                out_arr[y,x,3] = 0
    out_img = Image.fromarray(out_arr, 'RGBA')
    out_img = randomize_palette(out_img, mask)
    out_img.save(output_path)

# Generate a unique random skin for each planet using the style and mask PNGs
for i, p in enumerate(planets):
    output_path = f"{PLANET_TEXTURES_DIR}/skin_{i+1}.png"
    transfer_bands_and_randomize(STYLE_PNG, BASE_PNG, output_path)
    if (i+1) % 100 == 0:
        print(f"Generated {i+1} planet skins...")

print(f"Generated {NUM_PLANETS} planets: dimension files, entry/exit functions, sphere blocklist, and unique planet textures.")

# --- USAGE ---
# 1. Place armor stands at each planet's space coordinate (x, y, z) with tag "planet_N_marker":
#    /summon minecraft:armor_stand X Y Z {Invisible:1b,Marker:1b,Tags:["planet_1_marker"]}
# 2. Import the 32x32x32 sphere structure at (0,100,0) in each planet dimension (see planet_sphere_blocks.txt).
#    Use WorldEdit, Litematica, or Structure Block.
# 3. Assign the PNG skin as the planet's surface texture in your resource pack or via WorldEdit's //replace.
# 4. The tick function will handle entry/exit/ship/worldborder logic.
# 5. Add the tick function to your tick.json:
#    {
#      "values": ["dbz_space:tick"]
#    }
# 6. Each dimension has one random vanilla or Biomes O' Plenty biome.