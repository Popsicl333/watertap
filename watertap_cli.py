#!/usr/bin/env python
"""
WaterTAP Interactive Membrane Simulation CLI

An interactive terminal program that guides users step-by-step through
membrane simulation setup without requiring Python knowledge.

Usage:
    python watertap_cli.py

Supports: RO, NF-DSPMDE, ED (0D/1D), MD, and Zero-Order (MF/UF/NF) models.
"""
# ============================================================================
# Section 1: Utility Functions
# ============================================================================

def print_header(title):
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


def print_divider():
    print("-" * 64)


def format_value(val):
    if val is None:
        return "N/A"
    if isinstance(val, bool):  # must check bool before int (bool is subclass of int)
        return "Yes" if val else "No"
    if isinstance(val, str):
        return val
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if val == 0:
            return "0"
        if abs(val) < 0.01 or abs(val) >= 1e6:
            return f"{val:.4e}"
        return f"{val:.6g}"
    return str(val)


def get_choice(prompt, options, default_key=None):
    """Display numbered options and get user selection."""
    while True:
        print()
        for key in sorted(options.keys()):
            label = options[key] if isinstance(options[key], str) else options[key][0]
            marker = " (default)" if key == default_key else ""
            print(f"  {key}. {label}{marker}")
        default_hint = f" [{default_key}]" if default_key is not None else ""
        user_input = input(f"\n{prompt}{default_hint}: ").strip()
        if user_input == "" and default_key is not None:
            return default_key
        try:
            choice = int(user_input)
            if choice in options:
                return choice
        except ValueError:
            pass
        print(f"  Invalid choice. Please enter one of: {', '.join(str(k) for k in sorted(options.keys()))}")


def get_float(prompt, default=None, allow_negative=True, hint=None, warn_range=None):
    """Prompt user for a numeric value with a default.

    Args:
        hint: One-line guidance string shown before the prompt (e.g. typical range).
        warn_range: (min, max) tuple. If the entered value is outside this range,
                    a warning is shown and the user can choose to re-enter.
    """
    while True:
        if hint:
            print(f"    ({hint})")
        default_hint = f" [{format_value(default)}]" if default is not None else ""
        user_input = input(f"  {prompt}{default_hint}: ").strip()
        if user_input == "" and default is not None:
            return default
        try:
            val = float(user_input)
            if not allow_negative and val < 0:
                print("  Value must be non-negative. Try again.")
                continue
            if warn_range and (val < warn_range[0] or val > warn_range[1]):
                print(f"  WARNING: {format_value(val)} is outside the typical range "
                      f"({format_value(warn_range[0])} to {format_value(warn_range[1])})")
                confirm = input("  Use this value anyway? [y/N]: ").strip().lower()
                if confirm not in ("y", "yes"):
                    continue
            return val
        except ValueError:
            print("  Invalid number. Enter a decimal or scientific notation (e.g., 42, 3.14, 4.2e-12).")


def get_int(prompt, default=None, min_val=None, hint=None):
    """Prompt user for an integer value with a default."""
    while True:
        if hint:
            print(f"    ({hint})")
        default_hint = f" [{default}]" if default is not None else ""
        user_input = input(f"  {prompt}{default_hint}: ").strip()
        if user_input == "" and default is not None:
            return default
        try:
            val = int(user_input)
            if min_val is not None and val < min_val:
                print(f"  Value must be at least {min_val}. Try again.")
                continue
            return val
        except ValueError:
            print("  Invalid number. Please enter a whole number (e.g., 10, 50).")


def get_bool(prompt, default=False):
    """Prompt 'Yes/No' choice."""
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        user_input = input(f"  {prompt} {hint}: ").strip().lower()
        if user_input == "":
            return default
        if user_input in ("y", "yes"):
            return True
        if user_input in ("n", "no"):
            return False
        print("  Please enter 'y' or 'n'.")


# ============================================================================
# Section 2: Review & Edit Screen
# ============================================================================

def build_review_entries(config):
    """Build a flat list of reviewable entries from config."""
    entries = []
    row = 1
    for item in config.get("_review_order", []):
        key = item["key"]
        label = item["label"]
        unit = item.get("unit", "")
        section = item.get("section", "")
        editable = item.get("editable", True)
        edit_type = item.get("edit_type", "float")  # float, choice, int, bool
        val = config.get(key, "")
        display_val = item.get("display_fn", format_value)(val) if "display_fn" in item else format_value(val)
        entries.append({
            "row": row,
            "key": key,
            "label": label,
            "value": val,
            "display_val": display_val,
            "unit": unit,
            "section": section,
            "editable": editable,
            "edit_type": edit_type,
            "edit_options": item.get("edit_options", None),
        })
        row += 1
    return entries


def print_review_table(entries):
    """Print a formatted review table."""
    current_section = None
    print()
    for e in entries:
        if e["section"] != current_section:
            current_section = e["section"]
            print_divider()
            print(f"  {current_section}")
            print_divider()
        unit_str = f" {e['unit']}" if e["unit"] else ""
        print(f"  [{e['row']:2d}] {e['label']:<42s} {e['display_val']}{unit_str}")
    print()


def review_and_edit(config):
    """Show all settings, let user edit by row number."""
    while True:
        print_header("Review Your Configuration")
        entries = build_review_entries(config)
        print_review_table(entries)

        print("  Enter a row number to edit that value,")
        print("  or press Enter to confirm and run the simulation.")
        print("  Type 'q' to cancel and return to main menu.")
        user_input = input("\n  Your choice: ").strip()

        if user_input == "":
            return config
        if user_input.lower() == "q":
            return None

        try:
            row_num = int(user_input)
            entry = next((e for e in entries if e["row"] == row_num), None)
            if entry is None:
                print(f"  No row {row_num}. Valid rows: 1-{len(entries)}")
                continue
            if not entry["editable"]:
                print(f"  '{entry['label']}' cannot be edited directly.")
                continue

            print(f"\n  Editing: {entry['label']}")
            if entry["edit_type"] == "float":
                new_val = get_float("New value", default=entry["value"])
                config[entry["key"]] = new_val
            elif entry["edit_type"] == "int":
                new_val = get_int("New value", default=entry["value"])
                config[entry["key"]] = new_val
            elif entry["edit_type"] == "bool":
                new_val = get_bool("New value (yes/no)", default=entry["value"])
                config[entry["key"]] = new_val
            elif entry["edit_type"] == "choice":
                opts = entry["edit_options"]
                if opts:
                    new_choice = get_choice("Select new value", opts)
                    config[entry["key"]] = new_choice
            print("  Value updated.")
        except ValueError:
            print("  Invalid input.")

    return config


# ============================================================================
# Section 3a: RO Configuration
# ============================================================================

