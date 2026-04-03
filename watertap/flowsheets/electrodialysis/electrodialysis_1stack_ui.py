#################################################################################
# WaterTAP Copyright (c) 2020-2026, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory, Oak Ridge National Laboratory,
# National Laboratory of the Rockies, and National Energy Technology
# Laboratory (subject to receipt of any required approvals from the U.S. Dept.
# of Energy). All rights reserved.
#
# Please see the files COPYRIGHT.md and LICENSE.md for full copyright and license
# information, respectively. These files are also available online at the URL
# "https://github.com/watertap-org/watertap/"
#################################################################################
from watertap.core.solvers import get_solver
from idaes_flowsheet_processor.api import FlowsheetInterface
from watertap.flowsheets.electrodialysis.electrodialysis_1stack import (
    build,
    set_operating_conditions,
    initialize_system,
    solve,
)
from watertap.unit_models.electrodialysis_1D import (
    ElectricalOperationMode,
    PressureDropMethod,
    FrictionFactorMethod,
    HydraulicDiameterMethod,
    LimitingCurrentDensityMethod,
)
from pyomo.environ import Objective, value, units as pyunits


def export_to_ui():
    return FlowsheetInterface(
        name="Electrodialysis (single pass)",
        do_export=export_variables,
        do_build=build_flowsheet,
        do_solve=solve_flowsheet,
        build_options={
            "OperationMode": {
                "name": "OperationMode",
                "display_name": "Operation mode",
                "values_allowed": ["Simulation", "Optimization"],
                "value": "Simulation",
            },
            "ProductTargetNa": {
                "name": "ProductTargetNa",
                "display_name": "Product Na_+ target mass concentration (kg/m3, optimization only)",
                "values_allowed": "float",
                "value": 0.393,
                "min_val": 0.001,
                "max_val": 10.0,
            },
            "ElectricalMode": {
                "name": "ElectricalMode",
                "display_name": "Electrical operation mode",
                "values_allowed": [e.name for e in ElectricalOperationMode],
                "value": ElectricalOperationMode.Constant_Voltage.name,
            },
            "PressureDrop": {
                "name": "PressureDrop",
                "display_name": "Pressure drop method",
                "values_allowed": [e.name for e in PressureDropMethod],
                "value": PressureDropMethod.none.name,
            },
            "FrictionFactor": {
                "name": "FrictionFactor",
                "display_name": "Friction factor method",
                "values_allowed": [e.name for e in FrictionFactorMethod],
                "value": FrictionFactorMethod.fixed.name,
            },
            "HydraulicDiameter": {
                "name": "HydraulicDiameter",
                "display_name": "Hydraulic diameter method",
                "values_allowed": [e.name for e in HydraulicDiameterMethod],
                "value": HydraulicDiameterMethod.conventional.name,
            },
            "LimitingCurrentDensity": {
                "name": "LimitingCurrentDensity",
                "display_name": "Limiting current density method",
                "values_allowed": [e.name for e in LimitingCurrentDensityMethod],
                "value": LimitingCurrentDensityMethod.InitialValue.name,
            },
            "HasNonohmic": {
                "name": "HasNonohmic",
                "display_name": "Nonohmic membrane potential",
                "values_allowed": ["True", "False"],
                "value": "False",
            },
            "HasNernst": {
                "name": "HasNernst",
                "display_name": "Nernst diffusion layer",
                "values_allowed": ["True", "False"],
                "value": "False",
            },
            "FiniteElements": {
                "name": "FiniteElements",
                "display_name": "Number of finite elements",
                "values_allowed": "int",
                "value": 20,
                "min_val": 5,
                "max_val": 100,
            },
        },
    )


