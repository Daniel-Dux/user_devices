from labscript_devices import register_classes

# Register the labscript device, BLACS tab, and worker so BLACS can discover this device.
register_classes(
    'StaticSLM',
    BLACS_tab='user_devices.StaticLV2SLM.blacs_tabs.StaticLV2SLMTab',
    runviewer_parser=None,
)