def configure_ro():
    print_header("Reverse Osmosis (RO 0D) Configuration")

    config = {"model_type": "ro", "_review_order": []}

    # Step 1: Transport Model
    print("\n-- Step 1: Transport Model --")
    tm_opts = {1: "Solution-Diffusion (SD)", 2: "Spiegler-Kedem-Katchalsky (SKK)"}
    config["transport_model"] = get_choice("Select transport model", tm_opts, default_key=1)

    # Step 2: Concentration Polarization
    print("\n-- Step 2: Concentration Polarization --")
    cp_opts = {1: "None (ignore)", 2: "Fixed (specify CP modulus)", 3: "Calculated"}
    config["cp_type"] = get_choice("Select concentration polarization type", cp_opts, default_key=3)

    # Step 3: Mass Transfer Coefficient (only if CP != none)
    mtc_opts = {1: "None", 2: "Fixed (specify value)", 3: "Calculated"}
    if config["cp_type"] != 1:
        print("\n-- Step 3: Mass Transfer Coefficient --")
        config["mtc_type"] = get_choice("Select mass transfer coefficient", mtc_opts, default_key=3)
    else:
        config["mtc_type"] = 1

    # Step 4: Pressure Change
    print("\n-- Step 4: Pressure Change --")
    config["has_pressure_change"] = get_bool("Include pressure change?", default=True)
    if config["has_pressure_change"]:
        pc_opts = {1: "Fixed per stage", 2: "Fixed per unit length", 3: "Calculated"}
        config["pressure_change_type"] = get_choice("Select pressure change type", pc_opts, default_key=1)
    else:
        config["pressure_change_type"] = 1

    # Step 5: Module Type
    print("\n-- Step 5: Module Type --")
    mod_opts = {1: "Flat sheet", 2: "Spiral wound"}
    config["module_type"] = get_choice("Select module type", mod_opts, default_key=1)

    # Step 6: Membrane Properties
    print("\n-- Step 6: Membrane Properties --")
    config["A_comp"] = get_float("Water permeability A_comp (m/(Pa*s))", default=4.2e-12,
        hint="Typical: 1e-12 to 1e-11. Use scientific notation, e.g. 4.2e-12",
        warn_range=(1e-13, 1e-10))
    config["B_comp"] = get_float("Salt permeability B_comp (m/s)", default=3.5e-8,
        hint="Typical: 1e-08 to 1e-06. Use scientific notation, e.g. 3.5e-08",
        warn_range=(1e-11, 1e-5))
    config["area"] = get_float("Membrane area (m^2)", default=50.0, allow_negative=False,
        hint="Typical: 10 to 500. Enter a number, e.g. 50",
        warn_range=(0.1, 10000))

    # Step 7: Feed Conditions
    print("\n-- Step 7: Feed Conditions --")
    config["feed_h2o"] = get_float("Feed H2O flow rate (kg/s)", default=0.965, allow_negative=False,
        hint="Typical: 0.5 to 5. For seawater ~96.5% water, e.g. 0.965",
        warn_range=(0.001, 100))
    config["feed_nacl"] = get_float("Feed NaCl flow rate (kg/s)", default=0.035, allow_negative=False,
        hint="Typical: 0.01 to 0.5. Seawater ~3.5% salt, e.g. 0.035",
        warn_range=(0.0001, 10))
    config["feed_pressure"] = get_float("Feed pressure (Pa)", default=50e5, allow_negative=False,
        hint="1 bar = 100000 Pa. Typical RO: 10-70 bar (1e6 to 7e6 Pa). e.g. 5e6 = 50 bar",
        warn_range=(1e4, 5e7))
    config["feed_temperature"] = get_float("Feed temperature (K)", default=298.15, allow_negative=False,
        hint="K = Celsius + 273.15. Typical: 288-313 K (15-40 C). e.g. 298.15 = 25 C",
        warn_range=(273.15, 373.15))

    # Step 8: Permeate
    print("\n-- Step 8: Permeate Conditions --")
    config["permeate_pressure"] = get_float("Permeate pressure (Pa)", default=101325, allow_negative=False,
        hint="101325 Pa = 1 atm (standard). Typical: 101325",
        warn_range=(1e4, 5e7))

    # Step 9: Conditional Inputs
    print("\n-- Step 9: Additional Parameters (based on your selections) --")

    needs_geometry = (config["mtc_type"] == 3 or
                      (config["has_pressure_change"] and config["pressure_change_type"] == 3))

    if config["has_pressure_change"] and config["pressure_change_type"] == 1:
        config["deltaP"] = get_float("Pressure drop deltaP (Pa, negative = drop)", default=-3e5,
            hint="Negative value = pressure loss. Typical: -5e5 to -1e5 Pa")
    if config["has_pressure_change"] and config["pressure_change_type"] == 2:
        config["dP_dx"] = get_float("Pressure drop per unit length (Pa/m)", default=-5e4,
            hint="Negative value = pressure loss. Typical: -1e5 to -1e4 Pa/m")
    if config["cp_type"] == 2:
        config["cp_modulus"] = get_float("Concentration polarization modulus", default=1.1, allow_negative=False,
            hint="Ratio > 1 means wall concentration > bulk. Typical: 1.0 to 2.0",
            warn_range=(1.0, 5.0))
    if config["mtc_type"] == 2:
        config["kf_inlet"] = get_float("Mass transfer coeff at inlet (m/s)", default=2e-5, allow_negative=False,
            hint="Typical: 1e-5 to 5e-5. Use scientific notation, e.g. 2e-5")
        config["kf_outlet"] = get_float("Mass transfer coeff at outlet (m/s)", default=2e-5, allow_negative=False,
            hint="Typical: 1e-5 to 5e-5. Use scientific notation, e.g. 2e-5")
    if needs_geometry:
        config["channel_height"] = get_float("Channel height (m)", default=1e-3, allow_negative=False,
            hint="Typical: 5e-4 to 2e-3 m (0.5 to 2 mm). e.g. 1e-3 = 1 mm",
            warn_range=(1e-4, 0.01))
        config["spacer_porosity"] = get_float("Spacer porosity (0-1)", default=0.95, allow_negative=False,
            hint="Fraction of open space. Typical: 0.80 to 0.99",
            warn_range=(0.01, 1.0))
        config["length"] = get_float("Membrane length (m)", default=10.0, allow_negative=False,
            hint="Typical: 1 to 20 m",
            warn_range=(0.1, 100))
    if config["transport_model"] == 2:
        config["reflect_coeff"] = get_float("Reflection coefficient (0-1)", default=0.9, allow_negative=False,
            hint="0 = no rejection, 1 = perfect rejection. Typical: 0.8 to 1.0",
            warn_range=(0.0, 1.0))

    # Build review order
    ro = config["_review_order"]
    tm_display = {1: "Solution-Diffusion (SD)", 2: "Spiegler-Kedem-Katchalsky (SKK)"}
    cp_display = {1: "None", 2: "Fixed", 3: "Calculated"}
    mtc_display = {1: "None", 2: "Fixed", 3: "Calculated"}
    pc_display = {1: "Fixed per stage", 2: "Fixed per unit length", 3: "Calculated"}
    mod_display = {1: "Flat sheet", 2: "Spiral wound"}

    ro.append({"key": "transport_model", "label": "Transport Model", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": tm_opts,
               "display_fn": lambda v: tm_display.get(v, str(v))})
    ro.append({"key": "cp_type", "label": "Concentration Polarization", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": cp_opts,
               "display_fn": lambda v: cp_display.get(v, str(v))})
    ro.append({"key": "mtc_type", "label": "Mass Transfer Coefficient", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": mtc_opts,
               "display_fn": lambda v: mtc_display.get(v, str(v))})
    ro.append({"key": "has_pressure_change", "label": "Include Pressure Change", "section": "Model Configuration",
               "edit_type": "bool"})
    if config["has_pressure_change"]:
        ro.append({"key": "pressure_change_type", "label": "Pressure Change Type", "section": "Model Configuration",
                    "edit_type": "choice", "edit_options": pc_opts,
                    "display_fn": lambda v: pc_display.get(v, str(v))})
    ro.append({"key": "module_type", "label": "Module Type", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": mod_opts,
               "display_fn": lambda v: mod_display.get(v, str(v))})

    ro.append({"key": "A_comp", "label": "Water Permeability (A_comp)", "unit": "m/(Pa*s)", "section": "Membrane Properties"})
    ro.append({"key": "B_comp", "label": "Salt Permeability (B_comp)", "unit": "m/s", "section": "Membrane Properties"})
    ro.append({"key": "area", "label": "Membrane Area", "unit": "m^2", "section": "Membrane Properties"})
    if config["transport_model"] == 2:
        ro.append({"key": "reflect_coeff", "label": "Reflection Coefficient", "section": "Membrane Properties"})

    ro.append({"key": "feed_h2o", "label": "Feed H2O Flow Rate", "unit": "kg/s", "section": "Feed Conditions"})
    ro.append({"key": "feed_nacl", "label": "Feed NaCl Flow Rate", "unit": "kg/s", "section": "Feed Conditions"})
    ro.append({"key": "feed_pressure", "label": "Feed Pressure", "unit": "Pa", "section": "Feed Conditions"})
    ro.append({"key": "feed_temperature", "label": "Feed Temperature", "unit": "K", "section": "Feed Conditions"})
    ro.append({"key": "permeate_pressure", "label": "Permeate Pressure", "unit": "Pa", "section": "Feed Conditions"})

    if config["has_pressure_change"] and config["pressure_change_type"] == 1:
        ro.append({"key": "deltaP", "label": "Pressure Drop (deltaP)", "unit": "Pa", "section": "Additional Parameters"})
    if config["has_pressure_change"] and config["pressure_change_type"] == 2:
        ro.append({"key": "dP_dx", "label": "Pressure Drop per Length", "unit": "Pa/m", "section": "Additional Parameters"})
    if config["cp_type"] == 2:
        ro.append({"key": "cp_modulus", "label": "CP Modulus", "section": "Additional Parameters"})
    if config["mtc_type"] == 2:
        ro.append({"key": "kf_inlet", "label": "Mass Transfer Coeff (inlet)", "unit": "m/s", "section": "Additional Parameters"})
        ro.append({"key": "kf_outlet", "label": "Mass Transfer Coeff (outlet)", "unit": "m/s", "section": "Additional Parameters"})
    if needs_geometry:
        ro.append({"key": "channel_height", "label": "Channel Height", "unit": "m", "section": "Additional Parameters"})
        ro.append({"key": "spacer_porosity", "label": "Spacer Porosity", "section": "Additional Parameters"})
        ro.append({"key": "length", "label": "Membrane Length", "unit": "m", "section": "Additional Parameters"})

    return config


# ============================================================================
# Section 3b: NF-DSPMDE Configuration
# ============================================================================

NF_ION_PRESETS = {
    1: {
        "name": "Standard 5-ion (Ca, Mg, Na, SO4, Cl)",
        "solute_list": ["Ca_2+", "SO4_2-", "Mg_2+", "Na_+", "Cl_-"],
        "charge": {"Ca_2+": 2, "SO4_2-": -2, "Mg_2+": 2, "Na_+": 1, "Cl_-": -1},
        "diffusivity_data": {
            ("Liq", "Ca_2+"): 9.2e-10, ("Liq", "SO4_2-"): 1.06e-09,
            ("Liq", "Mg_2+"): 7.06e-10, ("Liq", "Na_+"): 1.33e-09, ("Liq", "Cl_-"): 2.03e-09,
        },
        "mw_data": {"H2O": 0.018, "Ca_2+": 0.04, "Mg_2+": 0.024, "SO4_2-": 0.096, "Na_+": 0.023, "Cl_-": 0.035},
        "stokes_radius_data": {"Ca_2+": 3.09e-10, "Mg_2+": 3.47e-10, "SO4_2-": 2.3e-10, "Cl_-": 1.21e-10, "Na_+": 1.84e-10},
        "default_feed_mass_frac": {
            "Ca_2+": 382e-6, "Mg_2+": 1394e-6, "SO4_2-": 2136e-6,
            "Cl_-": 20101.6e-6, "Na_+": 11122e-6,
        },
        "adjust_ion": "Cl_-",
    },
    2: {
        "name": "Simple 2-ion (Na, Cl)",
        "solute_list": ["Na_+", "Cl_-"],
        "charge": {"Na_+": 1, "Cl_-": -1},
        "diffusivity_data": {("Liq", "Na_+"): 1.33e-09, ("Liq", "Cl_-"): 2.03e-09},
        "mw_data": {"H2O": 0.018, "Na_+": 0.023, "Cl_-": 0.035},
        "stokes_radius_data": {"Cl_-": 1.21e-10, "Na_+": 1.84e-10},
        "default_feed_mass_frac": {"Na_+": 11122e-6, "Cl_-": 20101.6e-6},
        "adjust_ion": "Cl_-",
    },
}