def export_variables(flowsheet=None, exports=None, build_options=None, **kwargs):
    fs = flowsheet
    # --- Input data ---
    # Feed conditions
    exports.add(
        obj=fs.feed.properties[0].flow_mol_phase_comp["Liq", "H2O"],
        name="Feed H2O molar flow rate",
        ui_units=pyunits.mol / pyunits.s,
        display_units="mol/s",
        rounding=3,
        description="Inlet water molar flow rate",
        is_input=True,
        input_category="Feed",
        is_output=False,
    )
    exports.add(
        obj=fs.feed.properties[0].flow_mol_phase_comp["Liq", "Na_+"],
        name="Feed Na_+ molar flow rate",
        ui_units=pyunits.mol / pyunits.s,
        display_units="mol/s",
        rounding=6,
        description="Molar flow rate of Na_+ ions in the feed solution",
        is_input=True,
        input_category="Feed",
        is_output=False,
    )
    exports.add(
        obj=fs.feed.properties[0].flow_mol_phase_comp["Liq", "Cl_-"],
        name="Feed Cl_- molar flow rate",
        ui_units=pyunits.mol / pyunits.s,
        display_units="mol/s",
        rounding=6,
        description="Molar flow rate of Cl_- ions in the feed solution",
        is_input=True,
        input_category="Feed",
        is_output=False,
    )

    # Separator
    exports.add(
        obj=fs.separator.split_fraction[0, "inlet_diluate"],
        name="Separator split fraction (diluate)",
        ui_units=pyunits.dimensionless,
        display_units="fraction",
        rounding=2,
        description="Fraction of feed directed to the diluate channel",
        is_input=True,
        input_category="Feed",
        is_output=False,
    )

    # ED stack conditions
    exports.add(
        obj=fs.EDstack.voltage_applied[0],
        name="ED stack voltage",
        ui_units=pyunits.volt,
        display_units="V",
        rounding=3,
        description="Applied constant voltage on the ED stack",
        is_input=True,
        input_category="ED stack",
        is_output=True,
        output_category="ED stack",
    )
    exports.add(
        obj=fs.EDstack.cell_pair_num,
        name="ED stack cell pair number",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=0,
        description="Cell pair number in a single ED stack",
        is_input=True,
        input_category="ED stack",
        is_output=True,
        output_category="ED stack",
    )
    exports.add(
        obj=fs.EDstack.channel_height,
        name="ED flow channel height",
        ui_units=pyunits.meter,
        display_units="m",
        rounding=4,
        description="Channel height of the ED flow channels",
        is_input=True,
        input_category="ED stack",
        is_output=True,
        output_category="ED stack",
    )
    exports.add(
        obj=fs.EDstack.cell_width,
        name="ED cell width",
        ui_units=pyunits.meter,
        display_units="m",
        rounding=3,
        description="The width of ED cell or stack",
        is_input=True,
        input_category="ED stack",
        is_output=True,
        output_category="ED stack",
    )
    exports.add(
        obj=fs.EDstack.cell_length,
        name="ED channel length",
        ui_units=pyunits.meter,
        display_units="m",
        rounding=3,
        description="The length of ED cell or stack",
        is_input=True,
        input_category="ED stack",
        is_output=True,
        output_category="ED stack",
    )
    exports.add(
        obj=fs.EDstack.spacer_porosity,
        name="ED spacer porosity",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=2,
        description="Porosity of the flow spacer",
        is_input=True,
        input_category="ED stack",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.spacer_conductivity_coefficient,
        name="ED spacer conductivity coefficient",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=2,
        description="Conductivity coefficient of the flow spacer",
        is_input=True,
        input_category="ED stack",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.electrodes_resistance,
        name="ED electrode resistance",
        ui_units=pyunits.ohm * pyunits.meter**2,
        display_units="ohm m^2",
        rounding=2,
        description="Areal resistance of the two electrodes",
        is_input=True,
        input_category="ED stack",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.current_utilization,
        name="ED current utilization coefficient",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=2,
        description="Current utilization coefficient",
        is_input=True,
        input_category="ED stack",
        is_output=False,
    )

    # Membrane-related properties
    exports.add(
        obj=fs.EDstack.water_trans_number_membrane["cem"],
        name="Water electroosmosis transport number of CEM",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=2,
        description="Water electroosmosis transport number of the cation exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.water_trans_number_membrane["aem"],
        name="Water electroosmosis transport number of AEM",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=2,
        description="Water electroosmosis transport number of the anion exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.water_permeability_membrane["cem"],
        name="Water osmosis permeability of CEM",
        ui_units=pyunits.meter * pyunits.second**-1 * pyunits.pascal**-1,
        display_units="m s^-1 Pa^-1",
        rounding=2,
        description="Water osmosis permeability of the cation exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.water_permeability_membrane["aem"],
        name="Water osmosis permeability of AEM",
        ui_units=pyunits.meter * pyunits.second**-1 * pyunits.pascal**-1,
        display_units="m s^-1 Pa^-1",
        rounding=2,
        description="Water osmosis permeability of the anion exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.membrane_areal_resistance["cem"],
        name="Areal resistance of CEM",
        ui_units=pyunits.ohm * pyunits.meter**2,
        display_units="ohm m^2",
        rounding=2,
        description="Constant areal resistance of the cation exchange membrane measured in concentrated electrolyte.",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.membrane_areal_resistance["aem"],
        name="Areal resistance of AEM",
        ui_units=pyunits.ohm * pyunits.meter**2,
        display_units="ohm m^2",
        rounding=2,
        description="Constant areal resistance of the anion exchange membrane measured in concentrated electrolyte.",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.membrane_areal_resistance_coef["cem"],
        name="Areal resistance coefficient of CEM",
        ui_units=pyunits.ohm * pyunits.meter**2 * pyunits.mol / pyunits.m**3,
        display_units="ohm m^2 mol m^-3",
        rounding=2,
        description="Areal resistance coefficient of the cation exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.membrane_areal_resistance_coef["aem"],
        name="Areal resistance coefficient of AEM",
        ui_units=pyunits.ohm * pyunits.meter**2 * pyunits.mol / pyunits.m**3,
        display_units="ohm m^2 mol m^-3",
        rounding=2,
        description="Areal resistance coefficient of the anion exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.membrane_thickness["cem"],
        name="Thickness of CEM",
        ui_units=pyunits.meter,
        display_units="m",
        rounding=2,
        description="Thickness of the cation exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.membrane_thickness["aem"],
        name="Thickness of AEM",
        ui_units=pyunits.meter,
        display_units="m",
        rounding=2,
        description="Thickness of the anion exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.solute_diffusivity_membrane["cem", "Na_+"],
        name="Na_+ diffusivity as solute in CEM",
        ui_units=pyunits.meter**2 * pyunits.second**-1,
        display_units="m^2 s^-1",
        rounding=2,
        description="Na_+ diffusivity as solute in the cation exchange membrane (the mass diffusivity of the corresponding neutral solute should be used.)",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.solute_diffusivity_membrane["aem", "Na_+"],
        name="Na_+ diffusivity as solute in AEM",
        ui_units=pyunits.meter**2 * pyunits.second**-1,
        display_units="m^2 s^-1",
        rounding=2,
        description="Na_+ diffusivity as solute in the anion exchange membrane (the mass diffusivity of the corresponding neutral solute should be used.)",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.solute_diffusivity_membrane["cem", "Cl_-"],
        name="Cl_- diffusivity as solute in CEM",
        ui_units=pyunits.meter**2 * pyunits.second**-1,
        display_units="m^2 s^-1",
        rounding=2,
        description="Cl_- diffusivity as solute in the cation exchange membrane (the mass diffusivity of the corresponding neutral solute should be used.)",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.solute_diffusivity_membrane["aem", "Cl_-"],
        name="Cl_- diffusivity as solute in AEM",
        ui_units=pyunits.meter**2 * pyunits.second**-1,
        display_units="m^2 s^-1",
        rounding=2,
        description="Cl_- diffusivity as solute in the anion exchange membrane (the mass diffusivity of the corresponding neutral solute should be used.)",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.ion_trans_number_membrane["cem", "Na_+"],
        name="Na_+ transport number in CEM",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=1,
        description="Na_+ transport number in the cation exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.ion_trans_number_membrane["aem", "Na_+"],
        name="Na_+ transport number in AEM",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=1,
        description="Na_+ transport number in the anion exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.ion_trans_number_membrane["cem", "Cl_-"],
        name="Cl_- transport number in CEM",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=1,
        description="Cl_- transport number in the cation exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )
    exports.add(
        obj=fs.EDstack.ion_trans_number_membrane["aem", "Cl_-"],
        name="Cl_- transport number in AEM",
        ui_units=pyunits.dimensionless,
        display_units="",
        rounding=1,
        description="Cl_- transport number in the anion exchange membrane",
        is_input=True,
        input_category="Membrane properties",
        is_output=False,
    )

    # System costing
    exports.add(
        obj=fs.costing.utilization_factor,
        name="Utilization factor",
        ui_units=pyunits.dimensionless,
        display_units="fraction",
        rounding=2,
        description="Utilization factor - [annual use hours/total hours in year]",
        is_input=True,
        input_category="System costing",
        is_output=False,
    )
    exports.add(
        obj=fs.costing.TIC,
        name="Total Installed Cost",
        ui_units=pyunits.dimensionless,
        display_units="fraction",
        rounding=1,
        description="Total Installed Cost (TIC)",
        is_input=True,
        input_category="System costing",
        is_output=False,
    )
    exports.add(
        obj=fs.costing.TPEC,
        name="Total Purchased Equipment Cost",
        ui_units=pyunits.dimensionless,
        display_units="fraction",
        rounding=1,
        description="Total Purchased Equipment Cost (TPEC)",
        is_input=True,
        input_category="System costing",
        is_output=False,
    )
    exports.add(
        obj=fs.costing.total_investment_factor,
        name="Total investment factor",
        ui_units=pyunits.dimensionless,
        display_units="fraction",
        rounding=2,
        description="Total investment factor [investment cost/equipment cost]",
        is_input=True,
        input_category="System costing",
        is_output=False,
    )
    exports.add(
        obj=fs.costing.maintenance_labor_chemical_factor,
        name="Maintenance-labor-chemical factor",
        ui_units=1 / pyunits.year,
        display_units="fraction/year",
        rounding=2,
        description="Maintenance-labor-chemical factor [fraction of investment cost/year]",
        is_input=True,
        input_category="System costing",
        is_output=False,
    )
    exports.add(
        obj=fs.costing.capital_recovery_factor,
        name="Capital annualization factor",
        ui_units=1 / pyunits.year,
        display_units="fraction/year",
        rounding=2,
        description="Capital annualization factor [fraction of investment cost/year]",
        is_input=True,
        input_category="System costing",
        is_output=False,
    )
    exports.add(
        obj=fs.costing.electricity_cost,
        name="Electricity cost",
        ui_units=fs.costing.base_currency / pyunits.kWh,
        display_units="$/kWh",
        rounding=3,
        description="Electricity cost",
        is_input=True,
        input_category="System costing",
        is_output=False,
    )

    # --- Output data ---
    # Feed
    exports.add(
        obj=fs.feed.properties[0].flow_vol_phase["Liq"],
        name="Feed volume flow rate",
        ui_units=pyunits.m**3 / pyunits.s,
        display_units="m^3/s",
        rounding=6,
        description="Feed volumetric flow rate",
        is_input=False,
        is_output=True,
        output_category="Feed",
    )

    # Product
    exports.add(
        obj=fs.product.properties[0].flow_vol_phase["Liq"],
        name="Product volumetric flow rate",
        ui_units=pyunits.m**3 / pyunits.hr,
        display_units="m3/h",
        rounding=2,
        description="Product water volumetric flow rate",
        is_input=False,
        is_output=True,
        output_category="Product",
    )
    exports.add(
        obj=fs.product_salinity,
        name="Product NaCl mass concentration",
        ui_units=pyunits.kg / pyunits.meter**3,
        display_units="kg m^-3",
        rounding=3,
        description="Product water NaCl mass concentration",
        is_input=False,
        is_output=True,
        output_category="Product",
    )

    # Disposal
    exports.add(
        obj=fs.disposal.properties[0].flow_vol_phase["Liq"],
        name="Disposal volumetric flow rate",
        ui_units=pyunits.m**3 / pyunits.hr,
        display_units="m3/h",
        rounding=2,
        description="Disposal water volumetric flow rate",
        is_input=False,
        is_output=True,
        output_category="Disposal",
    )
    exports.add(
        obj=fs.disposal_salinity,
        name="Disposal NaCl mass concentration",
        ui_units=pyunits.kg / pyunits.meter**3,
        display_units="kg m^-3",
        rounding=3,
        description="Disposal water NaCl mass concentration",
        is_input=False,
        is_output=True,
        output_category="Disposal",
    )

    # System metrics
    exports.add(
        obj=fs.EDstack.recovery_mass_H2O[0],
        name="Water recovery by mass",
        ui_units=pyunits.dimensionless,
        display_units="fraction",
        rounding=3,
        description="Water recovery by mass",
        is_input=False,
        is_output=True,
        output_category="System metrics",
    )
    exports.add(
        obj=fs.mem_area,
        name="Membrane area of CEM and AEM",
        ui_units=pyunits.m**2,
        display_units="m^2",
        rounding=2,
        description="Membrane area of the cation or anion exchange membranes",
        is_input=False,
        is_output=True,
        output_category="System metrics",
    )
    exports.add(
        obj=fs.costing.specific_energy_consumption,
        name="Specific energy consumption",
        ui_units=pyunits.kWh / pyunits.m**3,
        display_units="kWh/m3 of product water",
        rounding=3,
        description="Specific energy consumption (SEC)",
        is_input=False,
        is_output=True,
        output_category="System metrics",
    )
    exports.add(
        obj=fs.costing.LCOW,
        name="Levelized cost of water",
        ui_units=fs.costing.base_currency / pyunits.m**3,
        display_units="$/m3 of product water",
        rounding=3,
        description="Levelized cost of water (LCOW)",
        is_input=False,
        is_output=True,
        output_category="System metrics",
    )


def _parse_build_options(build_options):
    """Convert GUI build_options to keyword arguments for build()."""
    if build_options is None:
        return {}
    kwargs = {}
    if "ElectricalMode" in build_options:
        kwargs["operation_mode"] = ElectricalOperationMode[
            build_options["ElectricalMode"].value
        ]
    if "PressureDrop" in build_options:
        pd_method = PressureDropMethod[build_options["PressureDrop"].value]
        kwargs["pressure_drop_method"] = pd_method
        kwargs["has_pressure_change"] = pd_method != PressureDropMethod.none
    if "FrictionFactor" in build_options:
        kwargs["friction_factor_method"] = FrictionFactorMethod[
            build_options["FrictionFactor"].value
        ]
    if "HydraulicDiameter" in build_options:
        kwargs["hydraulic_diameter_method"] = HydraulicDiameterMethod[
            build_options["HydraulicDiameter"].value
        ]
    if "LimitingCurrentDensity" in build_options:
        kwargs["limiting_current_density_method"] = LimitingCurrentDensityMethod[
            build_options["LimitingCurrentDensity"].value
        ]
    if "HasNonohmic" in build_options:
        kwargs["has_nonohmic_potential_membrane"] = (
            build_options["HasNonohmic"].value == "True"
        )
    if "HasNernst" in build_options:
        kwargs["has_Nernst_diffusion_layer"] = (
            build_options["HasNernst"].value == "True"
        )
    if "FiniteElements" in build_options:
        kwargs["finite_elements"] = build_options["FiniteElements"].value
    return kwargs


def build_flowsheet(build_options=None, **kwargs):

    solver = get_solver()

    # build, set operating conditions, and initialize
    build_kwargs = _parse_build_options(build_options)
    m = build(**build_kwargs)
    set_operating_conditions(m)

    # the UI sets `capital_recovery_factor`, so unfix `wacc`
    m.fs.costing.wacc.unfix()
    m.fs.costing.capital_recovery_factor.fix()

    initialize_system(m, solver=solver)
    solve(m, solver=solver)

    # Optimization mode: minimize LCOW by unfixing voltage and cell_pair_num
    if build_options is not None and build_options["OperationMode"].value == "Optimization":
        m.fs.objective = Objective(expr=m.fs.costing.LCOW)

        m.fs.EDstack.voltage_applied[0].unfix()
        m.fs.EDstack.cell_pair_num.unfix()
        m.fs.EDstack.cell_pair_num.set_value(30)

        m.fs.EDstack.voltage_applied[0].setlb(0.5)
        m.fs.EDstack.voltage_applied[0].setub(20)
        m.fs.EDstack.cell_pair_num.setlb(5)
        m.fs.EDstack.cell_pair_num.setub(500)

        # Fix product concentration target (Na_+ mass concentration in kg/m3)
        product_target = build_options["ProductTargetNa"].value
        m.fs.product.properties[0].conc_mass_phase_comp["Liq", "Na_+"].fix(
            product_target
        )

        solve(m, solver=solver)

        # Round cell pair number to integer and re-solve
        m.fs.EDstack.cell_pair_num.fix(round(value(m.fs.EDstack.cell_pair_num)))
        solve(m, solver=solver)

    return m


def solve_flowsheet(flowsheet=None):
    fs = flowsheet
    results = solve(fs)
    return results
