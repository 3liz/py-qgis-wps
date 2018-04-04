<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis minScale="1e+8" hasScaleBasedVisibilityFlag="0" maxScale="0" version="3.0.0-Girona">
  <pipe>
    <rasterrenderer band="1" classificationMin="1.01783e-10" classificationMax="0.000268079" opacity="1" alphaBand="-1" type="singlebandpseudocolor">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>MinMax</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader colorRampType="INTERPOLATED" classificationMode="1" clip="0">
          <colorramp name="[source]" type="gradient">
            <prop k="color1" v="26,150,65,255"/>
            <prop k="color2" v="215,25,28,255"/>
            <prop k="discrete" v="0"/>
            <prop k="rampType" v="gradient"/>
            <prop k="stops" v="0.25;166,217,106,255:0.5;255,255,192,255:0.75;253,174,97,255"/>
          </colorramp>
          <item color="#1a9641" label="1.02e-10" value="1.01783e-10" alpha="255"/>
          <item color="#a6d96a" label="6.7e-5" value="6.701982633725e-5" alpha="255"/>
          <item color="#ffffc0" label="0.000134" value="0.0001340395508915" alpha="255"/>
          <item color="#fdae61" label="0.000201" value="0.00020105927544575" alpha="255"/>
          <item color="#d7191c" label="0.000268" value="0.000268079" alpha="255"/>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0"/>
    <huesaturation colorizeBlue="128" colorizeOn="0" saturation="0" colorizeRed="255" colorizeStrength="100" grayscaleMode="0" colorizeGreen="128"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>