def configure_nf_dspmde():
    print_header("Nanofiltration DSPM-DE (0D) Configuration")
    config = {"model_type": "nf_dspmde", "_review_order": []}

    # Step 1: Ion Selection
    print("\n-- Step 1: Ion Selection --")
    ion_opts = {k: v["name"] for k, v in NF_ION_PRESETS.items()}
    ion_choice = get_choice("Select ion preset", ion_opts, default_key=1)
    preset = NF_ION_PRESETS[ion_choice]
    config["ion_preset"] = ion_choice
    config["solute_list"] = preset["solute_list"]
    config["charge"] = preset["charge"]
    config["diffusivity_data"] = preset["diffusivity_data"]
    config["mw_data"] = preset["mw_data"]
    config["stokes_radius_data"] = preset["stokes_radius_data"]
    config["adjust_ion"] = preset["adjust_ion"]

    # Step 2: Mass Transfer Coefficient
    print("\n-- Step 2: Mass Transfer Coefficient --")
    mtc_opts = {1: "None", 2: "Fixed", 3: "Spiral wound correlation"}
    config["mtc_type"] = get_choice("Select mass transfer coefficient", mtc_opts, default_key=3)

    # Step 3: Concentration Polarization
    print("\n-- Step 3: Concentration Polarization --")
    cp_opts = {1: "None", 2: "Calculated"}
    config["cp_type"] = get_choice("Select concentration polarization type", cp_opts, default_key=2)

    # Step 4: Membrane Properties
    print("\n-- Step 4: Membrane Properties --")
    config["radius_pore"] = get_float("Pore radius (m)", default=0.5e-9, allow_negative=False,
        hint="Typical NF: 0.3e-9 to 1e-9 m. Use scientific notation, e.g. 0.5e-9",
        warn_range=(1e-10, 1e-8))
    config["membrane_thickness"] = get_float("Effective membrane thickness (m)", default=1.33e-6, allow_negative=False,
        hint="Typical: 1e-6 to 1e-5 m. Use scientific notation, e.g. 1.33e-6",
        warn_range=(1e-7, 1e-4))
    config["membrane_charge_density"] = get_float("Membrane charge density (mol/m^3)", default=-27,
        hint="Negative for negatively charged membranes. Typical: -100 to -5",
        warn_range=(-1000, 1000))
    config["dielectric_constant_pore"] = get_float("Dielectric constant of pore", default=41.3, allow_negative=False,
        hint="Dimensionless. Water ~80, typical pore: 30 to 60",
        warn_range=(1, 100))
    config["area"] = get_float("Membrane area (m^2)", default=50.0, allow_negative=False,
        hint="Typical: 10 to 500",
        warn_range=(0.1, 10000))

    # Step 5: Channel Properties
    print("\n-- Step 5: Channel Properties --")
    config["spacer_porosity"] = get_float("Spacer porosity (0-1)", default=0.85, allow_negative=False,
        hint="Fraction of open space. Typical: 0.70 to 0.95",
        warn_range=(0.01, 1.0))
    config["channel_height"] = get_float("Channel height (m)", default=5e-4, allow_negative=False,
        hint="Typical: 3e-4 to 1e-3 m (0.3 to 1 mm). e.g. 5e-4 = 0.5 mm",
        warn_range=(1e-5, 0.01))
    config["velocity"] = get_float("Feed velocity at inlet (m/s)", default=0.25, allow_negative=False,
        hint="Typical: 0.1 to 1.0 m/s",
        warn_range=(0.01, 10))

    # Step 6: Feed Conditions
    print("\n-- Step 6: Feed Conditions --")
    config["feed_mass_flow"] = get_float("Total feed mass flow (kg/s)", default=1.0, allow_negative=False,
        hint="Typical: 0.1 to 10 kg/s")
    feed_fracs = {}
    print("  Enter mass fraction for each ion (mass of ion / total mass):")
    for ion in preset["solute_list"]:
        default_frac = preset["default_feed_mass_frac"].get(ion, 1e-4)
        feed_fracs[ion] = get_float(f"  {ion} mass fraction", default=default_frac, allow_negative=False)
    config["feed_mass_frac"] = feed_fracs
    config["feed_pressure"] = get_float("Feed pressure (Pa)", default=4e5, allow_negative=False,
        hint="1 bar = 100000 Pa. Typical NF: 3-10 bar (3e5 to 1e6 Pa). e.g. 4e5 = 4 bar",
        warn_range=(1e4, 5e7))
    config["feed_temperature"] = get_float("Feed temperature (K)", default=298.15, allow_negative=False,
        hint="K = Celsius + 273.15. Typical: 288-313 K (15-40 C). e.g. 298.15 = 25 C",
        warn_range=(273.15, 373.15))

    # Step 7: Permeate
    print("\n-- Step 7: Permeate Conditions --")
    config["permeate_pressure"] = get_float("Permeate pressure (Pa)", default=101325, allow_negative=False,
        hint="101325 Pa = 1 atm (standard). Typical: 101325",
        warn_range=(1e4, 5e7))

    # Build review order
    ro = config["_review_order"]
    ion_display = {k: v["name"] for k, v in NF_ION_PRESETS.items()}
    mtc_display = {1: "None", 2: "Fixed", 3: "Spiral wound"}
    cp_display = {1: "None", 2: "Calculated"}

    ro.append({"key": "ion_preset", "label": "Ion Preset", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": ion_opts,
               "display_fn": lambda v: ion_display.get(v, str(v))})
    ro.append({"key": "mtc_type", "label": "Mass Transfer Coefficient", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": mtc_opts,
               "display_fn": lambda v: mtc_display.get(v, str(v))})
    ro.append({"key": "cp_type", "label": "Concentration Polarization", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": cp_opts,
               "display_fn": lambda v: cp_display.get(v, str(v))})

    ro.append({"key": "radius_pore", "label": "Pore Radius", "unit": "m", "section": "Membrane Properties"})
    ro.append({"key": "membrane_thickness", "label": "Effective Membrane Thickness", "unit": "m", "section": "Membrane Properties"})
    ro.append({"key": "membrane_charge_density", "label": "Membrane Charge Density", "unit": "mol/m^3", "section": "Membrane Properties"})
    ro.append({"key": "dielectric_constant_pore", "label": "Dielectric Constant (pore)", "section": "Membrane Properties"})
    ro.append({"key": "area", "label": "Membrane Area", "unit": "m^2", "section": "Membrane Properties"})

    ro.append({"key": "spacer_porosity", "label": "Spacer Porosity", "section": "Channel Properties"})
    ro.append({"key": "channel_height", "label": "Channel Height", "unit": "m", "section": "Channel Properties"})
    ro.append({"key": "velocity", "label": "Feed Velocity (inlet)", "unit": "m/s", "section": "Channel Properties"})

    ro.append({"key": "feed_mass_flow", "label": "Total Feed Mass Flow", "unit": "kg/s", "section": "Feed Conditions"})
    for ion in preset["solute_list"]:
        frac_key = f"feed_frac_{ion}"
        config[frac_key] = feed_fracs[ion]
        ro.append({"key": frac_key, "label": f"  {ion} Mass Fraction", "section": "Feed Conditions"})
    ro.append({"key": "feed_pressure", "label": "Feed Pressure", "unit": "Pa", "section": "Feed Conditions"})
    ro.append({"key": "feed_temperature", "label": "Feed Temperature", "unit": "K", "section": "Feed Conditions"})
    ro.append({"key": "permeate_pressure", "label": "Permeate Pressure", "unit": "Pa", "section": "Feed Conditions"})

    return config


# ============================================================================
# Section 3c: ED Configuration
# ============================================================================

ED_ION_PRESETS = {
    1: {
        "name": "Simple NaCl",
        "solute_list": ["Na_+", "Cl_-"],
        "mw_data": {"H2O": 18e-3, "Na_+": 23e-3, "Cl_-": 35.5e-3},
        "elec_mobility_data": {("Liq", "Na_+"): 5.19e-8, ("Liq", "Cl_-"): 7.92e-8},
        "charge": {"Na_+": 1, "Cl_-": -1},
        "default_feed_mol": {"H2O": 2.40e-1, "Na_+": 7.38e-4, "Cl_-": 7.38e-4},
        "default_membrane_props": {
            "solute_diffusivity_membrane": {
                ("cem", "Na_+"): 1.8e-10, ("aem", "Na_+"): 1.25e-10,
                ("cem", "Cl_-"): 1.8e-10, ("aem", "Cl_-"): 1.25e-10,
            },
            "ion_trans_number_membrane": {
                ("cem", "Na_+"): 1, ("aem", "Na_+"): 0,
                ("cem", "Cl_-"): 0, ("aem", "Cl_-"): 1,
            },
        },
    },
}


