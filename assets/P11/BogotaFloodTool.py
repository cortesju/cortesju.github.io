# -*- coding: utf-8 -*-
import arcpy

class Toolbox(object):
    def __init__(self):
        """Define the toolbox."""
        self.label = "Flooding Risk Toolbox"
        self.alias = "FloodingRisk"
        self.tools = [FloodRiskTool]


class FloodRiskTool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Flood Risk Block Classification"
        self.description = (
            "Merge desbordamiento and jarillon hazard layers, buffer the "
            "hydrology network, and classify urban blocks into four categories "
            "based on intersection with hazard polygons and the hydrology buffer."
        )
        self.canRunInBackground = False

    # ----------------------------------------------------------------------
    def getParameterInfo(self):
        """Define parameter definitions."""

        p0 = arcpy.Parameter(
            displayName="Overflow Hazard (Desbordamiento)",
            name="in_haz_desb",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input"
        )
        p0.description = "Polygon hazard layer representing flood risk due to overflow (desbordamiento)."

        p1 = arcpy.Parameter(
            displayName="Jarillon Hazard (Rompimiento de Jarillon)",
            name="in_haz_jar",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input"
        )
        p1.description = "Polygon hazard layer representing flood risk due to failure of a containment dike (jarillon)."

        p2 = arcpy.Parameter(
            displayName="Hydrology (Drenaje)",
            name="in_hydro",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input"
        )
        p2.description = "Line layer representing rivers, creeks, and drainage channels."

        p3 = arcpy.Parameter(
            displayName="Blocks (Manzanas)",
            name="in_blocks",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input"
        )
        p3.description = "Urban block polygons used as the analysis unit for risk classification."

        p4 = arcpy.Parameter(
            displayName="Bogota Boundary",
            name="in_muni",
            datatype="Feature Layer",
            parameterType="Required",
            direction="Input"
        )
        p4.description = "Boundary polygon representing the study area used to clip all inputs."

        p5 = arcpy.Parameter(
            displayName="Buffer Distance",
            name="buffer_dist",
            datatype="Linear Unit",
            parameterType="Required",
            direction="Input"
        )
        p5.value = "100 Meters"
        p5.description = "Distance used to create a buffer around the hydrology network (for example, 100 Meters)."

        p6 = arcpy.Parameter(
            displayName="Output Blocks with Risk Categories",
            name="out_blocks_risk",
            datatype="Feature Class",
            parameterType="Required",
            direction="Output"
        )
        p6.description = "Output feature class containing blocks labeled with four categories: Hazard & Buffer, Only Buffer, Only Hazard, and None."

        return [p0, p1, p2, p3, p4, p5, p6]

    # ----------------------------------------------------------------------
    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify parameter values and properties before internal validation."""
        return

    def updateMessages(self, parameters):
        """Modify messages created by internal validation."""
        return

    # ----------------------------------------------------------------------
    def execute(self, parameters, messages):
        """Run the flood risk workflow."""

        arcpy.env.overwriteOutput = True
        sr = arcpy.SpatialReference(3116)  # MAGNA-SIRGAS / Colombia Bogota zone

        # Read parameters
        in_haz_desb   = parameters[0].valueAsText
        in_haz_jar    = parameters[1].valueAsText
        in_hydro      = parameters[2].valueAsText
        in_blocks     = parameters[3].valueAsText
        in_muni       = parameters[4].valueAsText
        buffer_dist   = parameters[5].valueAsText
        out_blocks_fc = parameters[6].valueAsText

        messages.addMessage("Projecting inputs to EPSG:3116 ...")

        # Project all inputs into memory
        haz_desb_prj = arcpy.management.Project(in_haz_desb, "in_memory/haz_desb_prj", sr)
        haz_jar_prj  = arcpy.management.Project(in_haz_jar,  "in_memory/haz_jar_prj",  sr)
        hydro_prj    = arcpy.management.Project(in_hydro,    "in_memory/hydro_prj",    sr)
        blocks_prj   = arcpy.management.Project(in_blocks,   "in_memory/blocks_prj",   sr)
        muni_prj     = arcpy.management.Project(in_muni,     "in_memory/muni_prj",     sr)

        # Dissolve Bogota boundary
        muni_union = arcpy.management.Dissolve(muni_prj, "in_memory/muni_union")

        messages.addMessage("Creating unified hazard layer with HAZ_TYPE ...")

        # Copy hazards and add HAZ_TYPE
        haz_desb_copy = arcpy.management.CopyFeatures(haz_desb_prj, "in_memory/haz_desb_copy")
        haz_jar_copy  = arcpy.management.CopyFeatures(haz_jar_prj,  "in_memory/haz_jar_copy")

        for fc, val in [(haz_desb_copy, "DESBORDAMIENTO"),
                        (haz_jar_copy,  "ROMPIMIENTO_JARILLON")]:
            field_names = [f.name for f in arcpy.ListFields(fc)]
            if "HAZ_TYPE" not in field_names:
                arcpy.management.AddField(fc, "HAZ_TYPE", "TEXT", field_length=30)
            arcpy.management.CalculateField(fc, "HAZ_TYPE", f'"{val}"', "PYTHON3")

        # Merge hazards
        haz_all = arcpy.management.Merge([haz_desb_copy, haz_jar_copy], "in_memory/haz_all")

        messages.addMessage("Clipping hazards, hydrology and blocks to boundary ...")

        haz_clip    = arcpy.analysis.Clip(haz_all,    muni_union, "in_memory/haz_clip")
        hydro_clip  = arcpy.analysis.Clip(hydro_prj,  muni_union, "in_memory/hydro_clip")
        blocks_clip = arcpy.analysis.Clip(blocks_prj, muni_union, "in_memory/blocks_clip")

        messages.addMessage("Buffering hydrology ...")
        hydro_buffer = arcpy.analysis.Buffer(
            hydro_clip, "in_memory/hydro_buffer", buffer_dist, dissolve_option="ALL"
        )

        # Copy blocks to output
        messages.addMessage("Copying blocks to output feature class ...")
        blocks_out = arcpy.management.CopyFeatures(blocks_clip, out_blocks_fc)

        # Add flag fields and risk category
        messages.addMessage("Adding fields IN_HAZARD, IN_BUFFER, RISK_CAT ...")
        field_names_out = [f.name for f in arcpy.ListFields(blocks_out)]
        if "IN_HAZARD" not in field_names_out:
            arcpy.management.AddField(blocks_out, "IN_HAZARD", "SHORT")
        if "IN_BUFFER" not in field_names_out:
            arcpy.management.AddField(blocks_out, "IN_BUFFER", "SHORT")
        if "RISK_CAT" not in field_names_out:
            arcpy.management.AddField(blocks_out, "RISK_CAT", "TEXT", field_length=30)

        arcpy.management.MakeFeatureLayer(blocks_out, "blocks_lyr")
        arcpy.management.MakeFeatureLayer(haz_clip,   "haz_lyr")
        arcpy.management.MakeFeatureLayer(hydro_buffer, "buf_lyr")

        # Initialize flags
        arcpy.management.CalculateField("blocks_lyr", "IN_HAZARD", "0", "PYTHON3")
        arcpy.management.CalculateField("blocks_lyr", "IN_BUFFER", "0", "PYTHON3")

        # IN_HAZARD = 1 where blocks intersect hazard
        arcpy.management.SelectLayerByLocation("blocks_lyr", "INTERSECT", "haz_lyr")
        arcpy.management.CalculateField("blocks_lyr", "IN_HAZARD", "1", "PYTHON3")

        # IN_BUFFER = 1 where blocks intersect buffer
        arcpy.management.SelectLayerByAttribute("blocks_lyr", "CLEAR_SELECTION")
        arcpy.management.SelectLayerByLocation("blocks_lyr", "INTERSECT", "buf_lyr")
        arcpy.management.CalculateField("blocks_lyr", "IN_BUFFER", "1", "PYTHON3")

        arcpy.management.SelectLayerByAttribute("blocks_lyr", "CLEAR_SELECTION")

        messages.addMessage("Calculating RISK_CAT categories ...")

        code_block = """
def classify(in_haz, in_buf):
    if in_haz == 1 and in_buf == 1:
        return "Hazard & Buffer"
    elif in_buf == 1 and in_haz == 0:
        return "Only Buffer"
    elif in_haz == 1 and in_buf == 0:
        return "Only Hazard"
    else:
        return "None"
"""
        arcpy.management.CalculateField(
            "blocks_lyr",
            "RISK_CAT",
            "classify(!IN_HAZARD!, !IN_BUFFER!)",
            "PYTHON3",
            code_block
        )

        messages.addMessage("Flood Risk Block Classification completed.")
        return