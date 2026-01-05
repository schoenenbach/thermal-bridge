<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2004/10/xpath-functions" xmlns:xdt="http://www.w3.org/2004/10/xpath-datatypes">
    <xsl:output version="1.0" encoding="UTF-8" indent="no" omit-xml-declaration="no" media-type="text/html" />
    <xsl:template match="/">
        <html>
            <head>
                <title />
            </head>
            <body>
                <xsl:for-each select="WUFI-Material">
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="Name">Name: <xsl:apply-templates />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="Info">Info: <xsl:apply-templates />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="Flags">Flags: <xsl:apply-templates />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="Type">Type: <xsl:apply-templates />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="NoMoistureTransport">NoMoistureTransport: <xsl:apply-templates />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="Color">Color: <xsl:apply-templates />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="Scalars">
                            <table border="1">
                                <thead>
                                    <tr>
                                        <td>name</td>
                                        <td>unit</td>
                                        <td>value</td>
                                    </tr>
                                </thead>
                                <tbody>
                                    <xsl:for-each select="Scalar">
                                        <tr>
                                            <td>
                                                <xsl:for-each select="@name">
                                                    <xsl:value-of select="." />
                                                </xsl:for-each>
                                            </td>
                                            <td>
                                                <xsl:for-each select="@unit">
                                                    <xsl:value-of select="." />
                                                </xsl:for-each>
                                            </td>
                                            <td>
                                                <xsl:for-each select="@value">
                                                    <xsl:value-of select="." />
                                                </xsl:for-each>
                                            </td>
                                        </tr>
                                    </xsl:for-each>
                                </tbody>
                            </table>
                            <br />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                    <xsl:for-each select="Data">
                        <xsl:for-each select="Functions">
                            <table border="1">
                                <thead>
                                    <tr>
                                        <td>name</td>
                                        <td>version</td>
                                        <td>Generated</td>
                                        <td>GenerationMode</td>
                                        <td>Items</td>
                                    </tr>
                                </thead>
                                <tbody>
                                    <xsl:for-each select="Function">
                                        <tr>
                                            <td>
                                                <xsl:for-each select="@name">
                                                    <xsl:value-of select="." />
                                                </xsl:for-each>
                                            </td>
                                            <td>
                                                <xsl:for-each select="@version">
                                                    <xsl:value-of select="." />
                                                </xsl:for-each>
                                            </td>
                                            <td>
                                                <xsl:for-each select="Generated">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </td>
                                            <td>
                                                <xsl:for-each select="GenerationMode">
                                                    <xsl:apply-templates />
                                                </xsl:for-each>
                                            </td>
                                            <td>
                                                <xsl:for-each select="Items">
                                                    <table border="1">
                                                        <thead>
                                                            <tr>
                                                                <td>x [<xsl:for-each select="@xunit">
                                                                        <xsl:value-of select="." />
                                                                    </xsl:for-each>]</td>
                                                                <td>y [<xsl:for-each select="@yunit">
                                                                        <xsl:value-of select="." />
                                                                    </xsl:for-each>]</td>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <xsl:for-each select="Item">
                                                                <tr>
                                                                    <td>
                                                                        <xsl:for-each select="@x">
                                                                            <xsl:value-of select="." />
                                                                        </xsl:for-each>
                                                                    </td>
                                                                    <td>
                                                                        <xsl:for-each select="@y">
                                                                            <xsl:value-of select="." />
                                                                        </xsl:for-each>
                                                                    </td>
                                                                </tr>
                                                            </xsl:for-each>
                                                        </tbody>
                                                    </table>
                                                </xsl:for-each>
                                            </td>
                                        </tr>
                                    </xsl:for-each>
                                </tbody>
                            </table>
                            <br />
                            <br />
                            <br />
                            <br />
                        </xsl:for-each>
                    </xsl:for-each>
                    <br />
                </xsl:for-each>
                <br />
            </body>
        </html>
    </xsl:template>
    <xsl:template match="WUFI-Material">
        <xsl:apply-templates />
    </xsl:template>
</xsl:stylesheet>