def configure_ed():
    print_header("Electrodialysis (ED) Configuration")
    config = {"_review_order": []}

    # Step 0: Dimension Selection
    print("\n-- Step 0: Model Dimension --")
    dim_opts = {1: "0D — Lumped (fast, uniform properties)", 2: "1D — Spatial (discretized along channel length)"}
    dim_choice = get_choice("Select model dimension", dim_opts, default_key=1)
    config["ed_dimension"] = dim_choice  # 1 = 0D, 2 = 1D
    config["model_type"] = "ed" if dim_choice == 1 else "ed_1d"

    if dim_choice == 2:
        print("\n  1D-specific settings:")
        config["finite_elements"] = get_int("Number of finite elements along channel length", default=20, min_val=1,
            hint="More elements = more accurate but slower. Typical: 10 to 40")
        config["has_Nernst_diffusion_layer"] = get_bool(
            "Model concentration-polarization (Nernst diffusion layer)?", default=False)
        config["has_nonohmic_potential_membrane"] = get_bool(
            "Model non-ohmic potential across membranes?", default=False)

    # Step 1: Ion Selection
    print("\n-- Step 1: Ion Selection --")
    ion_opts = {k: v["name"] for k, v in ED_ION_PRESETS.items()}
    ion_choice = get_choice("Select ion preset", ion_opts, default_key=1)
    preset = ED_ION_PRESETS[ion_choice]
    config["ion_preset"] = ion_choice
    config["solute_list"] = preset["solute_list"]
    config["mw_data"] = preset["mw_data"]
    config["elec_mobility_data"] = preset["elec_mobility_data"]
    config["charge"] = preset["charge"]

    # Step 2: Operation Mode
    print("\n-- Step 2: Operation Mode --")
    op_opts = {1: "Constant Voltage", 2: "Constant Current"}
    config["operation_mode"] = get_choice("Select operation mode", op_opts, default_key=1)

    # Step 3: Cell Geometry
    print("\n-- Step 3: Cell Geometry --")
    config["cell_pair_num"] = get_int("Number of cell pairs", default=10, min_val=1,
        hint="Typical: 5 to 200")
    config["cell_width"] = get_float("Cell width (m)", default=0.1, allow_negative=False,
        hint="Typical: 0.05 to 0.5 m",
        warn_range=(0.01, 2))
    config["cell_length"] = get_float("Cell length (m)", default=0.79, allow_negative=False,
        hint="Typical: 0.1 to 2 m",
        warn_range=(0.01, 10))
    config["channel_height"] = get_float("Channel height (m)", default=2.7e-4, allow_negative=False,
        hint="Typical: 1e-4 to 1e-3 m (0.1 to 1 mm). e.g. 2.7e-4 = 0.27 mm",
        warn_range=(1e-5, 0.01))
    config["spacer_porosity"] = get_float("Spacer porosity (0-1)", default=1.0, allow_negative=False,
        hint="1.0 = no spacer. Typical: 0.7 to 1.0",
        warn_range=(0.01, 1.0))

    # Step 4: Membrane Properties
    print("\n-- Step 4: Membrane Properties --")
    config["membrane_thickness_cem"] = get_float("CEM membrane thickness (m)", default=1.3e-4, allow_negative=False,
        hint="CEM = cation exchange membrane. Typical: 1e-4 to 5e-4 m. e.g. 1.3e-4",
        warn_range=(1e-5, 1e-2))
    config["membrane_thickness_aem"] = get_float("AEM membrane thickness (m)", default=1.3e-4, allow_negative=False,
        hint="AEM = anion exchange membrane. Typical: 1e-4 to 5e-4 m. e.g. 1.3e-4",
        warn_range=(1e-5, 1e-2))
    config["areal_resistance_cem"] = get_float("CEM areal resistance (ohm*m^2)", default=1.89e-4, allow_negative=False,
        hint="Typical: 1e-4 to 5e-4. Use scientific notation, e.g. 1.89e-4",
        warn_range=(1e-6, 1e-2))
    config["areal_resistance_aem"] = get_float("AEM areal resistance (ohm*m^2)", default=1.77e-4, allow_negative=False,
        hint="Typical: 1e-4 to 5e-4. Use scientific notation, e.g. 1.77e-4",
        warn_range=(1e-6, 1e-2))
    config["water_trans_num_cem"] = get_float("CEM water transference number", default=5.8, allow_negative=False,
        hint="Dimensionless. Typical: 3 to 10",
        warn_range=(0.1, 50))
    config["water_trans_num_aem"] = get_float("AEM water transference number", default=4.3, allow_negative=False,
        hint="Dimensionless. Typical: 3 to 10",
        warn_range=(0.1, 50))
    config["water_perm_cem"] = get_float("CEM water permeability (m/(s*Pa))", default=2.16e-14, allow_negative=False,
        hint="Typical: 1e-14 to 1e-13. Use scientific notation, e.g. 2.16e-14",
        warn_range=(1e-16, 1e-10))
    config["water_perm_aem"] = get_float("AEM water permeability (m/(s*Pa))", default=1.75e-14, allow_negative=False,
        hint="Typical: 1e-14 to 1e-13. Use scientific notation, e.g. 1.75e-14",
        warn_range=(1e-16, 1e-10))

    # Store default membrane transport properties from preset
    config["solute_diff_membrane"] = preset["default_membrane_props"]["solute_diffusivity_membrane"]
    config["ion_trans_num_membrane"] = preset["default_membrane_props"]["ion_trans_number_membrane"]

    # Step 5: Electrical Parameters
    print("\n-- Step 5: Electrical Parameters --")
    if config["operation_mode"] == 1:
        config["voltage"] = get_float("Stack voltage (V)", default=0.5, allow_negative=False,
            hint="Typical: 0.1 to 5 V per cell pair",
            warn_range=(0.01, 100))
    else:
        config["current"] = get_float("Stack current (A)", default=8.0, allow_negative=False,
            hint="Typical: 1 to 50 A",
            warn_range=(0.01, 500))
    config["electrodes_resistance"] = get_float("Electrodes resistance (ohm*m^2)", default=0.0,
        hint="0 = ideal electrodes. Typical: 0 to 0.01")
    config["current_utilization"] = get_float("Current utilization (0-1)", default=1.0, allow_negative=False,
        hint="1.0 = 100% utilization. Typical: 0.8 to 1.0",
        warn_range=(0.0, 1.0))

    # Step 6: Feed Conditions (Diluate)
    print("\n-- Step 6: Diluate Feed Conditions --")
    default_mol = preset["default_feed_mol"]
    config["dil_h2o"] = get_float("Diluate H2O flow (mol/s)", default=default_mol["H2O"], allow_negative=False,
        hint="In moles/second. 0.24 mol/s ~ 4.3 g/s of water")
    dil_ions = {}
    for ion in preset["solute_list"]:
        dil_ions[ion] = get_float(f"Diluate {ion} flow (mol/s)", default=default_mol[ion], allow_negative=False)
    config["dil_ions"] = dil_ions
    config["dil_pressure"] = get_float("Diluate pressure (Pa)", default=101325, allow_negative=False,
        hint="101325 Pa = 1 atm. Typical: 101325",
        warn_range=(1e4, 5e7))
    config["dil_temperature"] = get_float("Diluate temperature (K)", default=298.15, allow_negative=False,
        hint="K = Celsius + 273.15. e.g. 298.15 = 25 C",
        warn_range=(273.15, 373.15))

    # Step 7: Feed Conditions (Concentrate)
    print("\n-- Step 7: Concentrate Feed Conditions --")
    use_same = get_bool("Use same conditions as diluate?", default=True)
    if use_same:
        config["conc_h2o"] = config["dil_h2o"]
        config["conc_ions"] = dict(dil_ions)
        config["conc_pressure"] = config["dil_pressure"]
        config["conc_temperature"] = config["dil_temperature"]
    else:
        config["conc_h2o"] = get_float("Concentrate H2O flow (mol/s)", default=default_mol["H2O"], allow_negative=False)
        conc_ions = {}
        for ion in preset["solute_list"]:
            conc_ions[ion] = get_float(f"Concentrate {ion} flow (mol/s)", default=default_mol[ion], allow_negative=False)
        config["conc_ions"] = conc_ions
        config["conc_pressure"] = get_float("Concentrate pressure (Pa)", default=101325, allow_negative=False,
            hint="101325 Pa = 1 atm",
            warn_range=(1e4, 5e7))
        config["conc_temperature"] = get_float("Concentrate temperature (K)", default=298.15, allow_negative=False,
            hint="K = Celsius + 273.15. e.g. 298.15 = 25 C",
            warn_range=(273.15, 373.15))

    # Build review order
    ro = config["_review_order"]
    dim_display = {1: "0D (Lumped)", 2: "1D (Spatial)"}
    op_display = {1: "Constant Voltage", 2: "Constant Current"}

    ro.append({"key": "ed_dimension", "label": "Model Dimension", "section": "Model Configuration",
               "display_fn": lambda v: dim_display.get(v, str(v))})
    if dim_choice == 2:
        ro.append({"key": "finite_elements", "label": "Finite Elements", "section": "Model Configuration", "edit_type": "int"})
        ro.append({"key": "has_Nernst_diffusion_layer", "label": "Nernst Diffusion Layer", "section": "Model Configuration",
                   "edit_type": "bool"})
        ro.append({"key": "has_nonohmic_potential_membrane", "label": "Non-Ohmic Membrane Potential", "section": "Model Configuration",
                   "edit_type": "bool"})
    ro.append({"key": "operation_mode", "label": "Operation Mode", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": op_opts,
               "display_fn": lambda v: op_display.get(v, str(v))})

    ro.append({"key": "cell_pair_num", "label": "Number of Cell Pairs", "section": "Cell Geometry", "edit_type": "int"})
    ro.append({"key": "cell_width", "label": "Cell Width", "unit": "m", "section": "Cell Geometry"})
    ro.append({"key": "cell_length", "label": "Cell Length", "unit": "m", "section": "Cell Geometry"})
    ro.append({"key": "channel_height", "label": "Channel Height", "unit": "m", "section": "Cell Geometry"})
    ro.append({"key": "spacer_porosity", "label": "Spacer Porosity", "section": "Cell Geometry"})

    ro.append({"key": "membrane_thickness_cem", "label": "CEM Thickness", "unit": "m", "section": "Membrane Properties"})
    ro.append({"key": "membrane_thickness_aem", "label": "AEM Thickness", "unit": "m", "section": "Membrane Properties"})
    ro.append({"key": "areal_resistance_cem", "label": "CEM Areal Resistance", "unit": "ohm*m^2", "section": "Membrane Properties"})
    ro.append({"key": "areal_resistance_aem", "label": "AEM Areal Resistance", "unit": "ohm*m^2", "section": "Membrane Properties"})
    ro.append({"key": "water_trans_num_cem", "label": "CEM Water Trans. Number", "section": "Membrane Properties"})
    ro.append({"key": "water_trans_num_aem", "label": "AEM Water Trans. Number", "section": "Membrane Properties"})
    ro.append({"key": "water_perm_cem", "label": "CEM Water Permeability", "unit": "m/(s*Pa)", "section": "Membrane Properties"})
    ro.append({"key": "water_perm_aem", "label": "AEM Water Permeability", "unit": "m/(s*Pa)", "section": "Membrane Properties"})

    if config["operation_mode"] == 1:
        ro.append({"key": "voltage", "label": "Stack Voltage", "unit": "V", "section": "Electrical Parameters"})
    else:
        ro.append({"key": "current", "label": "Stack Current", "unit": "A", "section": "Electrical Parameters"})
    ro.append({"key": "electrodes_resistance", "label": "Electrodes Resistance", "unit": "ohm*m^2", "section": "Electrical Parameters"})
    ro.append({"key": "current_utilization", "label": "Current Utilization", "section": "Electrical Parameters"})

    ro.append({"key": "dil_h2o", "label": "Diluate H2O Flow", "unit": "mol/s", "section": "Diluate Feed"})
    for ion in preset["solute_list"]:
        dil_key = f"dil_{ion}"
        config[dil_key] = dil_ions[ion]
        ro.append({"key": dil_key, "label": f"Diluate {ion} Flow", "unit": "mol/s", "section": "Diluate Feed"})
    ro.append({"key": "dil_pressure", "label": "Diluate Pressure", "unit": "Pa", "section": "Diluate Feed"})
    ro.append({"key": "dil_temperature", "label": "Diluate Temperature", "unit": "K", "section": "Diluate Feed"})

    ro.append({"key": "conc_h2o", "label": "Concentrate H2O Flow", "unit": "mol/s", "section": "Concentrate Feed"})
    for ion in preset["solute_list"]:
        conc_key = f"conc_{ion}"
        config[conc_key] = config["conc_ions"][ion]
        ro.append({"key": conc_key, "label": f"Concentrate {ion} Flow", "unit": "mol/s", "section": "Concentrate Feed"})
    ro.append({"key": "conc_pressure", "label": "Concentrate Pressure", "unit": "Pa", "section": "Concentrate Feed"})
    ro.append({"key": "conc_temperature", "label": "Concentrate Temperature", "unit": "K", "section": "Concentrate Feed"})

    return config


