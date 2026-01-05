<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2004/10/xpath-functions" xmlns:xdt="http://www.w3.org/2004/10/xpath-datatypes">
    <xsl:output version="1.0" encoding="UTF-8" indent="no" omit-xml-declaration="no" media-type="text/html" />
    <xsl:template match="/">
        <html>
            <head>
                <title />
            </head>
            <body>
                <xsl:for-each select="WUFI2D">
                    <br />
                    <h3>
                        <center>WUFI2D Project Overview</center>
                    </h3>
                    <br />Info: <xsl:for-each select="Info">
                        <br />Projectname: <xsl:for-each select="ProjectName">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Contact: <xsl:for-each select="Contact">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Phone: <xsl:for-each select="Phone">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />City-Zip: <xsl:for-each select="City-Zip">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Street: <xsl:for-each select="Street">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Client: <xsl:for-each select="Client">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Number: <xsl:for-each select="Number">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Remarks: <xsl:for-each select="Remarks">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />e-Mail: <xsl:for-each select="eMail">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Responsible: <xsl:for-each select="Responsible">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Fax: <xsl:for-each select="Fax">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Comment: <xsl:for-each select="Comment">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Date of creation: <xsl:for-each select="Date">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />
                    </xsl:for-each>
                    <br />Construction:<br />
                    <xsl:for-each select="Construction">
                        <br />Definition of construction:<br />
                        <xsl:for-each select="Definition">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />
                        <xsl:for-each select="Path">
                            <br />Rectangles / orthogonal polygons:<br />
                            <xsl:for-each select="OrthoPolygons">
                                <br />
                                <xsl:for-each select="OrthoPolygon">
                                    <ul style="margin-bottom:0; margin-top:0; " start="1" type="disc">
                                        <li>
                                            <table border="1" width="100%">
                                                <tbody>
                                                    <tr>
                                                        <td>Name</td>
                                                        <td>
                                                            <xsl:for-each select="ID">
                                                                <xsl:apply-templates />
                                                            </xsl:for-each>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>Color</td>
                                                        <td>
                                                            <xsl:for-each select="Color">
                                                                <xsl:apply-templates />
                                                            </xsl:for-each>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>XMaterialID</td>
                                                        <td>
                                                            <xsl:for-each select="XMaterialID">
                                                                <xsl:apply-templates />
                                                            </xsl:for-each>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>XMaterialID</td>
                                                        <td>
                                                            <xsl:for-each select="YMaterialID">
                                                                <xsl:apply-templates />
                                                            </xsl:for-each>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>Initial Theta</td>
                                                        <td>
                                                            <xsl:for-each select="InitialTheta">
                                                                <xsl:apply-templates />
                                                            </xsl:for-each>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>Initial Phi</td>
                                                        <td>
                                                            <xsl:for-each select="InitialPhi">
                                                                <xsl:apply-templates />
                                                            </xsl:for-each>
                                                        </td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </li>
                                    </ul>
                                </xsl:for-each>
                                <br />
                            </xsl:for-each>
                            <br />
                            <br />Outersurfaces:<br />
                            <xsl:for-each select="OuterSurfaces">
                                <xsl:for-each select="Attributes">
                                    <br />Surfacetransfercoefficients and Climate<ul style="margin-bottom:0; margin-top:0; " start="1" type="disc">
                                        <xsl:for-each select="Attribute">
                                            <li>
                                                <xsl:apply-templates />
                                            </li>
                                        </xsl:for-each>
                                    </ul>
                                </xsl:for-each>
                                <br />
                            </xsl:for-each>
                            <br />
                            <br />Innersurfaces:<br />
                            <xsl:for-each select="InnerSurfaces">
                                <ul style="margin-bottom:0; margin-top:0; " start="1" type="disc">
                                    <xsl:for-each select="Attributes">
                                        <li>
                                            <xsl:apply-templates />
                                        </li>
                                    </xsl:for-each>
                                </ul>
                                <br />
                            </xsl:for-each>
                            <br />Grid:<br />
                            <xsl:for-each select="Grid">
                                <br />X-Direction:<br />
                                <xsl:for-each select="X-Direction">
                                    <br />Number of layers: <xsl:for-each select="NLayer">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Mode of generation: <xsl:for-each select="Mode">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Number of elements: <xsl:for-each select="Splitting">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Dimension [mm]: <xsl:for-each select="Dimension">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Expansion factor: <xsl:for-each select="Geometry">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />
                                </xsl:for-each>
                                <br />Y-Direction:<br />
                                <xsl:for-each select="Y-Direction">
                                    <br />Number of layers: <xsl:for-each select="NLayer">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Mode of generation: <xsl:for-each select="Mode">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Number of elements: <xsl:for-each select="Splitting">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Dimension [mm]: <xsl:for-each select="Dimension">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />Expansion factor: <xsl:for-each select="Geometry">
                                        <xsl:apply-templates />
                                    </xsl:for-each>
                                    <br />
                                </xsl:for-each>
                                <br />
                            </xsl:for-each>
                            <br />
                        </xsl:for-each>
                        <br />
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Numeric">
                        <br />Timestep [s]: <xsl:for-each select="Timestep">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Timestep is constant: <xsl:for-each select="ConstTimestep">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Name of file holding timesteps: <xsl:for-each select="TimestepFile">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Number of timesteps: <xsl:for-each select="TimestepCount">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Number of timesteps is constant: <xsl:for-each select="ConstTimestepCount">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Name of File holding number of timesteps: <xsl:for-each select="TimestepFileCount">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Convergence criterion: <xsl:for-each select="ConvergenceCrit">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Max. number of iterations: <xsl:for-each select="MaxIt">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Include Heat of Evaporation: <xsl:for-each select="HasHeatOfEvaporation">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Include Heat of Fusion: <xsl:for-each select="HasHeatOfFusion">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />Take capillary conduction into account: <xsl:for-each select="HasCapillaryConduction">
                            <xsl:apply-templates />
                        </xsl:for-each>
                        <br />
                        <xsl:for-each select="Solver">
                            <br />
                            <table border="1" width="100%">
                                <tbody>
                                    <tr>
                                        <td>Variable Name</td>
                                        <td>Flux blending</td>
                                        <td>Under relaxation</td>
                                        <td>SOR</td>
                                        <td>Number of swaps</td>
                                        <td>Solve for</td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <xsl:for-each select="Property1">
                                                <xsl:for-each select="VariableName">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property1">
                                                <xsl:for-each select="GDS">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property1">
                                                <xsl:for-each select="URF">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property1">
                                                <xsl:for-each select="SOR">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property1">
                                                <xsl:for-each select="NSW">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property1">
                                                <xsl:for-each select="Solve">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <xsl:for-each select="Property2">
                                                <xsl:for-each select="VariableName">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property2">
                                                <xsl:for-each select="GDS">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property2">
                                                <xsl:for-each select="URF">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property2">
                                                <xsl:for-each select="SOR">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property2">
                                                <xsl:for-each select="NSW">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property2">
                                                <xsl:for-each select="Solve">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <xsl:for-each select="Property3">
                                                <xsl:for-each select="VariableName">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property3">
                                                <xsl:for-each select="GDS">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property3">
                                                <xsl:for-each select="URF">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property3">
                                                <xsl:for-each select="SOR">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property3">
                                                <xsl:for-each select="NSW">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property3">
                                                <xsl:for-each select="Solve">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <xsl:for-each select="Property4">
                                                <xsl:for-each select="VariableName">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property4">
                                                <xsl:for-each select="GDS">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property4">
                                                <xsl:for-each select="URF">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property4">
                                                <xsl:for-each select="SOR">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property4">
                                                <xsl:for-each select="NSW">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property4">
                                                <xsl:for-each select="Solve">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            <xsl:for-each select="Property5">
                                                <xsl:for-each select="VariableName">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property5">
                                                <xsl:for-each select="GDS">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property5">
                                                <xsl:for-each select="URF">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property5">
                                                <xsl:for-each select="SOR">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property5">
                                                <xsl:for-each select="NSW">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                        <td>
                                            <xsl:for-each select="Property5">
                                                <xsl:for-each select="Solve">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </xsl:for-each>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </xsl:for-each>
                        <br />Store fields in outputfile:<br />
                        <table border="1" width="100%">
                            <tbody>
                                <tr>
                                    <td>Watercontent</td>
                                    <td>
                                        <xsl:for-each select="wcont">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                                <tr>
                                    <td>rel. Humidity</td>
                                    <td>
                                        <xsl:for-each select="phi">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                                <tr>
                                    <td>Temperature</td>
                                    <td>
                                        <xsl:for-each select="teta">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                                <tr>
                                    <td>part. Pressure of Vapour</td>
                                    <td>
                                        <xsl:for-each select="vap">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                                <tr>
                                    <td>cap. Flux</td>
                                    <td>
                                        <xsl:for-each select="flxc">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                                <tr>
                                    <td>diff. Flux</td>
                                    <td>
                                        <xsl:for-each select="flxd">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                                <tr>
                                    <td>heat Flux</td>
                                    <td>
                                        <xsl:for-each select="flxh">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                                <tr>
                                    <td>Air Velocity</td>
                                    <td>
                                        <xsl:for-each select="vxy">
                                            <xsl:apply-templates />
                                        </xsl:for-each>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </xsl:for-each>
                    <br />
                </xsl:for-each>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