# ============================================================================
# Section 3d: MD Configuration
# ============================================================================

def configure_md():
    print_header("Membrane Distillation (MD 0D) Configuration")
    config = {"model_type": "md", "_review_order": []}

    # Step 1: MD Type
    print("\n-- Step 1: MD Configuration Type --")
    md_opts = {1: "DCMD (Direct Contact)", 2: "VMD (Vacuum)", 3: "GMD (Conductive Gap)", 4: "AGMD (Air Gap)"}
    config["md_type"] = get_choice("Select MD type", md_opts, default_key=1)

    # Step 2: Membrane Properties
    print("\n-- Step 2: Membrane Properties --")
    config["area"] = get_float("Membrane area (m^2)", default=12.0, allow_negative=False,
        hint="Typical: 1 to 50 m^2",
        warn_range=(0.01, 1000))
    config["permeability_coef"] = get_float("Permeability coefficient (kg/(s*m*Pa))", default=1e-10, allow_negative=False,
        hint="Typical: 1e-11 to 1e-9. Use scientific notation, e.g. 1e-10",
        warn_range=(1e-12, 1e-8))
    config["membrane_thickness"] = get_float("Membrane thickness (m)", default=1e-4, allow_negative=False,
        hint="Typical: 5e-5 to 5e-4 m (0.05 to 0.5 mm). e.g. 1e-4 = 0.1 mm",
        warn_range=(1e-6, 1e-2))
    config["membrane_thermal_conductivity"] = get_float("Thermal conductivity (W/(m*K))", default=0.2, allow_negative=False,
        hint="Typical for PTFE/PVDF: 0.1 to 0.5 W/(m*K)",
        warn_range=(0.01, 10))

    # Step 3: Gap Properties (GMD/AGMD only)
    if config["md_type"] in (3, 4):
        print("\n-- Step 3: Gap Properties --")
        config["gap_thermal_conductivity"] = get_float("Gap thermal conductivity (W/(m*K))", default=0.06, allow_negative=False,
            hint="Typical for air: 0.02 to 0.1 W/(m*K)",
            warn_range=(0.001, 1))
        config["gap_thickness"] = get_float("Gap thickness (m)", default=1e-4, allow_negative=False,
            hint="Typical: 1e-4 to 5e-3 m (0.1 to 5 mm). e.g. 1e-4 = 0.1 mm",
            warn_range=(1e-5, 0.1))

    # Step 4: Hot Channel Feed
    print("\n-- Step 4: Hot Channel Feed Conditions --")
    config["hot_h2o"] = get_float("Hot channel H2O flow (kg/s)", default=0.965, allow_negative=False,
        hint="Typical: 0.1 to 5 kg/s",
        warn_range=(0.001, 100))
    config["hot_tds"] = get_float("Hot channel TDS flow (kg/s)", default=0.035, allow_negative=False,
        hint="TDS = total dissolved solids. Seawater ~3.5%. e.g. 0.035",
        warn_range=(0.0001, 10))
    config["hot_pressure"] = get_float("Hot channel pressure (Pa)", default=7e5, allow_negative=False,
        hint="1 bar = 100000 Pa. Typical: 1e5 to 1e6 Pa (1-10 bar)",
        warn_range=(1e4, 1e7))
    config["hot_temperature"] = get_float("Hot channel temperature (K)", default=363.15, allow_negative=False,
        hint="K = Celsius + 273.15. Typical: 333-363 K (60-90 C). e.g. 363.15 = 90 C",
        warn_range=(273.15, 393.15))

    # Step 5: Cold Channel Feed
    print("\n-- Step 5: Cold Channel Feed Conditions --")
    config["cold_h2o"] = get_float("Cold channel H2O flow (kg/s)", default=1.0, allow_negative=False,
        hint="Typical: 0.1 to 5 kg/s",
        warn_range=(0.001, 100))
    config["cold_pressure"] = get_float("Cold channel pressure (Pa)", default=101325, allow_negative=False,
        hint="101325 Pa = 1 atm. Typical: 101325",
        warn_range=(1e4, 1e7))
    config["cold_temperature"] = get_float("Cold channel temperature (K)", default=298.15, allow_negative=False,
        hint="K = Celsius + 273.15. Typical: 288-303 K (15-30 C). e.g. 298.15 = 25 C",
        warn_range=(273.15, 373.15))

    # Step 6: Channel Parameters
    print("\n-- Step 6: Channel Parameters --")
    config["hot_deltaP"] = get_float("Hot channel pressure drop (Pa)", default=0.0,
        hint="0 = no pressure loss. Negative = pressure drop. Typical: -1e5 to 0")
    config["cold_deltaP"] = get_float("Cold channel pressure drop (Pa)", default=0.0,
        hint="0 = no pressure loss. Negative = pressure drop. Typical: -1e5 to 0")
    config["hot_h_conv"] = get_float("Hot channel convection coeff (W/(m^2*K))", default=2400.0, allow_negative=False,
        hint="Typical: 500 to 5000 W/(m^2*K)",
        warn_range=(10, 50000))
    config["cold_h_conv"] = get_float("Cold channel convection coeff (W/(m^2*K))", default=2400.0, allow_negative=False,
        hint="Typical: 500 to 5000 W/(m^2*K)",
        warn_range=(10, 50000))

    # Build review order
    ro = config["_review_order"]
    md_display = {1: "DCMD", 2: "VMD", 3: "GMD", 4: "AGMD"}

    ro.append({"key": "md_type", "label": "MD Configuration Type", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": md_opts,
               "display_fn": lambda v: md_display.get(v, str(v))})

    ro.append({"key": "area", "label": "Membrane Area", "unit": "m^2", "section": "Membrane Properties"})
    ro.append({"key": "permeability_coef", "label": "Permeability Coefficient", "unit": "kg/(s*m*Pa)", "section": "Membrane Properties"})
    ro.append({"key": "membrane_thickness", "label": "Membrane Thickness", "unit": "m", "section": "Membrane Properties"})
    ro.append({"key": "membrane_thermal_conductivity", "label": "Thermal Conductivity", "unit": "W/(m*K)", "section": "Membrane Properties"})

    if config["md_type"] in (3, 4):
        ro.append({"key": "gap_thermal_conductivity", "label": "Gap Thermal Conductivity", "unit": "W/(m*K)", "section": "Gap Properties"})
        ro.append({"key": "gap_thickness", "label": "Gap Thickness", "unit": "m", "section": "Gap Properties"})

    ro.append({"key": "hot_h2o", "label": "Hot Channel H2O Flow", "unit": "kg/s", "section": "Hot Channel Feed"})
    ro.append({"key": "hot_tds", "label": "Hot Channel TDS Flow", "unit": "kg/s", "section": "Hot Channel Feed"})
    ro.append({"key": "hot_pressure", "label": "Hot Channel Pressure", "unit": "Pa", "section": "Hot Channel Feed"})
    ro.append({"key": "hot_temperature", "label": "Hot Channel Temperature", "unit": "K", "section": "Hot Channel Feed"})

    ro.append({"key": "cold_h2o", "label": "Cold Channel H2O Flow", "unit": "kg/s", "section": "Cold Channel Feed"})
    ro.append({"key": "cold_pressure", "label": "Cold Channel Pressure", "unit": "Pa", "section": "Cold Channel Feed"})
    ro.append({"key": "cold_temperature", "label": "Cold Channel Temperature", "unit": "K", "section": "Cold Channel Feed"})

    ro.append({"key": "hot_deltaP", "label": "Hot Channel Pressure Drop", "unit": "Pa", "section": "Channel Parameters"})
    ro.append({"key": "cold_deltaP", "label": "Cold Channel Pressure Drop", "unit": "Pa", "section": "Channel Parameters"})
    ro.append({"key": "hot_h_conv", "label": "Hot Channel h_conv", "unit": "W/(m^2*K)", "section": "Channel Parameters"})
    ro.append({"key": "cold_h_conv", "label": "Cold Channel h_conv", "unit": "W/(m^2*K)", "section": "Channel Parameters"})

    return config


# ============================================================================
# Section 3e: Zero-Order Configuration
# ============================================================================

ZO_SOLUTE_PRESETS = {
    "microfiltration": {
        "default_solutes": ["toc", "tss"],
        "default_flows": {"H2O": 10000, "toc": 2, "tss": 3},
    },
    "ultra_filtration": {
        "default_solutes": ["toc", "tss"],
        "default_flows": {"H2O": 10000, "toc": 2, "tss": 3},
    },
    "nanofiltration": {
        "default_solutes": ["sulfur", "toc", "tss"],
        "default_flows": {"H2O": 10000, "sulfur": 1, "toc": 2, "tss": 3},
    },
}


def configure_zero_order():
    print_header("Zero-Order Membrane Model Configuration")
    config = {"model_type": "zero_order", "_review_order": []}

    # Step 1: Membrane Type
    print("\n-- Step 1: Membrane Type --")
    zo_opts = {1: "Microfiltration (MF)", 2: "Ultrafiltration (UF)", 3: "Nanofiltration (NF)"}
    config["zo_type"] = get_choice("Select membrane type", zo_opts, default_key=1)
    zo_tech_map = {1: "microfiltration", 2: "ultra_filtration", 3: "nanofiltration"}
    config["technology"] = zo_tech_map[config["zo_type"]]
    preset = ZO_SOLUTE_PRESETS[config["technology"]]

    # Step 2: Solutes
    print("\n-- Step 2: Solutes --")
    print(f"  Default solutes for {config['technology']}: {', '.join(preset['default_solutes'])}")
    use_default = get_bool("Use default solutes?", default=True)
    if use_default:
        config["solute_list"] = list(preset["default_solutes"])
    else:
        solutes_input = input("  Enter solute names (comma-separated): ").strip()
        config["solute_list"] = [s.strip() for s in solutes_input.split(",") if s.strip()]
        if not config["solute_list"]:
            config["solute_list"] = list(preset["default_solutes"])
            print(f"  No solutes entered, using defaults: {config['solute_list']}")

    # Step 3: Feed Conditions
    print("\n-- Step 3: Feed Conditions --")
    default_flows = preset["default_flows"]
    config["feed_h2o"] = get_float("H2O feed flow (kg/s)", default=default_flows.get("H2O", 10000), allow_negative=False,
        hint="Typical for municipal water: 1000 to 50000 kg/s")
    feed_solutes = {}
    for sol in config["solute_list"]:
        feed_solutes[sol] = get_float(f"{sol} feed flow (kg/s)", default=default_flows.get(sol, 1.0), allow_negative=False,
            hint=f"Mass flow of {sol} in kg/s. Typical: 0.01 to 100")
    config["feed_solutes"] = feed_solutes

    # Step 4: Override Parameters
    print("\n-- Step 4: Parameter Overrides (optional) --")
    print("  Parameters will be loaded from the WaterTAP database by default.")
    config["override_recovery"] = get_bool("Override water recovery fraction?", default=False)
    if config["override_recovery"]:
        config["recovery_frac"] = get_float("Water recovery fraction (0-1)", default=0.85, allow_negative=False,
            hint="0 = no recovery, 1 = 100% recovery. Typical: 0.7 to 0.95",
            warn_range=(0.0, 1.0))

    config["override_removal"] = get_bool("Override solute removal fractions?", default=False)
    removal_fracs = {}
    if config["override_removal"]:
        for sol in config["solute_list"]:
            removal_fracs[sol] = get_float(f"Removal fraction for {sol} (0-1)", default=0.9, allow_negative=False,
                hint="0 = no removal, 1 = 100% removal. Typical: 0.8 to 0.99",
                warn_range=(0.0, 1.0))
    config["removal_fracs"] = removal_fracs

    # Build review order
    ro = config["_review_order"]
    zo_display = {1: "Microfiltration (MF)", 2: "Ultrafiltration (UF)", 3: "Nanofiltration (NF)"}

    ro.append({"key": "zo_type", "label": "Membrane Type", "section": "Model Configuration",
               "edit_type": "choice", "edit_options": zo_opts,
               "display_fn": lambda v: zo_display.get(v, str(v))})

    ro.append({"key": "feed_h2o", "label": "H2O Feed Flow", "unit": "kg/s", "section": "Feed Conditions"})
    for sol in config["solute_list"]:
        sol_key = f"feed_{sol}"
        config[sol_key] = feed_solutes[sol]
        ro.append({"key": sol_key, "label": f"{sol} Feed Flow", "unit": "kg/s", "section": "Feed Conditions"})

    if config["override_recovery"]:
        ro.append({"key": "recovery_frac", "label": "Water Recovery Fraction", "section": "Parameter Overrides"})
    if config["override_removal"]:
        for sol in config["solute_list"]:
            rm_key = f"removal_{sol}"
            config[rm_key] = removal_fracs[sol]
            ro.append({"key": rm_key, "label": f"Removal Fraction ({sol})", "section": "Parameter Overrides"})

    return config


# ============================================================================
# Section 4: Model Runners
# ============================================================================

def run_ro(config):
    print("\n  Loading WaterTAP modules...")
    from pyomo.environ import ConcreteModel, value
    from idaes.core import FlowsheetBlock
    from idaes.core.util.model_statistics import degrees_of_freedom
    import idaes.core.util.scaling as iscale
    from watertap.core.solvers import get_solver
    from watertap.property_models.NaCl_prop_pack import NaClParameterBlock
    from watertap.unit_models.reverse_osmosis_0D import (
        ReverseOsmosis0D,
        ConcentrationPolarizationType,
        MassTransferCoefficient,
        PressureChangeType,
    )
    from watertap.core.membrane_channel_base import TransportModel, ModuleType

    # Map config choices to enums
    tm_map = {1: TransportModel.SD, 2: TransportModel.SKK}
    cp_map = {1: ConcentrationPolarizationType.none, 2: ConcentrationPolarizationType.fixed,
              3: ConcentrationPolarizationType.calculated}
    mtc_map = {1: MassTransferCoefficient.none, 2: MassTransferCoefficient.fixed,
               3: MassTransferCoefficient.calculated}
    pc_map = {1: PressureChangeType.fixed_per_stage, 2: PressureChangeType.fixed_per_unit_length,
              3: PressureChangeType.calculated}
    mod_map = {1: ModuleType.flat_sheet, 2: ModuleType.spiral_wound}

    print("  Building model...")
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.properties = NaClParameterBlock()

    unit_config = {
        "property_package": m.fs.properties,
        "has_pressure_change": config["has_pressure_change"],
        "concentration_polarization_type": cp_map[config["cp_type"]],
        "mass_transfer_coefficient": mtc_map[config["mtc_type"]],
        "transport_model": tm_map[config["transport_model"]],
        "module_type": mod_map[config["module_type"]],
        "pressure_change_type": pc_map[config["pressure_change_type"]],
        "has_full_reporting": True,
    }
    m.fs.unit = ReverseOsmosis0D(**unit_config)

    # Fix feed
    m.fs.unit.inlet.flow_mass_phase_comp[0, "Liq", "H2O"].fix(config["feed_h2o"])
    m.fs.unit.inlet.flow_mass_phase_comp[0, "Liq", "NaCl"].fix(config["feed_nacl"])
    m.fs.unit.inlet.pressure[0].fix(config["feed_pressure"])
    m.fs.unit.inlet.temperature[0].fix(config["feed_temperature"])

    # Fix membrane
    m.fs.unit.A_comp.fix(config["A_comp"])
    m.fs.unit.B_comp.fix(config["B_comp"])
    m.fs.unit.area.fix(config["area"])
    m.fs.unit.permeate.pressure[0].fix(config["permeate_pressure"])

    # Conditional fixes
    if config["has_pressure_change"] and config["pressure_change_type"] == 1:
        m.fs.unit.deltaP.fix(config["deltaP"])
    if config["has_pressure_change"] and config["pressure_change_type"] == 2:
        m.fs.unit.feed_side.dP_dx.fix(config["dP_dx"])

    if config["cp_type"] == 2:  # fixed
        m.fs.unit.feed_side.cp_modulus.fix(config["cp_modulus"])

    if config["mtc_type"] == 2:  # fixed
        m.fs.unit.feed_side.K[0, 0.0, "NaCl"].fix(config["kf_inlet"])
        m.fs.unit.feed_side.K[0, 1.0, "NaCl"].fix(config["kf_outlet"])

    needs_geometry = (config["mtc_type"] == 3 or
                      (config["has_pressure_change"] and config["pressure_change_type"] == 3))
    if needs_geometry:
        m.fs.unit.feed_side.channel_height.fix(config["channel_height"])
        m.fs.unit.feed_side.spacer_porosity.fix(config["spacer_porosity"])
        m.fs.unit.length.fix(config["length"])

    if config["transport_model"] == 2:  # SKK
        m.fs.unit.reflect_coeff.fix(config["reflect_coeff"])

    # Scaling
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1, index=("Liq", "H2O"))
    m.fs.properties.set_default_scaling("flow_mass_phase_comp", 1e2, index=("Liq", "NaCl"))
    iscale.calculate_scaling_factors(m.fs.unit)

    dof = degrees_of_freedom(m)
    print(f"  Degrees of freedom: {dof}")
    if dof != 0:
        print(f"  WARNING: DOF is {dof}, not 0. Model may not solve correctly.")

    print("  Initializing model...")
    m.fs.unit.initialize()

    print("  Solving...")
    solver = get_solver()
    results = solver.solve(m)

    print_header("RESULTS - Reverse Osmosis")
    m.fs.unit.report()

    print("\n--- Key Performance Metrics ---")
    try:
        print(f"  Water Recovery (vol): {value(m.fs.unit.recovery_vol_phase[0, 'Liq']):.4f}")
        print(f"  Salt Rejection:       {value(m.fs.unit.rejection_phase_comp[0, 'Liq', 'NaCl']):.4f}")
    except Exception:
        pass


def run_nf_dspmde(config):
    print("\n  Loading WaterTAP modules...")
    from pyomo.environ import ConcreteModel, units as pyunits, value
    from idaes.core import FlowsheetBlock
    from idaes.core.util.model_statistics import degrees_of_freedom
    import idaes.core.util.scaling as iscale
    from watertap.core.solvers import get_solver
    from watertap.property_models.multicomp_aq_sol_prop_pack import (
        MCASParameterBlock, ActivityCoefficientModel, DensityCalculation,
    )
    from watertap.unit_models.nanofiltration_DSPMDE_0D import NanofiltrationDSPMDE0D

    preset = NF_ION_PRESETS[config["ion_preset"]]

    print("  Building model...")
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.properties = MCASParameterBlock(
        solute_list=config["solute_list"],
        diffusivity_data=config["diffusivity_data"],
        mw_data=config["mw_data"],
        stokes_radius_data=config["stokes_radius_data"],
        charge=config["charge"],
        activity_coefficient_model=ActivityCoefficientModel.davies,
        density_calculation=DensityCalculation.constant,
    )

    mtc_map = {}
    cp_map = {}
    # Lazy import of the NF-specific enums
    from watertap.unit_models.nanofiltration_DSPMDE_0D import (
        MassTransferCoefficient as NF_MTC,
        ConcentrationPolarizationType as NF_CP,
    )
    mtc_map = {1: NF_MTC.none, 2: NF_MTC.fixed, 3: NF_MTC.spiral_wound}
    cp_map = {1: NF_CP.none, 2: NF_CP.calculated}

    m.fs.unit = NanofiltrationDSPMDE0D(
        property_package=m.fs.properties,
        mass_transfer_coefficient=mtc_map[config["mtc_type"]],
        concentration_polarization_type=cp_map[config["cp_type"]],
    )

    # Fix feed molar flows
    mass_flow = config["feed_mass_flow"]
    feed_fracs = {}
    for ion in config["solute_list"]:
        frac_key = f"feed_frac_{ion}"
        feed_fracs[ion] = config[frac_key]

    for ion in config["solute_list"]:
        mw = config["mw_data"][ion]
        mol_flow = feed_fracs[ion] * mass_flow / mw
        m.fs.unit.inlet.flow_mol_phase_comp[0, "Liq", ion].fix(mol_flow)

    h2o_frac = 1 - sum(feed_fracs.values())
    h2o_mol = h2o_frac * mass_flow / config["mw_data"]["H2O"]
    m.fs.unit.inlet.flow_mol_phase_comp[0, "Liq", "H2O"].fix(h2o_mol)

    # Electroneutrality adjustment
    m.fs.unit.feed_side.properties_in[0].assert_electroneutrality(
        defined_state=True,
        adjust_by_ion=config["adjust_ion"],
        get_property="mass_frac_phase_comp",
    )

    m.fs.unit.inlet.temperature[0].fix(config["feed_temperature"])
    m.fs.unit.inlet.pressure[0].fix(config["feed_pressure"])

    # Fix membrane properties
    m.fs.unit.radius_pore.fix(config["radius_pore"])
    m.fs.unit.membrane_thickness_effective.fix(config["membrane_thickness"])
    m.fs.unit.membrane_charge_density.fix(config["membrane_charge_density"])
    m.fs.unit.dielectric_constant_pore.fix(config["dielectric_constant_pore"])
    m.fs.unit.mixed_permeate[0].pressure.fix(config["permeate_pressure"])

    m.fs.unit.spacer_porosity.fix(config["spacer_porosity"])
    m.fs.unit.channel_height.fix(config["channel_height"])
    m.fs.unit.velocity[0, 0].fix(config["velocity"])
    m.fs.unit.area.fix(config["area"])

    if config["mtc_type"] == 3:  # spiral_wound
        m.fs.unit.spacer_mixing_efficiency.fix()
        m.fs.unit.spacer_mixing_length.fix()

    # Scaling
    iscale.calculate_scaling_factors(m.fs.unit)

    dof = degrees_of_freedom(m)
    print(f"  Degrees of freedom: {dof}")
    if dof != 0:
        print(f"  WARNING: DOF is {dof}, not 0. Model may not solve correctly.")

    print("  Initializing model...")
    m.fs.unit.initialize()

    print("  Solving...")
    solver = get_solver()
    results = solver.solve(m)

    print_header("RESULTS - Nanofiltration DSPM-DE")
    m.fs.unit.report()


def run_ed(config):
    print("\n  Loading WaterTAP modules...")
    from pyomo.environ import ConcreteModel, value
    from idaes.core import FlowsheetBlock
    from idaes.core.util.model_statistics import degrees_of_freedom
    import idaes.core.util.scaling as iscale
    from watertap.core.solvers import get_solver
    from watertap.property_models.multicomp_aq_sol_prop_pack import MCASParameterBlock
    from watertap.unit_models.electrodialysis_0D import Electrodialysis0D

    preset = ED_ION_PRESETS[config["ion_preset"]]
    op_mode_str = "Constant_Voltage" if config["operation_mode"] == 1 else "Constant_Current"

    print("  Building model...")
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.properties = MCASParameterBlock(
        solute_list=preset["solute_list"],
        mw_data=preset["mw_data"],
        elec_mobility_data=preset["elec_mobility_data"],
        charge=preset["charge"],
    )

    m.fs.unit = Electrodialysis0D(
        property_package=m.fs.properties,
        operation_mode=op_mode_str,
    )

    # Cell geometry
    m.fs.unit.cell_pair_num.fix(config["cell_pair_num"])
    m.fs.unit.cell_width.fix(config["cell_width"])
    m.fs.unit.cell_length.fix(config["cell_length"])
    m.fs.unit.channel_height.fix(config["channel_height"])
    m.fs.unit.spacer_porosity.fix(config["spacer_porosity"])

    # Membrane properties
    m.fs.unit.membrane_thickness["cem"].fix(config["membrane_thickness_cem"])
    m.fs.unit.membrane_thickness["aem"].fix(config["membrane_thickness_aem"])
    m.fs.unit.membrane_areal_resistance["cem"].fix(config["areal_resistance_cem"])
    m.fs.unit.membrane_areal_resistance["aem"].fix(config["areal_resistance_aem"])
    m.fs.unit.water_trans_number_membrane["cem"].fix(config["water_trans_num_cem"])
    m.fs.unit.water_trans_number_membrane["aem"].fix(config["water_trans_num_aem"])
    m.fs.unit.water_permeability_membrane["cem"].fix(config["water_perm_cem"])
    m.fs.unit.water_permeability_membrane["aem"].fix(config["water_perm_aem"])

    # Ion-membrane transport properties from preset
    for (mem, ion), val in config["solute_diff_membrane"].items():
        m.fs.unit.solute_diffusivity_membrane[mem, ion].fix(val)
    for (mem, ion), val in config["ion_trans_num_membrane"].items():
        m.fs.unit.ion_trans_number_membrane[mem, ion].fix(val)

    # Electrical
    if config["operation_mode"] == 1:
        m.fs.unit.voltage.fix(config["voltage"])
    else:
        m.fs.unit.current.fix(config["current"])
    m.fs.unit.electrodes_resistance.fix(config["electrodes_resistance"])
    m.fs.unit.current_utilization.fix(config["current_utilization"])

    # Diluate feed
    m.fs.unit.inlet_diluate.pressure.fix(config["dil_pressure"])
    m.fs.unit.inlet_diluate.temperature.fix(config["dil_temperature"])
    m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(config["dil_h2o"])
    for ion in preset["solute_list"]:
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", ion].fix(config["dil_ions"][ion])

    # Concentrate feed
    m.fs.unit.inlet_concentrate.pressure.fix(config["conc_pressure"])
    m.fs.unit.inlet_concentrate.temperature.fix(config["conc_temperature"])
    m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(config["conc_h2o"])
    for ion in preset["solute_list"]:
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", ion].fix(config["conc_ions"][ion])

    # Scaling
    iscale.calculate_scaling_factors(m.fs.unit)

    dof = degrees_of_freedom(m)
    print(f"  Degrees of freedom: {dof}")
    if dof != 0:
        print(f"  WARNING: DOF is {dof}, not 0. Model may not solve correctly.")

    print("  Initializing model...")
    m.fs.unit.initialize()

    print("  Solving...")
    solver = get_solver()
    results = solver.solve(m)

    print_header("RESULTS - Electrodialysis (0D)")
    m.fs.unit.report()


def run_ed_1d(config):
    print("\n  Loading WaterTAP modules (1D ED)...")
    from pyomo.environ import ConcreteModel, value
    from idaes.core import FlowsheetBlock
    from idaes.core.util.model_statistics import degrees_of_freedom
    import idaes.core.util.scaling as iscale
    from watertap.core.solvers import get_solver
    from watertap.property_models.multicomp_aq_sol_prop_pack import MCASParameterBlock
    from watertap.unit_models.electrodialysis_1D import (
        Electrodialysis1D,
        ElectricalOperationMode,
        PressureDropMethod,
    )

    preset = ED_ION_PRESETS[config["ion_preset"]]
    op_mode = (ElectricalOperationMode.Constant_Voltage
               if config["operation_mode"] == 1
               else ElectricalOperationMode.Constant_Current)

    print("  Building 1D model...")
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.properties = MCASParameterBlock(
        solute_list=preset["solute_list"],
        mw_data=preset["mw_data"],
        elec_mobility_data=preset["elec_mobility_data"],
        charge=preset["charge"],
    )

    m.fs.unit = Electrodialysis1D(
        property_package=m.fs.properties,
        operation_mode=op_mode,
        finite_elements=config["finite_elements"],
        has_Nernst_diffusion_layer=config["has_Nernst_diffusion_layer"],
        has_nonohmic_potential_membrane=config["has_nonohmic_potential_membrane"],
        pressure_drop_method=PressureDropMethod.none,
    )

    # Cell geometry
    m.fs.unit.cell_pair_num.fix(config["cell_pair_num"])
    m.fs.unit.cell_width.fix(config["cell_width"])
    m.fs.unit.cell_length.fix(config["cell_length"])
    m.fs.unit.channel_height.fix(config["channel_height"])
    m.fs.unit.spacer_porosity.fix(config["spacer_porosity"])
    m.fs.unit.spacer_conductivity_coefficient.fix(1)

    # Membrane properties
    m.fs.unit.membrane_thickness["cem"].fix(config["membrane_thickness_cem"])
    m.fs.unit.membrane_thickness["aem"].fix(config["membrane_thickness_aem"])
    m.fs.unit.membrane_areal_resistance["cem"].fix(config["areal_resistance_cem"])
    m.fs.unit.membrane_areal_resistance["aem"].fix(config["areal_resistance_aem"])
    m.fs.unit.membrane_areal_resistance_coef["cem"].fix(0)
    m.fs.unit.membrane_areal_resistance_coef["aem"].fix(0)
    m.fs.unit.water_trans_number_membrane["cem"].fix(config["water_trans_num_cem"])
    m.fs.unit.water_trans_number_membrane["aem"].fix(config["water_trans_num_aem"])
    m.fs.unit.water_permeability_membrane["cem"].fix(config["water_perm_cem"])
    m.fs.unit.water_permeability_membrane["aem"].fix(config["water_perm_aem"])

    # Ion-membrane transport properties from preset
    for (mem, ion), val in config["solute_diff_membrane"].items():
        m.fs.unit.solute_diffusivity_membrane[mem, ion].fix(val)
    for (mem, ion), val in config["ion_trans_num_membrane"].items():
        m.fs.unit.ion_trans_number_membrane[mem, ion].fix(val)

    # Electrical
    if config["operation_mode"] == 1:
        m.fs.unit.voltage_applied.fix(config["voltage"])
    else:
        m.fs.unit.current_applied.fix(config["current"])
    m.fs.unit.electrodes_resistance.fix(config["electrodes_resistance"])
    m.fs.unit.current_utilization.fix(config["current_utilization"])

    # Diluate feed
    m.fs.unit.inlet_diluate.pressure.fix(config["dil_pressure"])
    m.fs.unit.inlet_diluate.temperature.fix(config["dil_temperature"])
    m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(config["dil_h2o"])
    for ion in preset["solute_list"]:
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", ion].fix(config["dil_ions"][ion])

    # Concentrate feed
    m.fs.unit.inlet_concentrate.pressure.fix(config["conc_pressure"])
    m.fs.unit.inlet_concentrate.temperature.fix(config["conc_temperature"])
    m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(config["conc_h2o"])
    for ion in preset["solute_list"]:
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", ion].fix(config["conc_ions"][ion])

    # Scaling
    iscale.calculate_scaling_factors(m.fs.unit)

    dof = degrees_of_freedom(m)
    print(f"  Degrees of freedom: {dof}")
    if dof != 0:
        print(f"  WARNING: DOF is {dof}, not 0. Model may not solve correctly.")

    print("  Initializing 1D model (this may take a moment)...")
    m.fs.unit.initialize()

    print("  Solving...")
    solver = get_solver()
    results = solver.solve(m)

    print_header("RESULTS - Electrodialysis (1D)")
    m.fs.unit.report()


def run_md(config):
    print("\n  Loading WaterTAP modules...")
    from pyomo.environ import ConcreteModel, value
    from idaes.core import FlowsheetBlock, FlowDirection
    from idaes.core.util.model_statistics import degrees_of_freedom
    import idaes.core.util.scaling as iscale
    from watertap.core.solvers import get_solver
    import watertap.property_models.seawater_prop_pack as props_sw
    import watertap.property_models.water_prop_pack as props_w
    from watertap.unit_models.MD.membrane_distillation_0D import MembraneDistillation0D
    from watertap.unit_models.MD.MD_channel_base import (
        ConcentrationPolarizationType as MD_CP,
        TemperaturePolarizationType,
        MassTransferCoefficient as MD_MTC,
        PressureChangeType as MD_PC,
    )
    from watertap.unit_models.MD.membrane_distillation_base import MDconfigurationType

    md_type_map = {1: MDconfigurationType.DCMD, 2: MDconfigurationType.VMD,
                   3: MDconfigurationType.GMD, 4: MDconfigurationType.AGMD}

    print("  Building model...")
    m = ConcreteModel()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.properties_hot_ch = props_sw.SeawaterParameterBlock()
    m.fs.properties_cold_ch = props_w.WaterParameterBlock()
    m.fs.properties_vapor = props_w.WaterParameterBlock()

    md_config = {
        "hot_ch": {
            "property_package": m.fs.properties_hot_ch,
            "property_package_vapor": m.fs.properties_vapor,
            "has_pressure_change": True,
            "temperature_polarization_type": TemperaturePolarizationType.fixed,
            "concentration_polarization_type": MD_CP.none,
            "mass_transfer_coefficient": MD_MTC.none,
            "pressure_change_type": MD_PC.fixed_per_stage,
            "flow_direction": FlowDirection.forward,
        },
        "cold_ch": {
            "property_package": m.fs.properties_cold_ch,
            "property_package_vapor": m.fs.properties_vapor,
            "has_pressure_change": True,
            "temperature_polarization_type": TemperaturePolarizationType.fixed,
            "mass_transfer_coefficient": MD_MTC.none,
            "concentration_polarization_type": MD_CP.none,
            "pressure_change_type": MD_PC.fixed_per_stage,
            "flow_direction": FlowDirection.backward,
        },
        "MD_configuration_Type": md_type_map[config["md_type"]],
    }

    m.fs.unit = MembraneDistillation0D(**md_config)

    # Hot channel feed
    m.fs.unit.hot_ch_inlet.flow_mass_phase_comp[0, "Liq", "H2O"].fix(config["hot_h2o"])
    m.fs.unit.hot_ch_inlet.flow_mass_phase_comp[0, "Liq", "TDS"].fix(config["hot_tds"])
    m.fs.unit.hot_ch_inlet.pressure[0].fix(config["hot_pressure"])
    m.fs.unit.hot_ch_inlet.temperature[0].fix(config["hot_temperature"])

    # Membrane properties
    m.fs.unit.area.fix(config["area"])
    m.fs.unit.permeability_coef.fix(config["permeability_coef"])
    m.fs.unit.membrane_thickness.fix(config["membrane_thickness"])
    m.fs.unit.membrane_thermal_conductivity.fix(config["membrane_thermal_conductivity"])

    # Cold channel feed
    m.fs.unit.cold_ch_inlet.flow_mass_phase_comp[0, "Liq", "H2O"].fix(config["cold_h2o"])
    m.fs.unit.cold_ch_inlet.pressure[0].fix(config["cold_pressure"])
    m.fs.unit.cold_ch_inlet.temperature[0].fix(config["cold_temperature"])

    # Channel pressure drops and convection
    m.fs.unit.hot_ch.deltaP.fix(config["hot_deltaP"])
    m.fs.unit.cold_ch.deltaP.fix(config["cold_deltaP"])
    m.fs.unit.hot_ch.h_conv.fix(config["hot_h_conv"])
    m.fs.unit.cold_ch.h_conv.fix(config["cold_h_conv"])

    # Scaling
    iscale.calculate_scaling_factors(m.fs.unit)

    dof = degrees_of_freedom(m)
    print(f"  Degrees of freedom: {dof}")
    if dof != 0:
        print(f"  WARNING: DOF is {dof}, not 0. Model may not solve correctly.")

    print("  Initializing model...")
    m.fs.unit.initialize()

    print("  Solving...")
    solver = get_solver()
    results = solver.solve(m)

    print_header("RESULTS - Membrane Distillation")
    m.fs.unit.report()


def run_zero_order(config):
    print("\n  Loading WaterTAP modules...")
    from pyomo.environ import ConcreteModel, value
    from idaes.core import FlowsheetBlock
    from idaes.core.util.model_statistics import degrees_of_freedom
    from watertap.core.solvers import get_solver
    from watertap.core.wt_database import Database
    from watertap.core.zero_order_properties import WaterParameterBlock
    from watertap.unit_models.zero_order import (
        NanofiltrationZO, UltraFiltrationZO, MicroFiltrationZO,
    )

    zo_class_map = {
        "microfiltration": MicroFiltrationZO,
        "ultra_filtration": UltraFiltrationZO,
        "nanofiltration": NanofiltrationZO,
    }

    print("  Building model...")
    m = ConcreteModel()
    m.db = Database()
    m.fs = FlowsheetBlock(dynamic=False)
    m.fs.params = WaterParameterBlock(solute_list=config["solute_list"])

    ZOClass = zo_class_map[config["technology"]]
    m.fs.unit = ZOClass(property_package=m.fs.params, database=m.db)

    # Fix feed
    m.fs.unit.inlet.flow_mass_comp[0, "H2O"].fix(config["feed_h2o"])
    for sol in config["solute_list"]:
        sol_key = f"feed_{sol}"
        m.fs.unit.inlet.flow_mass_comp[0, sol].fix(config[sol_key])

    # Load parameters from database
    m.fs.unit.load_parameters_from_database(use_default_removal=True)

    # Override if requested
    if config["override_recovery"]:
        m.fs.unit.recovery_frac_mass_H2O[0].fix(config["recovery_frac"])
    if config["override_removal"]:
        for sol in config["solute_list"]:
            rm_key = f"removal_{sol}"
            if rm_key in config:
                m.fs.unit.removal_frac_mass_comp[0, sol].fix(config[rm_key])

    dof = degrees_of_freedom(m)
    print(f"  Degrees of freedom: {dof}")

    print("  Initializing model...")
    m.fs.unit.initialize()

    print("  Solving...")
    solver = get_solver()
    results = solver.solve(m)

    print_header(f"RESULTS - Zero-Order {config['technology'].replace('_', ' ').title()}")
    m.fs.unit.report()


# ============================================================================
# Section 5: Result Export, Execution Wrapper & Main Menu
# ============================================================================

import io as _io


class _TeeOutput:
    """Write to both the real stdout and an internal buffer."""
    def __init__(self, original):
        self.original = original
        self.captured = _io.StringIO()

    def write(self, text):
        self.original.write(text)
        self.captured.write(text)

    def flush(self):
        self.original.flush()

    def getvalue(self):
        return self.captured.getvalue()


def export_results(report_text, model_name):
    """Offer to export simulation results to a text file."""
    save = get_bool("\n  Save results to a file?", default=False)
    if not save:
        return

    from datetime import datetime
    import os
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"watertap_results_{model_name}_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"WaterTAP Simulation Results - {model_name.upper()}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 64 + "\n\n")
        f.write(report_text)

    full_path = os.path.abspath(filename)
    print(f"\n  Results saved to: {full_path}")


def execute_model(config):
    """Dispatch to the appropriate runner with error handling."""
    import sys
    runners = {
        "ro": run_ro,
        "nf_dspmde": run_nf_dspmde,
        "ed": run_ed,
        "ed_1d": run_ed_1d,
        "md": run_md,
        "zero_order": run_zero_order,
    }

    tee = _TeeOutput(sys.stdout)
    old_stdout = sys.stdout
    success = False
    try:
        sys.stdout = tee
        runners[config["model_type"]](config)
        success = True
    except Exception as e:
        sys.stdout = old_stdout
        print(f"\n  Error during simulation: {type(e).__name__}: {e}")
        print("  Please check your input values and try again.")
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout = old_stdout

    if success:
        export_results(tee.getvalue(), config["model_type"])

    input("\n  Press Enter to return to the main menu...")


def main():
    while True:
        print_header("WaterTAP Membrane Simulation CLI")
        print("\n  Select a membrane model to simulate:\n")

        choice_opts = {
            1: "Reverse Osmosis (RO)",
            2: "Nanofiltration - DSPM-DE (NF)",
            3: "Electrodialysis (ED 0D / 1D)",
            4: "Membrane Distillation (MD)",
            5: "Zero-Order Models (MF / UF / NF simplified)",
            0: "Exit",
        }
        choice = get_choice("Select model", choice_opts)

        if choice == 0:
            print("\n  Goodbye!\n")
            break

        configurators = {
            1: configure_ro,
            2: configure_nf_dspmde,
            3: configure_ed,
            4: configure_md,
            5: configure_zero_order,
        }

        config = configurators[choice]()
        config = review_and_edit(config)

        if config is None:
            print("  Cancelled. Returning to main menu.")
            continue

        execute_model(config)


if __name__ == "__main__":
    main()
